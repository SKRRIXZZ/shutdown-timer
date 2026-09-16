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

## ⚠️ Windows SmartScreen / Defender warning (first launch)

This app is **not digitally signed**. That's why on first launch Windows may show:

- **SmartScreen:** *"Windows protected your PC"* (blue dialog)
- **Defender:** *"This app has been blocked for your protection"*

This is a **false positive**. It happens because Windows doesn't recognize the publisher — not because the app contains a virus. All source code is available in this repository, so you can inspect it and even build the `.exe` yourself.

### ✅ How to run it anyway

**For SmartScreen (blue dialog):**

1. Click **More info**.
2. Click **Run anyway**.

**Alternative — unblock the file permanently:**

1. Right-click the downloaded `.exe` file → **Properties**.
2. At the bottom of the **General** tab, check **Unblock**.
3. Click **Apply** → **OK**.

**If Windows Defender blocks it entirely:**

1. Open **Windows Security** → **Virus & threat protection**.
2. Scroll down to **Virus & threat protection settings** → **Manage settings**.
3. Under **Exclusions**, click **Add or remove exclusions**.
4. Click **Add an exclusion** → **File** → select the `.exe` file.
5. Run the app again.

**If Defender blocks your `.bat` build:**

PyInstaller "packs" Python code into a single `.exe`, which sometimes looks suspicious to Defender. Just add the project folder to Windows Security exclusions:

1. Open **Windows Security** → **Virus & threat protection** → **Manage settings**.
2. Under **Exclusions**, click **Add or remove exclusions** → **Add an exclusion** → **Folder**.
3. Select the folder containing your `.pyw` file and `.bat` script.
4. Run the `.bat` again.

> 💡 **Safety tip:** You can also upload the `.exe` to [VirusTotal](https://www.virustotal.com/) to verify it before running.

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
