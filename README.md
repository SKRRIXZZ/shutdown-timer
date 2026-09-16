# ⏻ Shutdown Timer

Multi-language PC shutdown / restart / sleep / hibernate timer with a minimalistic floating widget and a tray icon.

**English** | [Русский](README.ru.md)

---

## ✨ Features
- Shutdown / Restart / Sleep / Hibernate
- Countdown "after N time" or "at a specific time"
- Quick presets + custom presets
- Mini floating widget with click-through game mode
- Global hotkeys (Ctrl+Alt+S / P / X)
- 20 interface languages
- Autostart with Windows

## ✅ Requirements
- Windows 10 or 11
- **Python 3.11 or newer** (needed even if you run the `.exe` version)

## 🚀 Installation

### Step 1 — Install Python (always)
```cmd
winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements & winget upgrade --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
```
Close and reopen CMD, check:
```cmd
py -3 --version
```

### Step 2 — Choose your variant

#### 🟢 A. You have the `.exe` file
Double-click `ShutdownTimer.exe`.

#### 🟡 B. You have the `.pyw` file
```cmd
py -3 -m pip install --upgrade pystray Pillow keyboard
pythonw shutdown_timer_multilang.pyw
```

#### 🔴 C. You have a `.bat` that builds `.exe`
```cmd
py -3 -m pip install --upgrade pyinstaller pystray Pillow keyboard
```
Double-click the `.bat`.

## ▶️ Usage
- Choose action (Shutdown/Restart/Sleep).
- Choose mode (after duration / at specific time).
- Press **▶ Start**.
- Hotkeys: `Ctrl+Alt+S` (show/hide), `Ctrl+Alt+P` (pause), `Ctrl+Alt+X` (cancel).

## 📜 License
MIT
