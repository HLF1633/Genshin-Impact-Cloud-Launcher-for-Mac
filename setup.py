"""py2app 打包配置"""
from setuptools import setup

APP = ["main.py"]
DATA_FILES = []

OPTIONS = {
    "argv_emulation": False,
    "iconfile": "logo.icns",
    "plist": {
        "CFBundleName": "云原神启动器",
        "CFBundleDisplayName": "云原神启动器",
        "CFBundleIdentifier": "com.cloudgenshin.launcher",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "10.15.0",
        "LSUIElement": False,
    },
}

setup(
    name="CloudGenshinLauncher",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)