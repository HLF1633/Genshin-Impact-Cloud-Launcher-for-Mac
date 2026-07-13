"""工具函数模块"""
import os
import sys
import json
from pathlib import Path

# 云原神官方入口地址
CLOUD_GENSHIN_URL = "https://ys.mihoyo.com"


def get_app_dir() -> Path:
    """获取应用数据目录"""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path.home() / ".local" / "share"
    
    app_dir = base / "CloudGenshinLauncher"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_config_path() -> Path:
    """获取配置文件路径"""
    return get_app_dir() / "config.json"


def load_config() -> dict:
    """加载配置文件"""
    path = get_config_path()
    default = {
        "auto_hide_to_tray": True,
        "proxy": "",
        "remind_threshold_minutes": 15,
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "window_width": 1280,
        "window_height": 800,
        "cloud_genshin_url": CLOUD_GENSHIN_URL,
    }
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # 合并默认值
            for k, v in default.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
        except (json.JSONDecodeError, OSError):
            return default
    return default


def save_config(config: dict) -> None:
    """保存配置文件"""
    path = get_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_accounts_dir() -> Path:
    """获取账号数据目录"""
    d = get_app_dir() / "accounts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def resource_path(relative_path: str) -> str:
    """获取资源文件绝对路径（兼容PyInstaller打包）"""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = Path(__file__).resolve().parent.parent
    return str(Path(base) / relative_path)