"""云原神启动器 - WKWebView + JS Bridge Pointer Lock

正常浏览器行为: 点击游戏画面后 Pointer Lock 激活, 鼠标隐藏控制视角。
WKWebView on macOS 10.15 不支持原生 Pointer Lock。

方案: 注入 JS 代理 requestPointerLock, 通过 WKScriptMessageHandler
通知原生端进入"鼠标捕获模式"。页面普通操作(登录/按钮)不受影响。

Usage:
    python3 main.py
"""

import sys
import os
import json
from pathlib import Path

from PyObjCTools import AppHelper
import AppKit
import WebKit
import Foundation
import Quartz
import objc

CLOUD_URL = "https://ys.mihoyo.com/cloud/#/"
DEFAULT_W, DEFAULT_H = 1280, 800

SAFARI_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/15.6.1 Safari/605.1.15"
)


def get_app_dir():
    base = Path.home() / "Library" / "Application Support"
    d = base / "CloudGenshinLauncher"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_config():
    path = get_app_dir() / "config.json"
    default = {"window_width": DEFAULT_W, "window_height": DEFAULT_H}
    if path.exists():
        try:
            with open(path) as f:
                cfg = json.load(f)
            for k, v in default.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
        except (json.JSONDecodeError, OSError):
            pass
    return default


# ---- JS 注入脚本 ----

BRIDGE_JS = r"""
(function() {
    window.__pl_el = null;
    window.__pl_active = false;

    // 辅助: 派发 pointerlockchange 事件
    function _dispatchPlChange() {
        document.dispatchEvent(new Event('pointerlockchange', {bubbles: true}));
    }

    // 代理 requestPointerLock
    Element.prototype.requestPointerLock = function() {
        window.__pl_el = this;
        window.__pl_active = true;
        document.body.style.cursor = 'none';
        // ★ 关键: 通知原生端 + 派发 pointerlockchange 事件
        try {
            window.webkit.messageHandlers.plBridge.postMessage('lock');
        } catch(e) {}
        _dispatchPlChange();
    };

    // 代理 exitPointerLock
    document.exitPointerLock = function() {
        window.__pl_el = null;
        window.__pl_active = false;
        document.body.style.cursor = 'default';
        try {
            window.webkit.messageHandlers.plBridge.postMessage('unlock');
        } catch(e) {}
        _dispatchPlChange();
    };

    // pointerLockElement getter
    Object.defineProperty(document, 'pointerLockElement', {
        get: function() { return window.__pl_el; },
        configurable: true
    });

    // 原生端注入的鼠标移动处理
    window.__handlePlMove = function(movementX, movementY) {
        if (!window.__pl_active || !window.__pl_el) return;

        // 创建带 movementX/Y 的 MouseEvent，在 document 上派发
        var e = new MouseEvent('mousemove', {
            bubbles: true,
            cancelable: true,
            view: window,
            movementX: movementX,
            movementY: movementY,
            clientX: window.innerWidth / 2 + movementX,
            clientY: window.innerHeight / 2 + movementY,
            screenX: window.screenX + window.innerWidth / 2,
            screenY: window.screenY + window.innerHeight / 2
        });
        // 在 locked element 上 dispatch（游戏通常监听 canvas 上的 mousemove）
        window.__pl_el.dispatchEvent(e);
        // 同时在 document 上 dispatch（部分引擎监听全局 mousemove）
        document.dispatchEvent(e);
    };

    window.__handlePlSetActive = function(active) {
        window.__pl_active = active;
        if (!active) {
            window.__pl_el = null;
            _dispatchPlChange();
        }
    };
})();
"""


class PointerLockBridge(Foundation.NSObject):
    """接收 JS 的 Pointer Lock 请求"""

    def initWithView_(self, owner):
        self = objc.super(PointerLockBridge, self).init()
        if self:
            self._owner = owner
        return self

    def userContentController_didReceiveScriptMessage_(
        self, controller, message
    ):
        body = message.body()
        if body == "lock":
            self._owner._enter_game_mode()
        elif body == "unlock":
            self._owner._exit_game_mode()


class GameView(AppKit.NSView):
    """包装 WKWebView, 管理鼠标捕获模式"""

    def initWithFrame_webview_(self, frame, webview):
        self = objc.super(GameView, self).initWithFrame_(frame)
        if self:
            self._webview = webview
            self._webview.setFrame_(frame)
            self.addSubview_(self._webview)

            self._game_mode = False
            self._center = (0.0, 0.0)

            opts = (AppKit.NSTrackingMouseMoved
                    | AppKit.NSTrackingActiveInActiveApp)
            area = AppKit.NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(
                self.bounds(), opts, self, None
            )
            self.addTrackingArea_(area)
        return self

    def acceptsFirstResponder(self):
        return True

    def updateTrackingAreas(self):
        for a in self.trackingAreas():
            self.removeTrackingArea_(a)
        opts = AppKit.NSTrackingMouseMoved | AppKit.NSTrackingActiveInActiveApp
        area = AppKit.NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(
            self.bounds(), opts, self, None
        )
        self.addTrackingArea_(area)

    # ---- 游戏模式 ----

    def _enter_game_mode(self):
        if self._game_mode:
            return
        self._game_mode = True
        Quartz.CGAssociateMouseAndMouseCursorPosition(False)
        AppKit.NSCursor.hide()
        self._update_center()
        Quartz.CGWarpMouseCursorPosition(self._center)
        # 通知 JS
        self._webview.evaluateJavaScript_completionHandler_(
            "window.__pl_active=true;window.__handlePlSetActive(true);", None
        )

    def _exit_game_mode(self):
        if not self._game_mode:
            return
        self._game_mode = False
        Quartz.CGAssociateMouseAndMouseCursorPosition(True)
        AppKit.NSCursor.unhide()
        self._webview.evaluateJavaScript_completionHandler_(
            "window.__pl_active=false;window.__pl_el=null;window.__handlePlSetActive(false);document.body.style.cursor='default';", None
        )

    def _update_center(self):
        win = self.window()
        if win:
            f = win.frame()
            self._center = (f.origin.x + f.size.width / 2, f.origin.y + f.size.height / 2)

    # ---- 鼠标事件 ----
    # 正常模式下全部转发给 WKWebView
    # 游戏模式下: mousemove 计算delta注入JS, click正常转发

    def mouseMoved_(self, event):
        if not self._game_mode:
            return
        loc = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
        dx = loc.x - self._center[0]
        dy = loc.y - self._center[1]
        if abs(dx) > 0.05 or abs(dy) > 0.05:
            self._webview.evaluateJavaScript_completionHandler_(
                f"window.__handlePlMove({dx},{dy});", None
            )
            Quartz.CGWarpMouseCursorPosition(self._center)

    def mouseDown_(self, event):
        self._webview.mouseDown_(event)

    def mouseUp_(self, event):
        self._webview.mouseUp_(event)

    def rightMouseDown_(self, event):
        self._webview.rightMouseDown_(event)

    def rightMouseUp_(self, event):
        self._webview.rightMouseUp_(event)

    def otherMouseDown_(self, event):
        self._webview.otherMouseDown_(event)

    def otherMouseUp_(self, event):
        self._webview.otherMouseUp_(event)

    def scrollWheel_(self, event):
        self._webview.scrollWheel_(event)

    # ---- 键盘 ----
    def keyDown_(self, event):
        code = event.keyCode()
        # Alt / Option / Escape = 释放鼠标
        if code in (55, 56, 58, 61, 53):
            if self._game_mode:
                self._exit_game_mode()
        self._webview.keyDown_(event)

    def keyUp_(self, event):
        self._webview.keyUp_(event)

    # ---- resize ----
    def setFrameSize_(self, size):
        objc.super(GameView, self).setFrameSize_(size)
        self._webview.setFrameSize_(size)
        if self._game_mode:
            self._update_center()

    def viewDidMoveToWindow(self):
        if self._game_mode:
            self._update_center()


def main():
    cfg = load_config()
    w, h = cfg.get("window_width", DEFAULT_W), cfg.get("window_height", DEFAULT_H)

    app = AppKit.NSApplication.sharedApplication()
    app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)

    # ---- WKWebView ----
    web_config = WebKit.WKWebViewConfiguration.alloc().init()
    prefs = WebKit.WKPreferences.alloc().init()
    prefs.setValue_forKey_(True, "developerExtrasEnabled")
    web_config.setPreferences_(prefs)
    web_config.setMediaTypesRequiringUserActionForPlayback_(WebKit.WKAudiovisualMediaTypeNone)

    user_content = WebKit.WKUserContentController.alloc().init()
    wk_script = WebKit.WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
        BRIDGE_JS,
        WebKit.WKUserScriptInjectionTimeAtDocumentEnd,
        True,
    )
    user_content.addUserScript_(wk_script)
    web_config.setUserContentController_(user_content)

    webview = WebKit.WKWebView.alloc().initWithFrame_configuration_(
        Foundation.NSMakeRect(0, 0, w, h), web_config
    )
    webview.setCustomUserAgent_(SAFARI_UA)

    url = Foundation.NSURL.URLWithString_(CLOUD_URL)
    req = Foundation.NSMutableURLRequest.requestWithURL_(url)
    webview.loadRequest_(req)

    # ---- 窗口 ----
    frame = Foundation.NSMakeRect(100, 100, w, h)
    mask = (
        AppKit.NSWindowStyleMaskTitled
        | AppKit.NSWindowStyleMaskClosable
        | AppKit.NSWindowStyleMaskMiniaturizable
        | AppKit.NSWindowStyleMaskResizable
    )
    window = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, mask, AppKit.NSBackingStoreBuffered, False
    )
    window.setTitle_("云原神启动器")
    window.setMinSize_(Foundation.NSSize(800, 600))
    window.setReleasedWhenClosed_(False)
    window.setAcceptsMouseMovedEvents_(True)

    # GameView 包装
    sz = window.contentView().frame().size
    game_view = GameView.alloc().initWithFrame_webview_(
        Foundation.NSMakeRect(0, 0, sz.width, sz.height), webview
    )
    game_view.setAutoresizingMask_(
        AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable
    )
    window.setContentView_(game_view)
    window.makeFirstResponder_(game_view)

    # 注册 JS bridge
    bridge = PointerLockBridge.alloc().initWithView_(game_view)
    user_content.addScriptMessageHandler_name_(bridge, "plBridge")

    window.center()
    window.makeKeyAndOrderFront_(None)

    app.activateIgnoringOtherApps_(True)
    AppHelper.runEventLoop()


if __name__ == "__main__":
    main()