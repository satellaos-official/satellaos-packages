# Deb Creator

A Python tool to easily build `.deb` packages — available in both **GUI** and **CLI** modes.

Designed for **Debian / XFCE** systems (including Linux Mint Xfce, Xubuntu, SatellaOS, etc.).

---

## Features

- **GUI mode** — a clean PyQt6 interface to fill in package metadata, pick files, and build with one click
- **CLI mode** — build from a `.sdcfg` / `.json` config file without opening any interface
- **Config overrides** — override version, arch, package name and more directly from the command line
- **Dry-run mode** — validate your config and preview what would be built, without actually building
- **Auto-install** — optionally run `sudo apt install` on the produced `.deb` right after a successful build
- GTK theme-aware: the GUI reads your system colors automatically
- Supports Python, Bash, and binary scripts; creates wrapper launchers automatically
- Generates `.desktop` files and installs icons into the correct hicolor paths

---

## Requirements

- Python 3.10+
- `dpkg-deb` (usually pre-installed on Debian-based systems)
- **GUI mode:** `PyQt6`, `python3-gi`, `gir1.2-gtk-3.0`

Install dependencies:

**Debian 13 / SatellaOS Trixie**

```bash
sudo apt install --install-recommends -y python3 python3-gi gir1.2-gtk-3.0 python3-pyqt6
```

---

## Usage

### GUI Mode

Simply run the script without any arguments:

```bash
python3 deb-creator.py
```

Or explicitly:

```bash
python3 deb-creator.py --gui
```

A window will open where you can:

- Fill in package metadata (name, version, architecture, maintainer, description, dependencies)
- Select your main script (Python, Bash, or binary) and extra files/folders
- Pick an icon and configure the `.desktop` entry
- Set the output directory
- Click **BUILD** to create the `.deb` file and watch the live log

### CLI Mode

**Build from a config file:**

```bash
python3 deb-creator.py -f myapp.sdcfg
```

**Backwards-compatible shorthand (single positional argument):**

```bash
python3 deb-creator.py myapp.sdcfg
```

**Override version and output directory:**

```bash
python3 deb-creator.py -f myapp.sdcfg --version 2.1.0 -o ~/packages
```

**Preview without building (dry run):**

```bash
python3 deb-creator.py -f myapp.sdcfg --dry-run
```

**Build quietly, then auto-install:**

```bash
python3 deb-creator.py -f myapp.sdcfg -q --install
```

**Override architecture for cross-packaging:**

```bash
python3 deb-creator.py -f myapp.sdcfg --arch arm64
```

**Show help:**

```bash
python3 deb-creator.py --help
```

---

## Options

| Option | Description |
|--------|-------------|
| *(none)* | Launch the graphical interface (default) |
| `-f`, `--file <CONFIG>` | Path to a `.sdcfg` or `.json` config file (required for CLI mode) |
| `-o`, `--output <DIR>` | Output directory for the `.deb` file (overrides config) |
| `--version <VER>` | Package version string, e.g. `1.2.0` (overrides config) |
| `--arch <ARCH>` | Target architecture — `amd64`, `arm64`, `armhf`, `i386`, `all` (overrides config) |
| `--pkg-name <NAME>` | Package name (overrides config) |
| `--no-desktop` | Skip `.desktop` file creation even if config enables it |
| `-q`, `--quiet` | Suppress info-level log lines; only show warnings, errors, and the final result |
| `--dry-run` | Parse and validate config, print a summary, then exit without building |
| `--install` | After a successful build, run `sudo apt install` on the produced `.deb` |
| `--help` | Show the help message and exit |

> CLI overrides (`--version`, `--arch`, `--pkg-name`, etc.) take priority over values in the config file.

---

## Config File Format

Config files use the `.sdcfg` extension (JSON under the hood). The easiest way to create one is to fill in the GUI and use **File → Save Configuration**. The file can then be used directly with `-f` for automated or headless builds.

---

## What Happens When a Package is Built

1. A temporary staging directory is created under `/tmp/`
2. The directory structure (`DEBIAN/`, `usr/share/`, `usr/bin/`, etc.) is assembled
3. The main script is copied to `usr/share/<pkg>/` and a wrapper launcher is written to `usr/bin/<cmd>`
4. Extra files and folders are placed at their configured destination paths
5. The icon is installed to `usr/share/icons/hicolor/scalable/apps/`
6. A `.desktop` file is written to `usr/share/applications/` (if enabled)
7. `DEBIAN/control` (and optional `postinst` / `prerm` scripts) are generated
8. `dpkg-deb --build` produces the final `.deb` file in the output directory

---

## Notes

- Binary script type: the file is copied directly to `usr/bin/<cmd>` with no wrapper.
- Python / Bash script types: the file goes to `usr/share/<pkg>/` and a small `bash` wrapper is placed in `usr/bin/`.
- Extra entries that cannot be found on disk are skipped with a warning rather than aborting the build.
- The `--dry-run` flag never touches the filesystem; it is safe to use for validation in CI pipelines.

---

## License

MIT
