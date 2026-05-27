# Thunar Custom Actions Generator (`uca.xml`)

A Python tool to easily generate Thunar's `uca.xml` (Custom Actions) file — available in both **GUI** and **CLI** modes.

Designed for **Debian / XFCE** systems (including Linux Mint Xfce, Xubuntu, etc.).

---

## Features

- **GUI mode** — a clean PyQt6 interface with checkboxes, a live summary panel, and a one-click generate button
- **CLI mode** — scriptable, supports direct arguments, interactive `whiptail` prompts, or plain text input as fallback
- Writes `uca.xml` directly to `~/.config/Thunar/`
- Optionally copies the file to `/etc/skel/.config/Thunar/` (requires root via `pkexec`)
- GTK theme-aware: the GUI reads your system colors automatically

---

## Available Actions

| # | Action | Submenu |
|---|--------|---------|
| 1 | Open Terminal Here | — |
| 2 | Open as Root | — |
| 3 | Create a Link | — |
| 4 | Verify (ISO files) | — |
| 5 | Share with LocalSend | — |
| 6 | Run Python Script | Python |
| 7 | Run Python Script (No Log) | Python |
| 8 | Run Python Script (No Terminal) | Python |
| 9 | Run Bash Script | Bash |
| 10 | Run Bash Script (No Log) | Bash |
| 11 | Run Bash Script (No Terminal) | Bash |
| 12 | Install .deb Package | Debian |
| 13 | Install .deb Package (No Log) | Debian |
| 14 | Edit with Nano | — |

---

## Requirements

- Python 3.10+
- **GUI mode:** `PyQt6`
- **CLI interactive mode (optional):** `whiptail`

Install dependencies:

Debian 13 | SatellaOS Trixie

```bash
sudo apt install --install-recommends -y python3 python3-pyqt6 whiptail python3-gi libgtk-3-0 gir1.2-gtk-3.0
```

---

## Usage

### GUI Mode

Simply run the script without any arguments:

```bash
python3 uca-creator.py
```

A window will open where you can:
- Check/uncheck the actions you want
- See a live summary of your selection
- Click **GENERATE uca.xml** to write the file

### CLI Mode

**Add all actions at once:**

```bash
python3 uca-creator.py --cli all
```

**Add specific actions by number:**

```bash
python3 uca-creator.py --cli 1 3 9 12
```

**Interactive CLI (whiptail checklist or text prompt):**

```bash
python3 uca-creator.py --cli
```

If `whiptail` is installed, a terminal checklist dialog appears. Otherwise, a plain text prompt is shown.

**Show help:**

```bash
python3 uca-creator.py --help
```

---

## Output

The generated file is written to:

```
~/.config/Thunar/uca.xml
```

If root privileges are granted via `pkexec`, a copy is also placed at:

```
/etc/skel/.config/Thunar/uca.xml
```

After generating, restart Thunar to apply the changes:

```bash
thunar -q && thunar &
```

---

## Notes

- Actions that belong to a submenu group (Python, Bash, Debian) appear as nested entries in Thunar's right-click menu.
- The `Share with LocalSend` action (action 5) supports both native install and Flatpak.
- The `Verify (ISO files)` action (action 4) uses `mint-iso-verify`, available on Linux Mint systems.

---

## License

MIT
