"""账号管理模块 - 管理多账号的Cookie持久化"""
import json
import shutil
from pathlib import Path
from typing import Optional
from PyQt5.QtWebEngineWidgets import QWebEngineProfile

from .utils import get_accounts_dir


class AccountManager:
    """管理云原神多账号登录状态"""

    def __init__(self, profile: QWebEngineProfile):
        self._profile = profile
        self._accounts_dir = get_accounts_dir()
        self._current_account: Optional[str] = None

    def list_accounts(self) -> list[str]:
        accounts = []
        for item in sorted(self._accounts_dir.iterdir()):
            if item.is_dir() and (item / "cookies.json").exists():
                accounts.append(item.name)
        return accounts

    def get_current_account(self) -> Optional[str]:
        return self._current_account

    def save_cookies_from_storage(self, account_name: str) -> bool:
        account_dir = self._accounts_dir / account_name
        account_dir.mkdir(parents=True, exist_ok=True)

        profile_path = Path(self._profile.persistentStoragePath())
        if profile_path.exists():
            target = account_dir / "profile_data"
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(profile_path, target)

        self._current_account = account_name
        return True

    def load_account_cookies(self, account_name: str) -> bool:
        account_dir = self._accounts_dir / account_name
        cookies_file = account_dir / "cookies.json"
        if not cookies_file.exists():
            return False

        try:
            with open(cookies_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            cookie_list = data.get("cookies", [])
            cookie_store = self._profile.cookieStore()
            cookie_store.deleteAllCookies()

            from PyQt5.QtNetwork import QNetworkCookie
            from PyQt5.QtCore import QDateTime

            for c in cookie_list:
                qcookie = QNetworkCookie(
                    c["name"].encode("utf-8"),
                    c["value"].encode("utf-8"),
                )
                qcookie.setDomain(c.get("domain", ""))
                qcookie.setPath(c.get("path", "/"))
                qcookie.setExpirationDate(QDateTime.currentDateTime().addYears(1))
                cookie_store.setCookie(qcookie)

            self._current_account = account_name
            return True
        except (json.JSONDecodeError, OSError):
            return False

    def delete_account(self, account_name: str) -> bool:
        account_dir = self._accounts_dir / account_name
        if account_dir.exists():
            shutil.rmtree(account_dir)
            if self._current_account == account_name:
                self._current_account = None
            return True
        return False