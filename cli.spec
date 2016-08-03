# -*- mode: python -*-

block_cipher = None


a = Analysis(['baker.py'],
             pathex=['C:\\Users\\Roman\\PycharmProjects\\Baker'],
             binaries=None,
             datas=[("config.json", "."), ("README.md", ".")],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='BakerCore',
          debug=False,
          strip=False,
          upx=True,
          console=True , icon='resources\\cli.ico')
