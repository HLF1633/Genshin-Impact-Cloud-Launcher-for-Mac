"""设置对话框"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QCheckBox, QLineEdit, QSpinBox,
    QGroupBox, QDialogButtonBox,
)

from .utils import load_config, save_config


class SettingsDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = load_config()
        self.setWindowTitle("设置")
        self.setMinimumWidth(450)
        self._init_ui()
        self._load_config_to_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        group_general = QGroupBox("常规")
        form_general = QFormLayout(group_general)
        self.chk_auto_hide = QCheckBox("启动时自动隐藏到系统托盘")
        form_general.addRow(self.chk_auto_hide)
        layout.addWidget(group_general)

        group_remind = QGroupBox("时长提醒")
        form_remind = QFormLayout(group_remind)
        self.spin_threshold = QSpinBox()
        self.spin_threshold.setRange(1, 120)
        self.spin_threshold.setSuffix(" 分钟")
        self.spin_threshold.setToolTip("剩余时长低于此值时弹出提醒")
        form_remind.addRow("提醒阈值:", self.spin_threshold)
        layout.addWidget(group_remind)

        group_network = QGroupBox("网络")
        form_network = QFormLayout(group_network)
        self.edit_proxy = QLineEdit()
        self.edit_proxy.setPlaceholderText("例如: http://127.0.0.1:7890 (留空则直连)")
        form_network.addRow("代理地址:", self.edit_proxy)
        self.edit_user_agent = QLineEdit()
        self.edit_user_agent.setPlaceholderText("浏览器User-Agent")
        form_network.addRow("User-Agent:", self.edit_user_agent)
        layout.addWidget(group_network)

        group_window = QGroupBox("默认窗口")
        form_window = QFormLayout(group_window)
        self.spin_width = QSpinBox()
        self.spin_width.setRange(800, 3840)
        self.spin_width.setSuffix(" px")
        form_window.addRow("宽度:", self.spin_width)
        self.spin_height = QSpinBox()
        self.spin_height.setRange(600, 2160)
        self.spin_height.setSuffix(" px")
        form_window.addRow("高度:", self.spin_height)
        layout.addWidget(group_window)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        btn_box.accepted.connect(self._on_save)
        btn_box.rejected.connect(self.reject)
        btn_box.button(QDialogButtonBox.Apply).clicked.connect(self._on_save)
        layout.addWidget(btn_box)

    def _load_config_to_ui(self):
        cfg = self._config
        self.chk_auto_hide.setChecked(cfg.get("auto_hide_to_tray", True))
        self.spin_threshold.setValue(cfg.get("remind_threshold_minutes", 15))
        self.edit_proxy.setText(cfg.get("proxy", ""))
        self.edit_user_agent.setText(cfg.get("user_agent", ""))
        self.spin_width.setValue(cfg.get("window_width", 1280))
        self.spin_height.setValue(cfg.get("window_height", 800))

    def _on_save(self):
        self._config["auto_hide_to_tray"] = self.chk_auto_hide.isChecked()
        self._config["remind_threshold_minutes"] = self.spin_threshold.value()
        self._config["proxy"] = self.edit_proxy.text().strip()
        self._config["user_agent"] = self.edit_user_agent.text().strip()
        self._config["window_width"] = self.spin_width.value()
        self._config["window_height"] = self.spin_height.value()
        save_config(self._config)
        self.accept()

    def get_config(self) -> dict:
        return self._config