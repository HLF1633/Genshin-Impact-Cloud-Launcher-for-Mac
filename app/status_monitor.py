"""状态监控模块 - 通过JS注入获取等待队列和剩余时长信息"""
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView


class StatusMonitor(QObject):
    """定时通过JavaScript注入获取云原神页面状态信息"""

    queue_changed = pyqtSignal(int)
    remaining_time_changed = pyqtSignal(int)
    reminder_needed = pyqtSignal(int)

    def __init__(self, webview: QWebEngineView, threshold_minutes: int = 15, parent=None):
        super().__init__(parent)
        self._webview = webview
        self._threshold_minutes = threshold_minutes
        self._last_queue = -1
        self._last_remaining = -1
        self._reminder_sent = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll_status)
        self._timer.setInterval(15000)

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def set_threshold(self, minutes: int):
        self._threshold_minutes = minutes
        self._reminder_sent = False

    def _poll_status(self):
        script = r"""
        (function() {
            var result = {queue: -1, remaining: -1};
            var bodyText = document.body ? document.body.innerText : '';
            var queueMatch = bodyText.match(/(?:排队|前方|等待)[\s\S]*?(\d+)\s*(?:人|位)/);
            if (queueMatch) { result.queue = parseInt(queueMatch[1]); }
            var timeMatch = bodyText.match(/(?:剩余|可用)[\s\S]*?(\d+)\s*(?:小时|时|h)/);
            var minMatch = bodyText.match(/(?:剩余|可用)[\s\S]*?(\d+)\s*(?:分钟|分|min)/);
            if (timeMatch && minMatch) { result.remaining = parseInt(timeMatch[1]) * 60 + parseInt(minMatch[1]); }
            else if (minMatch) { result.remaining = parseInt(minMatch[1]); }
            else if (timeMatch) { result.remaining = parseInt(timeMatch[1]) * 60; }
            else {
                var clockMatch = bodyText.match(/(\d{1,2}):(\d{2}):(\d{2})/);
                if (clockMatch) { result.remaining = parseInt(clockMatch[1]) * 60 + parseInt(clockMatch[2]); }
            }
            return result;
        })();
        """

        def callback(result):
            try:
                queue_count = result.property("queue")
                remaining = result.property("remaining")
                try:
                    queue_count = int(queue_count)
                except (TypeError, ValueError):
                    queue_count = -1
                try:
                    remaining = int(remaining)
                except (TypeError, ValueError):
                    remaining = -1

                if 0 <= queue_count != self._last_queue:
                    self._last_queue = queue_count
                    self.queue_changed.emit(queue_count)

                if 0 <= remaining != self._last_remaining:
                    self._last_remaining = remaining
                    self.remaining_time_changed.emit(remaining)
                    if 0 <= remaining <= self._threshold_minutes and not self._reminder_sent:
                        self._reminder_sent = True
                        self.reminder_needed.emit(remaining)

                if remaining > self._threshold_minutes:
                    self._reminder_sent = False
            except Exception:
                pass

        self._webview.page().runJavaScript(script, callback)