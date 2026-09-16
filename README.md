# ⏻ Shutdown Timer

Multi-language PC shutdown / restart / sleep / hibernate timer with a minimalistic floating widget and tray support.

**English** | [Русский](README.ru.md)

---

## ✨ Features
- Shutdown / Restart / Sleep / Hibernate
- Countdown "after N time" or "at a specific time"
- Quick presets + custom presets
- Mini floating widget with click-through game mode
- Global hotkeys (`Ctrl+Alt+S` / `P` / `X`)
- 20 interface languages
- Dark / light theme
- Autostart with Windows

---

## ✅ Requirements
- Windows 10 or 11
- **Python 3.11 or newer** — required even if you use the `.exe` version

---

## 🚀 Installation

### Step 1 — Install / update Python (always, one command)

Open **CMD** (`Win + R` → `cmd` → Enter):

```cmd
winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements & winget upgrade --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
```

This **installs Python if missing** and **updates it if already present**.

Then **close and reopen CMD** and verify:

```cmd
py -3 --version
```

### Step 2 — Update pip, setuptools, wheel (always, one command)

```cmd
py -3 -m pip install --upgrade pip setuptools wheel
```

---

## 📥 Installing the app

### 🟢 A. If you have the `.exe` file
Double-click `ShutdownTimer.exe`. Done.

### 🟡 B. If you have the `.pyw` file
```cmd
py -3 -m pip install --upgrade pystray Pillow keyboard
pythonw shutdown_timer_multilang.pyw
```

### 🔴 C. If you have a `.bat` that builds `.exe`
```cmd
py -3 -m pip install --upgrade pyinstaller pystray Pillow keyboard
```
Then double-click the `.bat`. The ready `.exe` will appear in `dist\`.

---

## ▶️ Usage
- Choose action: **Shutdown / Restart / Sleep / Hibernate**.
- Choose mode: **after duration** or **at a specific time**.
- Pick a preset or spin the wheels manually.
- Press **▶ Start**. Main window hides, mini widget appears.
- Mini widget buttons: `⏸` pause, `⤢` expand, `✕` cancel.

Hotkeys:
- `Ctrl + Alt + S` — show / hide window
- `Ctrl + Alt + P` — pause / resume
- `Ctrl + Alt + X` — cancel

---

## 🛠 Troubleshooting

| Problem | Solution |
|---|---|
| `'py' is not recognized` | Reinstall Python with PrependPath (see weather README) |
| `pip` not found | Use `py -3 -m pip ...` |
| Hibernate does nothing | Enable hibernation: `powercfg /hibernate on` in CMD (as Administrator) |
| Hotkeys do not work | Another app uses them; the tray menu still works |
| `keyboard` module needs admin | Right-click CMD → *Run as administrator* |

---

## 📜 License
MIT
