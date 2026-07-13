# Cloud Genshin Launcher

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-macOS%2010.15%2B-lightgrey)]()

An unofficial macOS desktop launcher for **[Cloud Genshin](https://ys.mihoyo.com/cloud/#/)** (云·原神) — HoyoVerse's cloud-streaming Genshin Impact service. Built with native WKWebView (Safari engine) for maximum compatibility, with system-level mouse capture to enable full PC-style keyboard & mouse gameplay.

> ⚠️ This project is an **unofficial community tool** and is not affiliated with or endorsed by HoyoVerse/miHoYo. Use at your own discretion.

---

## Features

| Feature | Description |
|---------|-------------|
| **Native macOS window** | Clean NSWindow with the Genshin logo, no browser chrome |
| **PC-style mouse control** | System-level mouse capture (`CGWarpMouseCursorPosition`) with movement delta injection |
| **Pointer Lock emulation** | JS bridge proxies `requestPointerLock` / `exitPointerLock` via `WKScriptMessageHandler` |
| **Alt / Esc to release cursor** | Press Alt or Escape to exit game mode and recover the mouse |
| **Desktop Safari UA** | Masquerades as macOS Safari 15.6.1 for seamless page compatibility |
| **Minimal dependencies** | Only requires `pyobjc` (Apple frameworks bridge) — no heavy browser engine |

---

## How It Works

```
click game canvas → JS calls requestPointerLock()
  → WKScriptMessageHandler → native enters "game mode"
  → CGAssociateMouseAndMouseCursorPosition(False) + NSCursor.hide()
  → mouseMoved: captures delta, warp back to center
  → JS injects MouseEvent with movementX/Y
  → game processes camera rotation
press Alt/Esc → exit game mode → cursor restored
```

---

## Requirements

- **macOS 10.15 (Catalina)** or later
- **Python 3.10+** (system Python or homebrew)

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/cloud-genshin-launcher.git
cd cloud-genshin-launcher

# Install dependencies
pip3 install -r requirements.txt

# Run
python3 main.py
```

---

## Build .app Bundle

```bash
# Install py2app
pip3 install py2app

# Build
python3 setup.py py2app

# Output: dist/云原神启动器.app
# Copy to /Applications
cp -R "dist/云原神启动器.app" /Applications/
```

### Custom Icon

Place a `logo.png` (1024×1024 RGBA, transparent background) in the project root, then:

```bash
python3 setup.py py2app
```

The build script automatically generates a multi-resolution `.icns` file via `sips` + `iconutil`.

---

## Project Structure

```
cloud-genshin-launcher/
├── main.py              # Entry point — WKWebView + mouse capture
├── setup.py             # py2app packaging config
├── requirements.txt     # Python dependencies
├── logo.png             # App icon (1024×1024 RGBA)
├── build.sh             # One-click build script
├── LICENSE              # Apache License 2.0
├── README.md            # This file
└── app/                 # Legacy PyQt5 modules (not used in current version)
```

---

## Technical Details

### Why WKWebView?

PyQt5's Chromium 87 is too old for Cloud Genshin's modern Web APIs (WebCodecs, WebRTC).
WKWebView uses macOS's built-in Safari engine which fully supports the page.

### Why Custom Pointer Lock?

macOS 10.15's WKWebView does not support the Pointer Lock API.
The launcher emulates it using:

| Layer | API |
|-------|-----|
| Cursor hide | `NSCursor.hide()` |
| Cursor detach | `CGAssociateMouseAndMouseCursorPosition(False)` |
| Center lock | `CGWarpMouseCursorPosition()` |
| Delta capture | `NSTrackingArea` → `mouseMoved:` |
| JS injection | `evaluateJavaScript:completionHandler:` |

---

## License

```
Copyright 2025 Cloud Genshin Launcher Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

See [LICENSE](LICENSE) for the full text.

---

## Disclaimer

This project is for educational purposes. All rights related to "Genshin Impact", "Cloud Genshin" (云·原神), and related assets belong to HoyoVerse/miHoYo.