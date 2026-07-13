"""系统托盘图标模块"""
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt5.QtCore import QSize, Qt, pyqtSignal


class TrayIcon(QSystemTrayIcon):
    """系统托盘图标，支持右键菜单和状态显示"""

    show_window_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    switch_account_requested = pyqtSignal()
    open_settings_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue_count = 0
        self._remaining_minutes = -1
        self._setup_icon()
        self._setup_menu()
        self.setToolTip("云原神启动器")
        self.activated.connect(self._on_activated)

    def _setup_icon(self):
        icon = self._generate_icon("原", QColor("#4A90D9"))
        self.setIcon(icon)

    def _generate_icon(self, text: str, color: QColor, size: int = 64) -> QIcon:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, size - 8, size - 8)

        painter.setPen(Qt.white)
        font = QFont("PingFang SC", size // 2, QFont.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, text)

        painter.end()
        return QIcon(pixmap)

    def _setup_menu(self):
        menu = QMenu()

        action_show = QAction("显示主窗口", menu)
        action_show.triggered.connect(self.show_window_requested.emit)
        menu.addAction(action_show)

        menu.addSeparator()

        action_switch = QAction("切换账号", menu)
        action_switch.triggered.connect(self.switch_account_requested.emit)
        menu.addAction(action_switch)

        action_settings = QAction("设置", menu)
        action_settings.triggered.connect(self.open_settings_requested.emit)
        menu.addAction(action_settings)

        menu.addSeparator()

        action_quit = QAction("退出", menu)
        action_quit.triggered.connect(self.quit_requested.emit)
        menu.addAction(action_quit)

        self.setContextMenu(menu)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window_requested.emit()
        elif reason == QSystemTrayIcon.Trigger:
            self.show_window_requested.emit()

    def update_status(self, queue_count: int = -1, remaining_minutes: int = -1):
        tips = ["云原神启动器"]

        if queue_count >= 0:
            self._queue_count = queue_count
            tips.append(f"排队: {queue_count}人")

        if remaining_minutes >= 0:
            self._remaining_minutes = remaining_minutes
            if remaining_minutes >= 60:
                h = remaining_minutes // 60
                m = remaining_minutes % 60
                tips.append(f"剩余: {h}小时{m}分钟")
            else:
                tips.append(f"剩余: {remaining_minutes}分钟")

        self.setToolTip("\n".join(tips))

    def show_reminder(self, remaining_minutes: int):
        self.showMessage(
            "云原神 - 时长提醒",
            f"剩余游玩时长仅剩 {remaining_minutes} 分钟！请注意合理安排时间。",
            QIcon(),
            5000,
        )