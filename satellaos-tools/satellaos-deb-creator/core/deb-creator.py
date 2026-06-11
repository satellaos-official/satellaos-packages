#!/usr/bin/env python3
"""
SatellaOS Deb Creator
Builds .deb packages from a GUI interface.
"""

import os
import sys
import shutil
import subprocess
import tempfile
import argparse
from pathlib import Path
from datetime import datetime

# ── CLI mode (--file) ─────────────────────────────────────────────────────────
# Parse early so we never import PyQt6 when running headless.

def _parse_sdcf(path: str) -> dict:
    """Read a .sdcf config file and return a fields dict."""
    text = Path(path).read_text(encoding="utf-8")
    data: dict = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        data[key.strip()] = value

    # Decode escaped values
    if "post_install" in data:
        data["post_install"] = data["post_install"].replace("\\n", "\n").replace("\\\\", "\\")
    for bool_key in ("create_desktop", "terminal_app"):
        if bool_key in data:
            data[bool_key] = data[bool_key].lower() == "true"

    # Defaults for optional keys
    data.setdefault("extra_files", "")
    data.setdefault("extra_folders", "")
    data.setdefault("extra_files_location", "")
    data.setdefault("wrapper_location", "/usr/bin")
    data.setdefault("architecture", "x86_64")
    data.setdefault("create_desktop", True)
    data.setdefault("terminal_app", False)
    data.setdefault("post_install", "")
    data.setdefault("category", "Utility")
    data.setdefault("dependencies", "")
    data.setdefault("output_dir", str(Path.home()))
    data.setdefault("icon", "")

    return data


def _cli_build(sdcf_path: str):
    """Headless build: load .sdcf, run _build(), print logs to stdout."""
    from datetime import datetime as _dt

    sdcf_path = os.path.expanduser(sdcf_path)
    if not os.path.isfile(sdcf_path):
        print(f"✗ File not found: {sdcf_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading config: {sdcf_path}")
    fields = _parse_sdcf(sdcf_path)

    # Inline build (reuses BuildWorker._build logic but logs to print)
    class _TerminalWorker(BuildWorker):
        def _log(self, msg: str):
            ts = _dt.now().strftime("%H:%M:%S")
            print(f"[{ts}] {msg}")

        def run_sync(self):
            try:
                self._build(self.f)
                print("✓ Build succeeded.")
            except Exception as e:
                print(f"✗ Build failed: {e}", file=sys.stderr)
                sys.exit(1)

    worker = _TerminalWorker(fields)
    worker.run_sync()
    sys.exit(0)


_cli_args = None
if __name__ == "__main__":
    _parser = argparse.ArgumentParser(
        description="SatellaOS Deb Creator — GUI or headless build",
        add_help=True,
    )
    _parser.add_argument(
        "--file", metavar="PATH",
        help="Path to a .sdcf config file; build without opening the GUI",
    )
    _cli_args, _remaining = _parser.parse_known_args()
    # Remove --file … from sys.argv so Qt doesn't choke on unknown args
    sys.argv = [sys.argv[0]] + _remaining


from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton,
    QFileDialog, QTextEdit, QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QFont, QColor, QPalette, QTextCursor

# ── Palette ────────────────────────────────────────────────────────────────────

DARK = {
    "bg":        "#1E1E1E",
    "panel":     "#2e2e2e",
    "text":      "#bfbfbf",
    "accent":    "#442178",
    "scrollbar": "#F5F5F5",
}

LIGHT = {
    "bg":        "#F5F5F5",
    "panel":     "#bfbfbf",
    "text":      "#2e2e2e",
    "accent":    "#442178",
    "scrollbar": "#1E1E1E",
}

SCRIPT_DIR = Path(__file__).parent.resolve()

# ── Build worker ───────────────────────────────────────────────────────────────

class BuildWorker(QThread):
    log_line   = pyqtSignal(str)
    finished   = pyqtSignal(bool, str)   # success, message

    def __init__(self, fields: dict):
        super().__init__()
        self.f = fields

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_line.emit(f"[{ts}] {msg}")

    def run(self):
        f = self.f
        try:
            self._build(f)
        except Exception as e:
            self.finished.emit(False, str(e))

    def _build(self, f):
        pkg_name     = f["package_name"].strip()
        cmd_name     = f["command_name"].strip()
        app_name     = f["app_name"].strip()
        version      = f["version"].strip() or "1.0.0"
        maintainer   = f["maintainer"].strip() or "unknown"
        arch         = f["architecture"]
        main_script  = f["main_script"].strip()
        icon_path    = f["icon"].strip()
        output_dir   = f["output_dir"].strip() or str(Path.home())
        wrapper_loc  = f["wrapper_location"].strip() or "/usr/bin"
        depends      = f["dependencies"].strip()
        create_desk  = f["create_desktop"]
        terminal_app = f["terminal_app"]
        category     = f["category"].strip() or "Utility"
        post_install = f["post_install"].strip()

        if not pkg_name:
            raise ValueError("Package Name is required.")
        if not cmd_name:
            raise ValueError("Command Name is required.")
        if not main_script:
            raise ValueError("Main Script is required.")
        if not os.path.isfile(main_script):
            raise FileNotFoundError(f"Main script not found: {main_script}")

        self._log(f"Starting build: {pkg_name} {version}")

        tmpdir = Path(tempfile.mkdtemp())
        pkg_root = tmpdir / f"{pkg_name}_{version}"
        debian_dir = pkg_root / "DEBIAN"
        debian_dir.mkdir(parents=True)

        # ── DEBIAN/control ────────────────────────────────────────────────────
        arch_map = {"x86_64": "amd64", "arm64": "arm64"}
        deb_arch = arch_map.get(arch, "amd64")

        control_lines = [
            f"Package: {pkg_name}",
            f"Version: {version}",
            f"Architecture: {deb_arch}",
            f"Maintainer: {maintainer}",
            f"Description: {app_name}",
        ]
        if depends:
            control_lines.append(f"Depends: {depends}")
        control_lines.append("")
        (debian_dir / "control").write_text("\n".join(control_lines))
        self._log("Created DEBIAN/control")

        # ── wrapper script ────────────────────────────────────────────────────
        wrapper_dir = pkg_root / wrapper_loc.lstrip("/")
        wrapper_dir.mkdir(parents=True, exist_ok=True)

        script_dest_dir = pkg_root / "usr" / "lib" / pkg_name
        script_dest_dir.mkdir(parents=True, exist_ok=True)

        main_script_name = Path(main_script).name
        shutil.copy2(main_script, script_dest_dir / main_script_name)
        self._log(f"Copied main script → /usr/lib/{pkg_name}/{main_script_name}")

        wrapper_script = wrapper_dir / cmd_name
        wrapper_content = f"#!/bin/bash\nexec /usr/lib/{pkg_name}/{main_script_name} \"$@\"\n"
        wrapper_script.write_text(wrapper_content)
        wrapper_script.chmod(0o755)
        self._log(f"Created wrapper → {wrapper_loc}/{cmd_name}")

        # ── extra files ───────────────────────────────────────────────────────
        extra_dest = f["extra_files_location"].strip()
        if extra_dest:
            dest_base = pkg_root / extra_dest.lstrip("/") / pkg_name
            dest_base.mkdir(parents=True, exist_ok=True)
            for file_path in [p for p in f["extra_files"].split("|") if p]:
                src = Path(file_path)
                if src.is_file():
                    shutil.copy2(src, dest_base / src.name)
                    self._log(f"Copied file {src.name} → {extra_dest}/{pkg_name}/")
                else:
                    self._log(f"⚠ File not found, skipped: {file_path}")
            for folder_path in [p for p in f["extra_folders"].split("|") if p]:
                src = Path(folder_path)
                if src.is_dir():
                    shutil.copytree(src, dest_base / src.name, dirs_exist_ok=True)
                    self._log(f"Copied folder {src.name} → {extra_dest}/{pkg_name}/")
                else:
                    self._log(f"⚠ Folder not found, skipped: {folder_path}")

        # ── icon ──────────────────────────────────────────────────────────────
        icon_installed_path = ""
        if icon_path and os.path.isfile(icon_path):
            icon_ext   = Path(icon_path).suffix.lower()
            icon_name  = f"{pkg_name}{icon_ext}"
            icon_dest  = pkg_root / "usr" / "share" / "pixmaps"
            icon_dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(icon_path, icon_dest / icon_name)
            icon_installed_path = f"/usr/share/pixmaps/{icon_name}"
            self._log(f"Copied icon → {icon_installed_path}")

        # ── .desktop file ─────────────────────────────────────────────────────
        if create_desk:
            desktop_dir = pkg_root / "usr" / "share" / "applications"
            desktop_dir.mkdir(parents=True, exist_ok=True)
            desktop_lines = [
                "[Desktop Entry]",
                "Type=Application",
                f"Name={app_name}",
                f"Exec={wrapper_loc}/{cmd_name}",
                f"Categories={category};",
                f"Terminal={'true' if terminal_app else 'false'}",
            ]
            if icon_installed_path:
                desktop_lines.append(f"Icon={icon_installed_path}")
            desktop_lines.append("")
            (desktop_dir / f"{pkg_name}.desktop").write_text("\n".join(desktop_lines))
            self._log(f"Created .desktop file for {app_name}")

        # ── postinst ──────────────────────────────────────────────────────────
        postinst_lines = ["#!/bin/bash", "set -e", ""]
        postinst_lines.append(f"chmod +x /usr/lib/{pkg_name}/{main_script_name}")
        if post_install:
            postinst_lines.append("")
            postinst_lines.append(post_install)
        postinst_lines.append("")
        postinst = debian_dir / "postinst"
        postinst.write_text("\n".join(postinst_lines))
        postinst.chmod(0o755)
        self._log("Created DEBIAN/postinst")

        # ── build .deb ────────────────────────────────────────────────────────
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        deb_filename = f"{pkg_name}_{version}_{deb_arch}.deb"
        deb_out = output_path / deb_filename

        self._log(f"Running dpkg-deb...")
        result = subprocess.run(
            ["dpkg-deb", "--build", "--root-owner-group", str(pkg_root), str(deb_out)],
            capture_output=True, text=True
        )
        shutil.rmtree(tmpdir, ignore_errors=True)

        if result.returncode != 0:
            raise RuntimeError(f"dpkg-deb failed:\n{result.stderr}")

        self._log(f"Done → {deb_out}")
        self.finished.emit(True, str(deb_out))


# ── Main window ────────────────────────────────────────────────────────────────

class DebCreator(QWidget):
    def __init__(self):
        super().__init__()
        self.dark_mode = True
        self._worker: BuildWorker | None = None
        self.setWindowTitle("SatellaOS Deb Creator")
        self.setMinimumSize(1000, 680)
        self._setup_ui()
        self._apply_theme()

    # ── UI construction ───────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # top bar (theme toggle)
        self.top_bar = QFrame()
        self.top_bar.setFixedHeight(44)
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(10, 4, 10, 4)
        top_layout.addStretch()

        self.btn_dark  = QPushButton()
        self.btn_light = QPushButton()
        for btn, filename, tip in [
            (self.btn_dark,  "darkmode.png",  "Dark Mode"),
            (self.btn_light, "lightmode.png", "Light Mode"),
        ]:
            btn.setFixedSize(32, 32)
            btn.setToolTip(tip)
            btn.setFlat(True)
            icon_path = SCRIPT_DIR / filename
            if icon_path.exists():
                btn.setIcon(QIcon(str(icon_path)))
            else:
                btn.setText("◐" if "dark" in filename else "○")
            top_layout.addWidget(btn)

        self.btn_dark.clicked.connect(lambda: self._set_theme(True))
        self.btn_light.clicked.connect(lambda: self._set_theme(False))
        root.addWidget(self.top_bar)

        # middle: scrollable left panel + log
        middle = QHBoxLayout()
        middle.setContentsMargins(0, 0, 0, 0)
        middle.setSpacing(0)

        # scrollbar + panel
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setFixedWidth(370)

        panel_widget = QWidget()
        self.panel_layout = QVBoxLayout(panel_widget)
        self.panel_layout.setContentsMargins(14, 14, 14, 14)
        self.panel_layout.setSpacing(10)
        scroll.setWidget(panel_widget)
        self.scroll = scroll

        # fields dict
        self.fields = {}

        self._add_field("package_name",       "Package Name",         "satellaos-my-app")
        self._add_field("command_name",        "Command Name",         "my-app")
        self._add_field("app_name",            "Application Name",     "My App")
        self._add_field("version",             "Version",              "1.0.0")
        self._add_field("maintainer",          "Maintainer",           "dev@example.com")

        # arch pill selector
        lbl = QLabel("Architecture")
        lbl.setObjectName("field_label")
        self.panel_layout.addWidget(lbl)

        arch_row = QHBoxLayout()
        arch_row.setSpacing(0)
        arch_row.setContentsMargins(0, 0, 0, 0)

        self._arch_value = "x86_64"
        self._arch_btns = {}
        for i, arch in enumerate(["x86_64", "arm64"]):
            btn = QPushButton(arch)
            btn.setCheckable(True)
            btn.setObjectName("arch_pill_left" if i == 0 else "arch_pill_right")
            btn.setFixedHeight(30)
            btn.setChecked(arch == self._arch_value)
            btn.clicked.connect(lambda _, a=arch: self._select_arch(a))
            self._arch_btns[arch] = btn
            arch_row.addWidget(btn)

        arch_widget = QWidget()
        arch_widget.setLayout(arch_row)
        self.panel_layout.addWidget(arch_widget)

        self._add_file_field("main_script",         "Main Script",            "Select script file")
        self._add_file_field("icon",                "Icon (SVG/PNG)",          "Select icon file", filters="Images (*.svg *.png)")
        self._add_dir_field( "output_dir",          "Output Directory",        str(Path.home()))
        # ── Extra Files (multi) ───────────────────────────────────────────────
        lbl_ef = QLabel("Extra Files")
        lbl_ef.setObjectName("field_label")
        self.panel_layout.addWidget(lbl_ef)
        self.extra_files_list = self._make_list_widget()
        self.panel_layout.addWidget(self.extra_files_list["frame"])
        ef_row = QHBoxLayout()
        ef_row.setSpacing(6)
        ef_row.setContentsMargins(0, 0, 0, 0)
        btn_ef_add = QPushButton("Add Files")
        btn_ef_add.setObjectName("btn_browse")
        btn_ef_rem = QPushButton("Remove")
        btn_ef_rem.setObjectName("btn_browse")
        ef_row.addWidget(btn_ef_add)
        ef_row.addWidget(btn_ef_rem)
        ef_row.addStretch()
        ef_row_w = QWidget()
        ef_row_w.setLayout(ef_row)
        self.panel_layout.addWidget(ef_row_w)

        def _ef_add():
            paths, _ = QFileDialog.getOpenFileNames(self, "Select Files", str(Path.home()), "All files (*)")
            for p in paths:
                self._list_add(self.extra_files_list, p)
        def _ef_rem():
            self._list_remove(self.extra_files_list)
        btn_ef_add.clicked.connect(_ef_add)
        btn_ef_rem.clicked.connect(_ef_rem)

        # ── Extra Folders (multi) ─────────────────────────────────────────────
        lbl_efol = QLabel("Extra Folders")
        lbl_efol.setObjectName("field_label")
        self.panel_layout.addWidget(lbl_efol)
        self.extra_folders_list = self._make_list_widget()
        self.panel_layout.addWidget(self.extra_folders_list["frame"])
        efol_row = QHBoxLayout()
        efol_row.setSpacing(6)
        efol_row.setContentsMargins(0, 0, 0, 0)
        btn_efol_add = QPushButton("Add Folder")
        btn_efol_add.setObjectName("btn_browse")
        btn_efol_rem = QPushButton("Remove")
        btn_efol_rem.setObjectName("btn_browse")
        efol_row.addWidget(btn_efol_add)
        efol_row.addWidget(btn_efol_rem)
        efol_row.addStretch()
        efol_row_w = QWidget()
        efol_row_w.setLayout(efol_row)
        self.panel_layout.addWidget(efol_row_w)

        def _efol_add():
            path = QFileDialog.getExistingDirectory(self, "Select Folder", str(Path.home()))
            if path:
                self._list_add(self.extra_folders_list, path)
        def _efol_rem():
            self._list_remove(self.extra_folders_list)
        btn_efol_add.clicked.connect(_efol_add)
        btn_efol_rem.clicked.connect(_efol_rem)

        self._add_field(     "extra_files_location","Extra Files/Folders Location", "/usr/lib")
        self._add_field(     "wrapper_location",    "Wrapper Location",        "/usr/bin")
        self._add_field(     "dependencies",        "Dependencies",            "python3 python3-pyqt6")
        self._add_field(     "category",            "Category",                "Utility")

        # checkboxes
        self.chk_desktop  = QCheckBox("Create .desktop file")
        self.chk_terminal = QCheckBox("Terminal Application")
        self.chk_desktop.setChecked(True)
        self.chk_desktop.setObjectName("field_check")
        self.chk_terminal.setObjectName("field_check")
        self.panel_layout.addWidget(self.chk_desktop)
        self.panel_layout.addWidget(self.chk_terminal)

        # post install
        lbl_post = QLabel("Post Install Script")
        lbl_post.setObjectName("field_label")
        self.txt_post = QTextEdit()
        self.txt_post.setObjectName("field_textedit")
        self.txt_post.setFixedHeight(80)
        self.txt_post.setPlaceholderText("bash commands to run after install…")
        self.panel_layout.addWidget(lbl_post)
        self.panel_layout.addWidget(self.txt_post)

        self.panel_layout.addStretch()
        middle.addWidget(scroll)

        # log pane
        log_frame = QFrame()
        log_frame.setObjectName("log_frame")
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(10, 10, 10, 10)

        lbl_log = QLabel("Build Log")
        lbl_log.setObjectName("log_title")
        self.log_view = QTextEdit()
        self.log_view.setObjectName("log_view")
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Monospace", 9))

        log_layout.addWidget(lbl_log)
        log_layout.addWidget(self.log_view)
        middle.addWidget(log_frame, 1)

        root.addLayout(middle, 1)

        # bottom buttons
        self.bottom_bar = QFrame()
        self.bottom_bar.setFixedHeight(52)
        btn_layout = QHBoxLayout(self.bottom_bar)
        btn_layout.setContentsMargins(14, 8, 14, 8)
        btn_layout.addStretch()

        self.btn_save = QPushButton("Save")
        self.btn_save.setObjectName("btn_secondary")
        self.btn_save.setFixedHeight(34)
        self.btn_save.setMinimumWidth(80)
        self.btn_save.clicked.connect(self._save_config)

        self.btn_load = QPushButton("Load")
        self.btn_load.setObjectName("btn_secondary")
        self.btn_load.setFixedHeight(34)
        self.btn_load.setMinimumWidth(80)
        self.btn_load.clicked.connect(self._load_config)

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setObjectName("btn_secondary")
        self.btn_reset.setFixedHeight(34)
        self.btn_reset.setMinimumWidth(90)
        self.btn_reset.clicked.connect(self._reset)

        self.btn_build = QPushButton("BUILD .DEB")
        self.btn_build.setObjectName("btn_primary")
        self.btn_build.setFixedHeight(34)
        self.btn_build.setMinimumWidth(130)
        self.btn_build.clicked.connect(self._build)

        btn_layout.addWidget(self.btn_save)
        btn_layout.addSpacing(6)
        btn_layout.addWidget(self.btn_load)
        btn_layout.addSpacing(6)
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addSpacing(10)
        btn_layout.addWidget(self.btn_build)
        root.addWidget(self.bottom_bar)

    def _make_list_widget(self) -> dict:
        """Return a small scrollable list frame with an internal QVBoxLayout."""
        from PyQt6.QtWidgets import QListWidget
        lw = QListWidget()
        lw.setObjectName("field_edit")
        lw.setFixedHeight(72)
        lw.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        frame = QFrame()
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.addWidget(lw)
        return {"frame": frame, "list": lw}

    def _list_add(self, widget: dict, path: str):
        from PyQt6.QtWidgets import QListWidgetItem
        lw = widget["list"]
        existing = [lw.item(i).text() for i in range(lw.count())]
        if path not in existing:
            lw.addItem(path)

    def _list_remove(self, widget: dict):
        lw = widget["list"]
        for item in lw.selectedItems():
            lw.takeItem(lw.row(item))

    def _list_items(self, widget: dict) -> list[str]:
        lw = widget["list"]
        return [lw.item(i).text() for i in range(lw.count())]

    def _list_set(self, widget: dict, paths: list[str]):
        lw = widget["list"]
        lw.clear()
        for p in paths:
            lw.addItem(p)

    def _add_field(self, key: str, label: str, placeholder: str = ""):
        lbl = QLabel(label)
        lbl.setObjectName("field_label")
        edit = QLineEdit()
        edit.setObjectName("field_edit")
        edit.setPlaceholderText(placeholder)
        self.fields[key] = edit
        self.panel_layout.addWidget(lbl)
        self.panel_layout.addWidget(edit)

    def _add_file_field(self, key: str, label: str, btn_text: str,
                         filters: str = "All files (*)", folder_ok: bool = False):
        lbl = QLabel(label)
        lbl.setObjectName("field_label")
        row = QHBoxLayout()
        edit = QLineEdit()
        edit.setObjectName("field_edit")
        btn = QPushButton("Browse")
        btn.setObjectName("btn_browse")
        btn.setFixedWidth(64)
        row.addWidget(edit)
        row.addWidget(btn)
        self.fields[key] = edit

        def browse():
            if folder_ok:
                choice = QFileDialog.getOpenFileName(self, btn_text, str(Path.home()), filters)
                path = choice[0]
                if not path:
                    path = QFileDialog.getExistingDirectory(self, btn_text, str(Path.home()))
            else:
                path, _ = QFileDialog.getOpenFileName(self, btn_text, str(Path.home()), filters)
            if path:
                edit.setText(path)

        btn.clicked.connect(browse)
        self.panel_layout.addWidget(lbl)
        row_widget = QWidget()
        row_widget.setLayout(row)
        self.panel_layout.addWidget(row_widget)

    def _add_dir_field(self, key: str, label: str, default: str = ""):
        lbl = QLabel(label)
        lbl.setObjectName("field_label")
        row = QHBoxLayout()
        edit = QLineEdit()
        edit.setObjectName("field_edit")
        edit.setText(default)
        btn = QPushButton("Browse")
        btn.setObjectName("btn_browse")
        btn.setFixedWidth(64)
        row.addWidget(edit)
        row.addWidget(btn)
        self.fields[key] = edit

        def browse():
            path = QFileDialog.getExistingDirectory(self, label, edit.text() or str(Path.home()))
            if path:
                edit.setText(path)

        btn.clicked.connect(browse)
        self.panel_layout.addWidget(lbl)
        row_widget = QWidget()
        row_widget.setLayout(row)
        self.panel_layout.addWidget(row_widget)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _select_arch(self, arch: str):
        self._arch_value = arch
        for a, btn in self._arch_btns.items():
            btn.setChecked(a == arch)

    def _collect_fields(self) -> dict:
        d = {k: v.text() for k, v in self.fields.items()}
        d["architecture"]  = self._arch_value
        d["create_desktop"] = self.chk_desktop.isChecked()
        d["terminal_app"]   = self.chk_terminal.isChecked()
        d["post_install"]   = self.txt_post.toPlainText()
        d["extra_files"]    = "|".join(self._list_items(self.extra_files_list))
        d["extra_folders"]  = "|".join(self._list_items(self.extra_folders_list))
        return d

    def _reset(self):
        for edit in self.fields.values():
            edit.clear()
        self.fields["output_dir"].setText(str(Path.home()))
        self._select_arch("x86_64")
        self.chk_desktop.setChecked(True)
        self.chk_terminal.setChecked(False)
        self.txt_post.clear()
        self.extra_files_list["list"].clear()
        self.extra_folders_list["list"].clear()
        self.log_view.clear()
        self._log("Fields reset.")

    def _save_config(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration", str(Path.home()), "SatellaOS DEB Config File (*.sdcf)"
        )
        if not path:
            return
        if not path.endswith(".sdcf"):
            path += ".sdcf"
        f = self._collect_fields()
        lines = []
        for key, value in f.items():
            if key in ("create_desktop", "terminal_app"):
                lines.append(f"{key}={'true' if value else 'false'}")
            elif key == "post_install":
                encoded = value.replace("\\", "\\\\").replace("\n", "\\n")
                lines.append(f"{key}={encoded}")
            elif key in ("extra_files", "extra_folders"):
                lines.append(f"{key}={value}")  # already |-joined
            else:
                lines.append(f"{key}={value}")
        try:
            Path(path).write_text("\n".join(lines), encoding="utf-8")
            self._log(f"Config saved → {path}")
        except Exception as e:
            self._log(f"✗ Save failed: {e}")

    def _load_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Configuration", str(Path.home()), "SatellaOS DEB Config File (*.sdcf)"
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
        except Exception as e:
            self._log(f"✗ Load failed: {e}")
            return
        data = {}
        for line in text.splitlines():
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            data[key.strip()] = value
        for key, edit in self.fields.items():
            if key in data:
                edit.setText(data[key])
        if "extra_files" in data:
            paths = [p for p in data["extra_files"].split("|") if p]
            self._list_set(self.extra_files_list, paths)
        if "extra_folders" in data:
            paths = [p for p in data["extra_folders"].split("|") if p]
            self._list_set(self.extra_folders_list, paths)
        if "architecture" in data:
            self._select_arch(data["architecture"])
        if "create_desktop" in data:
            self.chk_desktop.setChecked(data["create_desktop"].lower() == "true")
        if "terminal_app" in data:
            self.chk_terminal.setChecked(data["terminal_app"].lower() == "true")
        if "post_install" in data:
            decoded = data["post_install"].replace("\\n", "\n").replace("\\\\", "\\")
            self.txt_post.setPlainText(decoded)
        self._log(f"Config loaded ← {path}")

    def _build(self):
        if self._worker and self._worker.isRunning():
            return
        self.log_view.clear()
        self._log("Collecting fields…")
        f = self._collect_fields()
        self._worker = BuildWorker(f)
        self._worker.log_line.connect(self._log)
        self._worker.finished.connect(self._on_done)
        self.btn_build.setEnabled(False)
        self._worker.start()

    def _on_done(self, success: bool, msg: str):
        self.btn_build.setEnabled(True)
        if success:
            self._log(f"✓ Package ready: {msg}")
        else:
            self._log(f"✗ Build failed: {msg}")

    def _log(self, text: str):
        self.log_view.append(text)
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _set_theme(self, dark: bool):
        self.dark_mode = dark
        self._apply_theme()

    def _apply_theme(self):
        p = DARK if self.dark_mode else LIGHT

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {p['bg']};
                color: {p['text']};
                font-family: "Segoe UI", "Noto Sans", sans-serif;
                font-size: 13px;
            }}
            QFrame#log_frame {{
                background-color: {p['panel']};
                border-left: 1px solid {p['accent']};
            }}
            QLabel#field_label {{
                color: {p['text']};
                font-size: 11px;
                margin-top: 4px;
            }}
            QLabel#log_title {{
                color: {p['accent']};
                font-weight: bold;
                font-size: 13px;
                margin-bottom: 4px;
            }}
            QLineEdit#field_edit {{
                background-color: {p['panel']};
                color: {p['text']};
                border: 1px solid {p['accent']}55;
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QLineEdit#field_edit:focus {{
                border: 1px solid {p['accent']};
            }}
            QPushButton#arch_pill_left {{
                background-color: {p['panel']};
                color: {p['text']};
                border: 1px solid {p['accent']}66;
                border-right: none;
                border-top-left-radius: 5px;
                border-bottom-left-radius: 5px;
                border-top-right-radius: 0;
                border-bottom-right-radius: 0;
                font-size: 12px;
                padding: 0 12px;
            }}
            QPushButton#arch_pill_right {{
                background-color: {p['panel']};
                color: {p['text']};
                border: 1px solid {p['accent']}66;
                border-top-left-radius: 0;
                border-bottom-left-radius: 0;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
                font-size: 12px;
                padding: 0 12px;
            }}
            QPushButton#arch_pill_left:checked,
            QPushButton#arch_pill_right:checked {{
                background-color: {p['accent']};
                color: #ffffff;
                border-color: {p['accent']};
            }}
            QPushButton#arch_pill_left:hover:!checked,
            QPushButton#arch_pill_right:hover:!checked {{
                border-color: {p['accent']};
                color: {p['accent']};
            }}
            QTextEdit#field_textedit {{
                background-color: {p['panel']};
                color: {p['text']};
                border: 1px solid {p['accent']}55;
                border-radius: 4px;
                padding: 4px;
            }}
            QTextEdit#log_view {{
                background-color: {p['bg']};
                color: {p['text']};
                border: none;
            }}
            QCheckBox#field_check {{
                color: {p['text']};
                spacing: 6px;
            }}
            QCheckBox#field_check::indicator {{
                width: 14px;
                height: 14px;
                border: 1px solid {p['accent']};
                border-radius: 3px;
                background: {p['panel']};
            }}
            QCheckBox#field_check::indicator:checked {{
                background: {p['accent']};
            }}
            QPushButton#btn_primary {{
                background-color: {p['accent']};
                color: #ffffff;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                padding: 0 16px;
            }}
            QPushButton#btn_primary:hover {{
                background-color: #5a2ea0;
            }}
            QPushButton#btn_primary:disabled {{
                background-color: #444444;
                color: #888888;
            }}
            QPushButton#btn_secondary {{
                background-color: {p['panel']};
                color: {p['text']};
                border: 1px solid {p['accent']}55;
                border-radius: 5px;
                padding: 0 16px;
            }}
            QPushButton#btn_secondary:hover {{
                border-color: {p['accent']};
            }}
            QPushButton#btn_browse {{
                background-color: {p['panel']};
                color: {p['text']};
                border: 1px solid {p['accent']}44;
                border-radius: 4px;
                font-size: 11px;
            }}
            QPushButton#btn_browse:hover {{
                border-color: {p['accent']};
            }}
            QPushButton[flat="true"] {{
                background: transparent;
                border: none;
            }}
            QScrollArea {{
                border: none;
                background-color: {p['bg']};
            }}
            QScrollBar:vertical {{
                background: {p['bg']};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {p['scrollbar']};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    if _cli_args and _cli_args.file:
        _cli_build(_cli_args.file)
        return  # _cli_build calls sys.exit(), but keep for clarity

    app = QApplication(sys.argv)
    app.setApplicationName("SatellaOS Deb Creator")
    win = DebCreator()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()