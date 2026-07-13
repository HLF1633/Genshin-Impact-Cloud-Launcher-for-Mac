"""主窗口模块 - 核心WebEngine视图，整合所有子模块"""
import sys
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QToolBar, QAction, QLabel, QMenu, QInputDialog,
    QMessageBox, QApplication, QStatusBar, QProgressBar,
    QPushButton, QStyle,
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEngineScript
from PyQt5.QtCore import QUrl, Qt, QTimer, QEvent
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtNetwork import QNetworkProxy

from .utils import (
    load_config, save_config,
)
from .account_manager import AccountManager
from .status_monitor import StatusMonitor
from .settings_dialog import SettingsDialog
from .tray_icon import TrayIcon


class MainWindow(QMainWindow):
    """云原神启动器主窗口"""

    def __init__(self):
        super().__init__()
        self._config = load_config()
        self._cloud_url = self._config.get("cloud_genshin_url", "https://ys.mihoyo.com/cloud/#/")
        self._close_to_tray = False

        self._profile = QWebEngineProfile.defaultProfile()
        self._setup_profile()

        self._webview = QWebEngineView()
        self._account_manager = AccountManager(self._profile)
        self._status_monitor = StatusMonitor(
            self._webview,
            threshold_minutes=self._config.get("remind_threshold_minutes", 15),
            parent=self,
        )

        self._init_ui()
        self._init_toolbar()
        self._init_statusbar()
        self._init_tray()

        self._connect_signals()

        from PyQt5.QtCore import QTimer
        QTimer.singleShot(200, lambda: self._webview.load(QUrl(self._cloud_url)))

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._update_statusbar_info)
        self._poll_timer.start(5000)

    def _setup_profile(self):
        """配置WebEngine Profile"""
        self._profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)

        from PyQt5.QtCore import QStandardPaths
        storage_path = QStandardPaths.writableLocation(
            QStandardPaths.AppLocalDataLocation
        ) + "/QtWebEngine"
        self._profile.setPersistentStoragePath(storage_path)

        # 在DocumentCreation阶段注入JS，这是最早的注入时机，确保在页面任何JS执行前运行
        script = QWebEngineScript()
        script.setName("fake-browser")
        script.setInjectionPoint(QWebEngineScript.DocumentCreation)
        script.setWorldId(QWebEngineScript.MainWorld)
        script.setRunsOnSubFrames(True)
        script.setSourceCode(
            "Object.defineProperty(navigator,'userAgent',{"
            "get:function(){return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36';},"
            "configurable:true});"
            "Object.defineProperty(navigator,'platform',{"
            "get:function(){return 'Win32';},configurable:true});"
            "Object.defineProperty(navigator,'vendor',{"
            "get:function(){return 'Google Inc.';},configurable:true});"
            "Object.defineProperty(navigator,'webdriver',{"
            "get:function(){return false;},configurable:true});"
            "if(typeof window.chrome==='undefined'){"
            "window.chrome={runtime:{},loadTimes:function(){},csi:function(){},app:{}};}"
        )
        self._profile.scripts().insert(script)

    def _init_ui(self):
        self.setWindowTitle("云原神启动器")
        self.resize(
            self._config.get("window_width", 1280),
            self._config.get("window_height", 800),
        )
        self.setMinimumSize(800, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._webview)

    def _init_toolbar(self):
        toolbar = QToolBar("导航")
        toolbar.setMovable(False)
        toolbar.setIconSize(toolbar.iconSize() * 0.8)
        self.addToolBar(toolbar)

        style = self.style()

        action_back = QAction("后退", self)
        action_back.setIcon(style.standardIcon(QStyle.SP_ArrowBack))
        action_back.triggered.connect(self._webview.back)
        toolbar.addAction(action_back)

        action_forward = QAction("前进", self)
        action_forward.setIcon(style.standardIcon(QStyle.SP_ArrowForward))
        action_forward.triggered.connect(self._webview.forward)
        toolbar.addAction(action_forward)

        action_reload = QAction("刷新", self)
        action_reload.setIcon(style.standardIcon(QStyle.SP_BrowserReload))
        action_reload.triggered.connect(self._webview.reload)
        toolbar.addAction(action_reload)

        action_home = QAction("主页", self)
        action_home.setIcon(style.standardIcon(QStyle.SP_ComputerIcon))
        action_home.triggered.connect(
            lambda: self._webview.load(QUrl(self._cloud_url))
        )
        toolbar.addAction(action_home)

        toolbar.addSeparator()

        self._url_label = QLabel(self._cloud_url)
        self._url_label.setStyleSheet(
            "QLabel {"
            "  background: #f0f0f0;"
            "  border: 1px solid #ccc;"
            "  border-radius: 4px;"
            "  padding: 2px 8px;"
            "  color: #333;"
            "}"
        )
        self._url_label.setMinimumWidth(300)
        toolbar.addWidget(self._url_label)

        toolbar.addSeparator()

        btn_account = QPushButton("账号")
        btn_account.setToolTip("账号管理")
        btn_account.clicked.connect(self._show_account_menu)
        toolbar.addWidget(btn_account)

        self._proxy_label = QLabel(
            "🔗" if self._config.get("proxy") else "🌐"
        )
        self._proxy_label.setToolTip(
            f"代理: {self._config.get('proxy', '直连')}"
        )
        toolbar.addWidget(self._proxy_label)

        action_settings = QAction("设置", self)
        action_settings.setIcon(style.standardIcon(QStyle.SP_FileDialogDetailedView))
        action_settings.triggered.connect(self._open_settings)
        toolbar.addAction(action_settings)

    def _show_account_menu(self, pos=None):
        menu = QMenu(self)
        accounts = self._account_manager.list_accounts()
        current = self._account_manager.get_current_account()

        if current:
            act_current = QAction(f"👤 当前: {current}")
            act_current.setEnabled(False)
            menu.addAction(act_current)
            menu.addSeparator()

        for name in accounts:
            action = QAction(
                f"✅ {name}" if name == current else f"📋 {name}"
            )
            action.triggered.connect(lambda checked, n=name: self._switch_to_account(n))
            menu.addAction(action)

        menu.addSeparator()

        action_save = QAction("💾 保存当前账号", menu)
        action_save.triggered.connect(self._save_current_account)
        menu.addAction(action_save)

        menu.addSeparator()

        if accounts:
            menu_del = menu.addMenu("🗑 删除账号")
            for name in accounts:
                del_action = QAction(name, menu_del)
                del_action.triggered.connect(lambda checked, n=name: self._delete_account(n))
                menu_del.addAction(del_action)

        sender = self.sender()
        if isinstance(sender, QPushButton):
            menu.exec_(sender.mapToGlobal(sender.rect().bottomLeft()))
        else:
            menu.exec_(self.mapToGlobal(self.rect().center()))

    def _init_statusbar(self):
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)

        self._lbl_queue = QLabel("排队: --")
        self._lbl_queue.setMinimumWidth(100)
        self._statusbar.addPermanentWidget(self._lbl_queue)

        self._lbl_remaining = QLabel("剩余时长: --")
        self._lbl_remaining.setMinimumWidth(150)
        self._lbl_remaining.setStyleSheet("color: #E67E22; font-weight: bold;")
        self._statusbar.addPermanentWidget(self._lbl_remaining)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumWidth(120)
        self._progress_bar.setMaximumHeight(14)
        self._progress_bar.setVisible(False)
        self._statusbar.addPermanentWidget(self._progress_bar)

    def _init_tray(self):
        self._tray = TrayIcon(self)
        self._tray.show()

    def _connect_signals(self):
        self._webview.loadStarted.connect(self._on_load_started)
        self._webview.loadFinished.connect(self._on_load_finished)
        self._webview.urlChanged.connect(self._on_url_changed)
        self._webview.titleChanged.connect(self._on_title_changed)

        self._status_monitor.queue_changed.connect(self._on_queue_changed)
        self._status_monitor.remaining_time_changed.connect(self._on_remaining_changed)
        self._status_monitor.reminder_needed.connect(self._on_reminder_needed)

        self._tray.show_window_requested.connect(self._show_window)
        self._tray.quit_requested.connect(self._do_quit)
        self._tray.switch_account_requested.connect(self._show_account_menu)
        self._tray.open_settings_requested.connect(self._open_settings)

    def _on_load_started(self):
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)
        self._statusbar.showMessage("正在加载...")

    def _on_load_finished(self, ok):
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(100 if ok else 0)
        self._progress_bar.setVisible(False)
        if ok:
            self._statusbar.showMessage("加载完成", 3000)
            if not self._status_monitor._timer.isActive():
                self._status_monitor.start()
        else:
            self._statusbar.showMessage("加载失败", 5000)

    def _on_url_changed(self, url: QUrl):
        url_str = url.toString()
        self._url_label.setText(url_str)

        if "mihoyo.com" not in url_str and "hoyoverse.com" not in url_str:
            if url_str.startswith("http") and url_str != "about:blank":
                reply = QMessageBox.question(
                    self,
                    "外部链接",
                    f"即将跳转到外部网站:\n{url_str}\n\n是否允许？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply == QMessageBox.No:
                    self._webview.load(QUrl(self._cloud_url))

    def _on_title_changed(self, title: str):
        if title:
            self.setWindowTitle(f"云原神启动器 - {title}")

    def _on_queue_changed(self, count: int):
        self._lbl_queue.setText(f"排队: {count}人")
        if count > 0:
            self._lbl_queue.setStyleSheet("color: #E74C3C; font-weight: bold;")
        else:
            self._lbl_queue.setStyleSheet("color: #27AE60;")

    def _on_remaining_changed(self, minutes: int):
        if minutes >= 60:
            h = minutes // 60
            m = minutes % 60
            text = f"剩余时长: {h}小时{m}分钟"
        else:
            text = f"剩余时长: {minutes}分钟"
        self._lbl_remaining.setText(text)

        if minutes <= 30:
            self._lbl_remaining.setStyleSheet("color: #E74C3C; font-weight: bold;")
        elif minutes <= 60:
            self._lbl_remaining.setStyleSheet("color: #E67E22; font-weight: bold;")
        else:
            self._lbl_remaining.setStyleSheet("color: #27AE60; font-weight: bold;")

    def _on_reminder_needed(self, remaining: int):
        self._tray.show_reminder(remaining)

    def _update_statusbar_info(self):
        queue = self._status_monitor._last_queue
        remaining = self._status_monitor._last_remaining
        self._tray.update_status(queue, remaining)

    def _save_current_account(self):
        name, ok = QInputDialog.getText(
            self,
            "保存账号",
            "请输入账号名称:",
        )
        if ok and name.strip():
            name = name.strip()
            self._account_manager.save_cookies_from_storage(name)
            self._statusbar.showMessage(f"账号 '{name}' 已保存", 3000)

    def _switch_to_account(self, name: str):
        reply = QMessageBox.question(
            self,
            "切换账号",
            f"确定要切换到账号 '{name}' 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            success = self._account_manager.load_account_cookies(name)
            if success:
                self._statusbar.showMessage(f"已切换到账号 '{name}'", 3000)
                self._webview.load(QUrl(self._cloud_url))
            else:
                QMessageBox.warning(self, "错误", f"加载账号失败！")

    def _delete_account(self, name: str):
        reply = QMessageBox.warning(
            self,
            "删除账号",
            f"确定要删除账号 '{name}' 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._account_manager.delete_account(name)
            self._statusbar.showMessage(f"账号 '{name}' 已删除", 3000)

    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec_():
            self._config = dlg.get_config()
            self._apply_settings()

    def _apply_settings(self):
        cfg = self._config
        self.resize(
            cfg.get("window_width", 1280),
            cfg.get("window_height", 800),
        )
        self._status_monitor.set_threshold(
            cfg.get("remind_threshold_minutes", 15)
        )
        new_url = cfg.get("cloud_genshin_url", "")
        if new_url and new_url != self._cloud_url:
            self._cloud_url = new_url
            self._webview.load(QUrl(self._cloud_url))
        proxy = cfg.get("proxy", "")
        self._proxy_label.setText("🔗" if proxy else "🌐")
        self._proxy_label.setToolTip(f"代理: {proxy if proxy else '直连'}")

    def _show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if self._config.get("auto_hide_to_tray", True):
            event.ignore()
            self.hide()
        else:
            self._do_quit()
            event.accept()

    def _do_quit(self):
        self._status_monitor.stop()
        self._tray.hide()
        QApplication.quit()