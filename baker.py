# -*- coding: utf-8 -*-
from PyQt4.QtCore import QThread
import os
import subprocess
import probe


class Converter(QThread):
    if __name__ != "__main__":
        from PyQt4.QtCore import pyqtSignal
        from PyQt4.QtCore import QThread
        update = pyqtSignal(list)
        finished = pyqtSignal()

    def __init__(self, anime, performance=""):
        import json
        from collections import OrderedDict
        from os import environ, path, makedirs, chdir

        with open("config.json", "r") as f:
            global settings
            settings = json.load(f, object_pairs_hook=OrderedDict)
        print("Settings loaded.")

        workdir = settings["tools_location"].replace("%appdata%", environ['APPDATA'])
        if not path.exists(workdir):
            makedirs(workdir)
        chdir(workdir)
        print("Working directory changed to {}".format(workdir))

        if __name__ != "__main__":
            super(Converter, self).__init__()
        self.need_convert = False
        self.audio = [False, 'path', 'items']
        self.subs = [False, 'path', 'items']
        self.first = 0
        self.last = 0
        self.params = ""
        for flag in settings["x264"]:
            if flag == "preset" and "fast" in performance:
                self.params = "--preset {} ".format(performance)
                break
            self.params += "--{} {} ".format(flag, settings["x264"][flag])
        if performance == "lightweight":
           self.params = "--threads 1 {}".format(self.params)
        self.verbose = False
        self.anime = anime
        print("Converter initialized.")

    def setup(self, first, last, need_convert, audio=None, subs=None, verbose=False):
        if audio:
            self.audio = [True,
                          anime.audio[audio]["path"],
                          anime.audio[audio]["items"]]
        if subs:
            self.subs = [True,
                         anime.subtitles[subs]["path"],
                         anime.subtitles[subs]["items"]]
        self.first = first
        self.last = last
        self.need_convert = bool(need_convert)
        if verbose:
            self.verbose = True
        print("Converter parameters set.")

    def x264(self, folder, file, extension):
        import atexit

        print("[x264] Converting:\n\t{} from {}".format(file, folder))
        preset = 'x264 --verbose {} -o "'.format(self.params)
        query = '{}{}.x264" "{}\\{}.{}"'.format(preset, file, folder, file, extension)
        frames_to_decode = probe.frames_total("{}\\{}.{}".format(folder, file, extension))
        completion = -1
        print("[x264] Executing: {}".format(query))
        x = subprocess.Popen(query, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        atexit.register(x.kill)
        while x.returncode is None:
            x.poll()
            #print("[x264][DEBUG] {}".format(x.stdout.readline()))
            #print("[x264][DEBUG] {}".format(x.stderr.readline()))
            line = x.stderr.readline()
            try:
                frame = line.decode().split('frame=')[-1].split()[0]
                frame = int(frame)
            except:
                continue
            progress = int(int(frame)/frames_to_decode*100)
            if progress != completion:
                try:
                    self.update.emit([None, progress])
                except RuntimeError:
                    print("{}%".format(progress))
                completion = progress
        if x.returncode != 0:
            print("[x264][ERROR] x264 exited with code {}!".format(x.returncode))
            exit(1)
        else:
            print("[x264] Conversion completed.")
        atexit.unregister(x.kill)


    def mkvmerge(self, folder, file, fonts):
        print("[mkvmerge] Merging:\n\t{} from {}".format(file, folder))
        if not os.path.exists(folder + '\\Baked'):
            os.makedirs(folder + '\\Baked')
        v = '"{}\\{}.mkv" '.format(folder, file)
        v8 = '"{}.x264" '.format(file)
        a = '--forced-track "0:yes" --default-track "0:yes" "{}\\{}.mka" '.format(self.audio[1], file)
        if os.path.exists('{}\\{}.ass'.format(self.subs[1], file)):
            s = '--forced-track "0:yes" --default-track "0:yes" "{}\\{}.ass" '.format(self.subs[1], file)
        elif os.path.exists('{}\\{}.надписи.ass'.format(self.subs[1], file)):
            s = '--forced-track "0:yes" --default-track "0:yes" "{}\\{}.надписи.ass" '.format(self.subs[1], file)
        else:
            print('[mkvmerge][ERROR] Sub file error!')
            s = ''
        query = 'mkvmerge -o "' + folder + '\\Baked\\' + file + '.mkv" '
        if self.need_convert:
            query += (v8 + '-D ')
        query += v
        if self.audio[0]:
            query += a
        if self.subs[0]:
            query += s
            if fonts:
                for folder in fonts:
                    for font in fonts[folder]:
                        query += '--attachment-mime-type application/octet-stream ' \
                                 '--attach-file "{}\{}" '.format(folder, font)
        print("[mkvmerge] Executing: {}".format(query))
        if self.verbose:
            ret = subprocess.call(query, shell=True, creationflags=0x08000000)
        else:
            ret = subprocess.call(query, shell=True)
        if ret != 0:
            print("[mkvmerge][ERROR] mkvmerge exited with code {}!".format(ret))
            exit(1)
        else:
            print("[mkvmerge] Merging completed.")

    def run(self):
        print("Work started...")
        self.progress_counter = 0
        for i in range(self.first, self.last+1):
            if self.need_convert:
                self.x264(self.anime.folder, self.anime.episode(i-1), self.anime.v_ext)
            self.mkvmerge(self.anime.folder, self.anime.episode(i-1), self.anime.fonts)
            if self.need_convert:
                os.remove(self.anime.episode(i-1)+'.x264')
            self.progress_counter += 1
            try:
                self.update.emit([self.progress_counter, None])
            except RuntimeError:
                print("Completed {} episode(s).".format(self.progress_counter))
        try:
            self.update.emit([None, 100])
            self.finished.emit()
        except RuntimeError:
            print("Work finished.")

if __name__ == "__main__":
    import sys
    import json
    from collections import OrderedDict
    from getopt import getopt
    from title import Anime
    from os import environ, path, makedirs, chdir

    print("Baker started.")
    convert = False
    verbose = False
    lightweight = False
    opts, args = getopt(sys.argv[1:], "p:a:s:f:t:P:cv")
    '''
    p - Path to title folder
    a - name of the folder containing Audio
    s - name of the folder containing Subtitles
    f - From episode number
    t - To episode number
    P - performance mode (lightweight or ultrafast)
    c - file needs Conversion
    v - verbose output
    l - lightweight conversion
    '''
    for opt, arg in opts:
        if opt == "-p":   path = arg
        elif opt == "-a": audio = arg
        elif opt == "-s": subtitles = arg
        elif opt == "-f": fromep = int(arg)
        elif opt == "-t": toep = int(arg)
        elif opt == "-c": convert = True
        elif opt == "-v": verbose = True
        elif opt == "-P": performance = arg
    print("Command line parameters read.")
    anime = Anime(path)
    converter = Converter(anime, performance=performance)
    converter.setup(fromep, toep, convert, audio, subtitles, verbose)
    converter.run()