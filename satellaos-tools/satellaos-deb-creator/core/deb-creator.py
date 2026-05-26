#!/usr/bin/env python3
import subprocess
import os
import sys
import shutil
import stat
import tempfile
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QMessageBox, QFrame, QLineEdit, QTextEdit,
    QFileDialog, QScrollArea, QListWidget, QListWidgetItem, QCheckBox
)
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtCore import Qt, QThread, pyqtSignal


# ── GTK Color Reader ─────────────────────────────────────────────────────────

def get_gtk_colors() -> dict:
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk

        ctx = Gtk.Window().get_style_context()

        def rgba_to_hex(rgba) -> str:
            return "#{:02x}{:02x}{:02x}".format(
                int(rgba.red * 255), int(rgba.green * 255), int(rgba.blue * 255)
            )

        def mix(c1, c2, t):
            r1,g1,b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
            r2,g2,b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
            return "#{:02x}{:02x}{:02x}".format(
                int(r1*(1-t)+r2*t), int(g1*(1-t)+g2*t), int(b1*(1-t)+b2*t)
            )

        def lighten(c, amount): return mix(c, "#ffffff", amount)
        def darken(c, amount):  return mix(c, "#000000", amount)

        bg_raw   = ctx.lookup_color("theme_bg_color")
        fg_raw   = ctx.lookup_color("theme_fg_color")
        sel_raw  = ctx.lookup_color("theme_selected_bg_color")
        base_raw = ctx.lookup_color("theme_base_color")

        bg   = rgba_to_hex(bg_raw[1])   if bg_raw[0]   else "#2b2b2b"
        fg   = rgba_to_hex(fg_raw[1])   if fg_raw[0]   else "#eeeeee"
        sel  = rgba_to_hex(sel_raw[1])  if sel_raw[0]  else "#4a90d9"
        base = rgba_to_hex(base_raw[1]) if base_raw[0] else "#1e1e1e"

        return {
            "BG_DARK":      base,
            "BG_PANEL":     mix(base, bg, 0.4),
            "BG_CARD":      mix(base, bg, 0.2),
            "BG_INPUT":     mix(base, bg, 0.15),
            "ACCENT":       sel,
            "ACCENT_LIGHT": lighten(sel, 0.25),
            "ACCENT_DARK":  darken(sel, 0.15),
            "TEXT_PRIMARY": fg,
            "TEXT_MUTED":   mix(fg, base, 0.45),
            "BORDER":       mix(base, fg, 0.12),
            "BORDER_FOCUS": lighten(sel, 0.1),
            "SUCCESS":      "#4caf50",
            "ERROR":        "#f44336",
            "WARNING":      "#ff9800",
        }
    except Exception as e:
        print(f"[GTK color reading failed]: {e}")
        return {
            "BG_DARK":      "#1e1e1e",
            "BG_PANEL":     "#252525",
            "BG_CARD":      "#2b2b2b",
            "BG_INPUT":     "#222222",
            "ACCENT":       "#4a90d9",
            "ACCENT_LIGHT": "#74b3f5",
            "ACCENT_DARK":  "#3070b9",
            "TEXT_PRIMARY": "#eeeeee",
            "TEXT_MUTED":   "#888888",
            "BORDER":       "#3a3a3a",
            "BORDER_FOCUS": "#5a9ae9",
            "SUCCESS":      "#4caf50",
            "ERROR":        "#f44336",
            "WARNING":      "#ff9800",
        }


# ── Build Worker ──────────────────────────────────────────────────────────────

class BuildWorker(QThread):
    log      = pyqtSignal(str, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, config: dict):
        super().__init__()
        self.config = config

    def _log(self, msg, level="info"):
        self.log.emit(msg, level)

    def run(self):
        cfg  = self.config
        pkg  = cfg["pkg_name"]
        ver  = cfg["version"]
        arch = cfg["arch"]

        build_root = tempfile.mkdtemp(prefix="deb_creator_")
        pkg_dir    = os.path.join(build_root, f"{pkg}_{ver}_{arch}")
        debian_dir = os.path.join(pkg_dir, "DEBIAN")

        try:
            self._log("Creating directory structure…")
            os.makedirs(debian_dir)

            install_share   = cfg.get("install_share", "").strip().rstrip("/") or f"/usr/share/{pkg}"
            install_bin     = cfg.get("install_bin", "").strip().rstrip("/") or "/usr/bin"
            install_icons   = "/usr/share/icons/hicolor/scalable/apps"
            install_desktop = "/usr/share/applications"

            for d in [install_share, install_bin, install_icons, install_desktop]:
                os.makedirs(pkg_dir + d, exist_ok=True)

            # Main script
            if cfg.get("main_script") and os.path.isfile(cfg["main_script"]):
                stype    = cfg.get("script_type", "python")
                cmd_name = cfg.get("cmd_name", "").strip() or pkg
                sname    = os.path.basename(cfg["main_script"])

                if stype == "binary":
                    # Binary: copy directly to install_bin with cmd_name
                    self._log(f"Copying binary: {sname} → {install_bin}/{cmd_name}")
                    bin_dest = pkg_dir + install_bin + "/" + cmd_name
                    shutil.copy2(cfg["main_script"], bin_dest)
                    os.chmod(bin_dest, 0o755)
                    self._log(f"Binary installed: {install_bin}/{cmd_name}", "success")
                else:
                    # Python / Bash: copy to install_share + create wrapper
                    self._log(f"Copying main script: {sname}")
                    script_dest = pkg_dir + install_share + "/" + sname
                    shutil.copy2(cfg["main_script"], script_dest)
                    os.chmod(script_dest, 0o755)
                    wrapper_path = pkg_dir + install_bin + "/" + cmd_name
                    with open(wrapper_path, "w") as f:
                        f.write("#!/usr/bin/env bash\n")
                        if stype == "python":
                            f.write(f'exec python3 {install_share}/{sname} "$@"\n')
                        else:
                            f.write(f'exec bash {install_share}/{sname} "$@"\n')
                    os.chmod(wrapper_path, 0o755)
                    self._log("Wrapper created.", "success")

            # Extra files/folders — each entry: (src, dest_dir, use_subdir)
            for entry in cfg.get("extra_files", []):
                if isinstance(entry, (list, tuple)) and len(entry) == 3:
                    src, dest_dir, use_subdir = entry
                else:
                    # legacy format compatibility
                    src, dest_dir, use_subdir = entry, install_share, True
                dest_dir = os.path.expandvars(os.path.expanduser(dest_dir))

                if os.path.isdir(src):
                    # Directory: copy entire tree preserving structure
                    folder_name = os.path.basename(src.rstrip("/"))
                    if use_subdir:
                        final_dir = pkg_dir + dest_dir.rstrip("/") + "/" + pkg + "/" + folder_name
                    else:
                        final_dir = pkg_dir + dest_dir.rstrip("/") + "/" + folder_name
                    if os.path.exists(final_dir):
                        shutil.rmtree(final_dir)
                    shutil.copytree(src, final_dir)
                    rel = dest_dir.rstrip("/") + ("/" + pkg if use_subdir else "") + "/" + folder_name
                    # Preserve executable bits, set 644 for data files, 755 for dirs
                    for root_d, dirs, files in os.walk(final_dir):
                        os.chmod(root_d, 0o755)
                        for fname in files:
                            fpath = os.path.join(root_d, fname)
                            st = os.stat(fpath).st_mode
                            os.chmod(fpath, 0o755 if (st & 0o111) else 0o644)
                    self._log(f"Extra folder: {folder_name}/  →  {rel}/")
                elif os.path.isfile(src):
                    if use_subdir:
                        final_dir = pkg_dir + dest_dir.rstrip("/") + "/" + pkg
                    else:
                        final_dir = pkg_dir + dest_dir.rstrip("/")
                    os.makedirs(final_dir, exist_ok=True)
                    shutil.copy2(src, os.path.join(final_dir, os.path.basename(src)))
                    rel = dest_dir.rstrip("/") + ("/" + pkg if use_subdir else "") + "/" + os.path.basename(src)
                    self._log(f"Extra file: {os.path.basename(src)}  →  {rel}")
                else:
                    self._log(f"Extra entry not found, skipped: {src}", "warn")

            # Icon
            if cfg.get("icon_path") and os.path.isfile(cfg["icon_path"]):
                ext  = os.path.splitext(cfg["icon_path"])[1]
                dest = pkg_dir + install_icons + f"/{pkg}{ext}"
                shutil.copy2(cfg["icon_path"], dest)
                self._log("Icon copied.")

            # .desktop
            if cfg.get("create_desktop"):
                desktop_path = pkg_dir + install_desktop + f"/{pkg}.desktop"
                terminal = "true" if cfg.get("terminal_app") else "false"
                exec_cmd = cfg.get("cmd_name", "").strip() or pkg
                with open(desktop_path, "w") as f:
                    f.write("[Desktop Entry]\n")
                    f.write(f"Name={cfg.get('app_name', pkg)}\n")
                    f.write(f"Comment={cfg.get('description', '')}\n")
                    f.write(f"Exec={exec_cmd}\n")
                    f.write(f"Icon={pkg}\n")
                    f.write(f"Terminal={terminal}\n")
                    f.write("Type=Application\n")
                    f.write(f"Categories={cfg.get('categories', 'Utility')};\n")
                self._log(".desktop file created.", "success")

            # DEBIAN/control
            self._log("Writing DEBIAN/control…")
            depends = cfg.get("depends", "").strip()
            with open(os.path.join(debian_dir, "control"), "w") as f:
                f.write(f"Package: {pkg}\n")
                f.write(f"Version: {ver}\n")
                f.write(f"Architecture: {arch}\n")
                f.write(f"Maintainer: {cfg.get('maintainer', 'Unknown')}\n")
                if depends:
                    f.write(f"Depends: {depends}\n")
                desc = cfg.get('description', '').strip() or 'No description provided.'
                f.write(f'Description: {desc}\n')

            # DEBIAN/postinst
            postinst_lines = ["#!/usr/bin/env bash", "set -e", ""]
            extra_cmd = cfg.get("postinst_cmd", "").strip()
            if extra_cmd:
                postinst_lines.append(extra_cmd)
                postinst_lines.append("")
            postinst_lines += [
                "if command -v gtk-update-icon-cache &>/dev/null; then",
                "    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true",
                "fi",
                "if command -v update-desktop-database &>/dev/null; then",
                "    update-desktop-database /usr/share/applications 2>/dev/null || true",
                "fi",
                f'echo "{cfg.get("app_name", pkg)} installation completed."',
                "exit 0",
            ]
            postinst_path = os.path.join(debian_dir, "postinst")
            with open(postinst_path, "w") as f:
                f.write("\n".join(postinst_lines) + "\n")
            os.chmod(postinst_path, 0o755)

            # DEBIAN/postrm
            postrm_path = os.path.join(debian_dir, "postrm")
            with open(postrm_path, "w") as f:
                f.write('#!/usr/bin/env bash\nset -e\n')
                f.write('if [ "$1" = "purge" ] || [ "$1" = "remove" ]; then\n')
                f.write('    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true\n')
                f.write('    update-desktop-database /usr/share/applications 2>/dev/null || true\n')
                f.write('fi\nexit 0\n')
            os.chmod(postrm_path, 0o755)

            # dpkg-deb
            output_dir = os.path.expandvars(os.path.expanduser(cfg.get("output_dir") or "~"))
            output_deb = os.path.join(output_dir, f"{pkg}_{ver}_{arch}.deb")
            self._log("Building with dpkg-deb…")

            result = subprocess.run(
                ["dpkg-deb", "--build", "--root-owner-group", pkg_dir, output_deb],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                self._log(f"dpkg-deb error: {result.stderr}", "error")
                self.finished.emit(False, "")
                return

            self._log("Package created successfully!", "success")
            self._log(f"→ {output_deb}", "success")
            self.finished.emit(True, output_deb)

        except Exception as e:
            self._log(f"Unexpected error: {e}", "error")
            self.finished.emit(False, "")
        finally:
            shutil.rmtree(build_root, ignore_errors=True)


# ── Small Widget Helpers ─────────────────────────────────────────────────────

class SectionLabel(QLabel):
    def __init__(self, text, accent_light):
        super().__init__(text)
        self.setStyleSheet(
            f"color: {accent_light}; font-size: 10px; font-weight: bold; "
            f"letter-spacing: 1.5px; margin-top: 12px; margin-bottom: 2px;"
        )


class StyledLineEdit(QLineEdit):
    def __init__(self, placeholder, C, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self._C = C
        self._style(False)

    def focusInEvent(self, e):
        super().focusInEvent(e)
        self._style(True)

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        self._style(False)

    def _style(self, focused):
        border = self._C["BORDER_FOCUS"] if focused else self._C["BORDER"]
        self.setStyleSheet(f"""
            QLineEdit {{
                background: {self._C['BG_INPUT']};
                color: {self._C['TEXT_PRIMARY']};
                border: 1px solid {border};
                border-radius: 5px;
                padding: 6px 10px;
                font-size: 12px;
            }}
        """)


class BrowseRow(QWidget):
    def __init__(self, placeholder, C, mode="file", parent=None):
        super().__init__(parent)
        self._C    = C
        self._mode = mode
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.edit = StyledLineEdit(placeholder, C)
        layout.addWidget(self.edit)
        btn = QPushButton("…")
        btn.setFixedSize(34, 32)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['BG_CARD']}; color: {C['TEXT_PRIMARY']};
                border: 1px solid {C['BORDER']}; border-radius: 5px;
                font-size: 14px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {C['BORDER']}; }}
        """)
        btn.clicked.connect(self._browse)
        layout.addWidget(btn)

    def _browse(self):
        if self._mode == "file":
            path, _ = QFileDialog.getOpenFileName(self, "Select File")
        else:
            path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if path:
            self.edit.setText(path)

    def text(self):  return self.edit.text().strip()
    def setText(self, t): self.edit.setText(t)


def field_wrap(label_text, widget, C):
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(3)
    lbl = QLabel(label_text)
    lbl.setStyleSheet(f"color: {C['TEXT_MUTED']}; font-size: 11px;")
    lay.addWidget(lbl)
    lay.addWidget(widget)
    return w


# ── Main Window ───────────────────────────────────────────────────────────────

class DebCreator(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Deb Creator")
        self.setMinimumSize(1020, 660)
        self.resize(1100, 700)
        self._worker: BuildWorker | None = None
        C = get_gtk_colors()
        self._C = C

        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {C['BG_DARK']};
                color: {C['TEXT_PRIMARY']};
                font-family: "Segoe UI", "Noto Sans", sans-serif;
            }}
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{
                background: {C['BG_DARK']}; width: 6px; border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {C['BORDER']}; border-radius: 3px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QCheckBox {{
                color: {C['TEXT_PRIMARY']}; spacing: 6px; font-size: 12px;
            }}
            QCheckBox::indicator {{
                width: 14px; height: 14px;
                border: 1px solid {C['BORDER']}; border-radius: 3px;
                background: {C['BG_INPUT']};
            }}
            QCheckBox::indicator:checked {{
                background: {C['ACCENT']}; border-color: {C['ACCENT']};
            }}
        """)

        self._build_ui()

    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        C = self._C
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ════════════════════════════════════ LEFT PANEL ═══════════════════════
        left = QFrame()
        left.setObjectName("LP")
        left.setStyleSheet(f"""
            QFrame#LP {{
                background: {C['BG_PANEL']};
                border-right: 1px solid {C['BORDER']};
            }}
        """)
        left.setFixedWidth(640)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        # — form —
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        fw = QWidget(); fw.setStyleSheet("background: transparent;")
        form = QVBoxLayout(fw)
        form.setContentsMargins(20, 14, 20, 20)
        form.setSpacing(7)

        def sec(txt):
            form.addWidget(SectionLabel(txt, C['ACCENT_LIGHT']))

        def linef(lbl, ph, attr):
            w = StyledLineEdit(ph, C)
            setattr(self, attr, w)
            form.addWidget(field_wrap(lbl, w, C))

        def browsef(lbl, ph, attr, mode="file"):
            w = BrowseRow(ph, C, mode=mode)
            setattr(self, attr, w)
            form.addWidget(field_wrap(lbl, w, C))

        # ── Package Information ───────────────────────────────────────
        sec("PACKAGE INFORMATION")
        linef("Package Name  (apt install / purge <this>)", "e.g.: satellaos-papirus-color-manager", "f_pkg")
        linef("Command Name  (to run in terminal)", "e.g.: papirus-color-manager  —  if empty, package name is used", "f_cmd")
        linef("Application Name  (display name)",             "e.g.: Papirus Color Manager",           "f_app")
        linef("Version",                         "e.g.: 1.0.0",                           "f_ver")
        linef("Maintainer",                       "e.g.: Random <random@randomos>",     "f_maint")
        linef("Description",                         "Short package description",                "f_desc")

        # architecture
        arch_w = QWidget()
        al = QVBoxLayout(arch_w); al.setContentsMargins(0,0,0,0); al.setSpacing(3)
        al_lbl = QLabel("Architecture"); al_lbl.setStyleSheet(f"color:{C['TEXT_MUTED']};font-size:11px;")
        al.addWidget(al_lbl)
        ar = QHBoxLayout(); ar.setSpacing(14)
        self.a_amd = QCheckBox("amd64"); self.a_amd.setChecked(True)
        self.a_arm = QCheckBox("arm64")
        self.a_all = QCheckBox("all")
        for cb in [self.a_amd, self.a_arm, self.a_all]:
            ar.addWidget(cb)
        ar.addStretch()
        al.addLayout(ar)
        form.addWidget(arch_w)

        def _only(cb, others):
            def _f(s):
                if s:
                    [o.setChecked(False) for o in others]
            return _f
        self.a_amd.stateChanged.connect(_only(self.a_amd, [self.a_arm, self.a_all]))
        self.a_arm.stateChanged.connect(_only(self.a_arm, [self.a_amd, self.a_all]))
        self.a_all.stateChanged.connect(_only(self.a_all, [self.a_amd, self.a_arm]))

        # ── Files ──────────────────────────────────────────────
        sec("FILES")
        browsef("Main Script",      "Executable .py / .sh / binary…", "f_script", "file")

        # script type selector
        stype_w = QWidget()
        stl = QVBoxLayout(stype_w); stl.setContentsMargins(0,0,0,0); stl.setSpacing(3)
        stl_lbl = QLabel("Script Type"); stl_lbl.setStyleSheet(f"color:{C['TEXT_MUTED']};font-size:11px;")
        stl.addWidget(stl_lbl)
        str_row = QHBoxLayout(); str_row.setSpacing(14)
        self.st_python = QCheckBox("Python 3  (.py)")
        self.st_bash   = QCheckBox("Bash  (.sh)")
        self.st_binary = QCheckBox("Binary / Other")
        self.st_python.setChecked(True)
        for cb in [self.st_python, self.st_bash, self.st_binary]:
            str_row.addWidget(cb)
        str_row.addStretch()
        stl.addLayout(str_row)
        form.addWidget(stype_w)

        def _only_st(cb, others):
            def _f(s):
                if s:
                    [o.setChecked(False) for o in others]
            return _f
        self.st_python.stateChanged.connect(_only_st(self.st_python, [self.st_bash, self.st_binary]))
        self.st_bash.stateChanged.connect(_only_st(self.st_bash,   [self.st_python, self.st_binary]))
        self.st_binary.stateChanged.connect(_only_st(self.st_binary, [self.st_python, self.st_bash]))
        browsef("Icon",           "SVG or PNG icon file…",          "f_icon",   "file")
        browsef("Output Directory",    "Where should the created .deb go?",     "f_outdir", "dir")
        self.f_outdir.setText(os.path.expanduser("~"))

        sec("INSTALL LOCATIONS")
        install_hint = QLabel("Leave empty to use default locations.")
        install_hint.setStyleSheet(f"color:{C['TEXT_MUTED']};font-size:10px;")
        form.addWidget(install_hint)

        self.f_install_share = StyledLineEdit("/usr/share/<package>  —  main files installed here", C)
        form.addWidget(field_wrap("File Install Location  (install_share)", self.f_install_share, C))

        self.f_install_bin = StyledLineEdit("/usr/bin  —  wrapper/binary installed here", C)
        form.addWidget(field_wrap("Binary / Wrapper Location  (install_bin)", self.f_install_bin, C))

        bin_presets = QWidget()
        bpl = QHBoxLayout(bin_presets); bpl.setContentsMargins(0,0,0,0); bpl.setSpacing(6)
        for preset in ["/usr/bin", "/usr/local/bin", "/opt"]:
            pb = QPushButton(preset)
            pb.setStyleSheet(f"""
                QPushButton {{background:{C['BG_CARD']};color:{C['TEXT_MUTED']};
                    border:1px solid {C['BORDER']};border-radius:4px;
                    font-size:10px;padding:3px 8px;}}
                QPushButton:hover {{color:{C['ACCENT_LIGHT']};border-color:{C['ACCENT_LIGHT']};}}
            """)
            pb.clicked.connect(lambda _, p=preset: self.f_install_bin.setText(p))
            bpl.addWidget(pb)
        bpl.addStretch()
        form.addWidget(bin_presets)

        # ── Extra Files ───────────────────────────────────────────
        sec("EXTRA FILES  (optional)")
        extra_hint = QLabel("Target location and subfolder option can be set individually for each file.")
        extra_hint.setStyleSheet(f"color:{C['TEXT_MUTED']};font-size:10px;")
        extra_hint.setWordWrap(True)
        form.addWidget(extra_hint)

        # Data: [(src_path, dest_dir, use_subdir), ...]
        self._extra_entries: list = []

        # List widget
        self.extra_list = QListWidget()
        self.extra_list.setFixedHeight(90)
        self.extra_list.setStyleSheet(f"""
            QListWidget {{background:{C['BG_CARD']};color:{C['TEXT_PRIMARY']};
                border:1px solid {C['BORDER']};border-radius:5px;font-size:11px;}}
            QListWidget::item {{padding:3px 8px;}}
            QListWidget::item:selected {{background:{C['ACCENT']};}}
        """)
        form.addWidget(self.extra_list)

        def _refresh_extra_list():
            self.extra_list.clear()
            for src, dest, subdir in self._extra_entries:
                name = os.path.basename(src.rstrip("/"))
                is_dir = os.path.isdir(src)
                icon = "📁" if is_dir else "📄"
                suffix = "/" if is_dir else ""
                if subdir:
                    final = dest.rstrip("/") + "/<package>/" + name + suffix
                else:
                    final = dest.rstrip("/") + "/" + name + suffix
                self.extra_list.addItem(f"  {icon} {name}{suffix}  →  {final}")

        def _extra_location_dialog(label_text, default_dest="/usr/share"):
            """Shared target-location dialog for files and folders. Returns (dest, use_subdir) or None."""
            from PyQt6.QtWidgets import QDialog, QDialogButtonBox
            dlg = QDialog(self)
            dlg.setWindowTitle("Target Location Settings")
            dlg.setMinimumWidth(420)
            dlg.setStyleSheet(f"""
                QDialog {{background:{C['BG_DARK']};}}
                QLabel {{color:{C['TEXT_PRIMARY']};font-size:12px;}}
                QLineEdit {{background:{C['BG_INPUT']};color:{C['TEXT_PRIMARY']};
                    border:1px solid {C['BORDER']};border-radius:5px;
                    padding:6px 10px;font-size:12px;}}
                QCheckBox {{color:{C['TEXT_PRIMARY']};spacing:6px;font-size:12px;}}
                QCheckBox::indicator {{width:14px;height:14px;
                    border:1px solid {C['BORDER']};border-radius:3px;background:{C['BG_INPUT']};}}
                QCheckBox::indicator:checked {{background:{C['ACCENT']};border-color:{C['ACCENT']};}}
            """)
            dl = QVBoxLayout(dlg); dl.setSpacing(10); dl.setContentsMargins(18,16,18,16)

            src_lbl = QLabel(label_text)
            src_lbl.setStyleSheet(f"color:{C['ACCENT_LIGHT']};font-size:11px;")
            src_lbl.setWordWrap(True)
            dl.addWidget(src_lbl)

            dest_lbl = QLabel("Target Location:")
            dl.addWidget(dest_lbl)

            dest_edit = QLineEdit()
            dest_edit.setText(default_dest)
            dest_edit.setStyleSheet(
                f"background:{C['BG_INPUT']};color:{C['TEXT_PRIMARY']};"
                f"border:1px solid {C['BORDER']};border-radius:5px;padding:6px 10px;font-size:12px;")
            dl.addWidget(dest_edit)

            preset_row = QWidget(); pr_l = QHBoxLayout(preset_row)
            pr_l.setContentsMargins(0,0,0,0); pr_l.setSpacing(6)
            for preset in ["/usr/share", "/usr/share/<package>", "/etc", "/opt"]:
                pb = QPushButton(preset)
                pb.setStyleSheet(f"""
                    QPushButton {{background:{C['BG_CARD']};color:{C['TEXT_MUTED']};
                        border:1px solid {C['BORDER']};border-radius:4px;
                        font-size:10px;padding:3px 7px;}}
                    QPushButton:hover {{color:{C['ACCENT_LIGHT']};border-color:{C['ACCENT_LIGHT']};}}
                """)
                pb.clicked.connect(lambda _, p=preset: dest_edit.setText(p))
                pr_l.addWidget(pb)
            pr_l.addStretch()
            dl.addWidget(preset_row)

            subdir_cb = QCheckBox("Create Subfolder  —  place under <location>/<package-name>/")
            subdir_cb.setChecked(True)
            dl.addWidget(subdir_cb)

            preview_lbl = QLabel()
            preview_lbl.setStyleSheet(f"color:{C['TEXT_MUTED']};font-size:10px;font-style:italic;")
            preview_lbl.setWordWrap(True)
            dl.addWidget(preview_lbl)

            # preview is updated by callers via a closure — store refs so they can call _refresh
            dlg._dest_edit  = dest_edit
            dlg._subdir_cb  = subdir_cb
            dlg._preview_lbl = preview_lbl

            btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            btns.setStyleSheet(f"""
                QPushButton {{background:{C['ACCENT']};color:{C['TEXT_PRIMARY']};
                    border:none;border-radius:5px;padding:6px 20px;font-size:12px;}}
                QPushButton:hover {{background:{C['ACCENT_LIGHT']};}}
                QPushButton[text="Cancel"] {{background:{C['BG_CARD']};color:{C['TEXT_MUTED']};
                    border:1px solid {C['BORDER']};}}
            """)
            btns.accepted.connect(dlg.accept)
            btns.rejected.connect(dlg.reject)
            dl.addWidget(btns)
            return dlg

        def _add_extra():
            paths, _ = QFileDialog.getOpenFileNames(self, "Select files to add")
            if not paths:
                return
            label = "Files to add: " + ", ".join(os.path.basename(p) for p in paths)
            dlg = _extra_location_dialog(label)

            def _update_preview():
                dest = dlg._dest_edit.text().strip().rstrip("/")
                pkg  = self.f_pkg.text().strip() or "<package>"
                base = os.path.basename(paths[0]) if len(paths) == 1 else f"{len(paths)} files"
                if dlg._subdir_cb.isChecked():
                    dlg._preview_lbl.setText(f"→  {dest}/{pkg}/{base}")
                else:
                    dlg._preview_lbl.setText(f"→  {dest}/{base}")
            _update_preview()
            dlg._dest_edit.textChanged.connect(lambda _: _update_preview())
            dlg._subdir_cb.stateChanged.connect(lambda _: _update_preview())

            from PyQt6.QtWidgets import QDialog
            if dlg.exec() == QDialog.DialogCode.Accepted:
                dest = dlg._dest_edit.text().strip().rstrip("/")
                use_subdir = dlg._subdir_cb.isChecked()
                for p in paths:
                    self._extra_entries.append((p, dest, use_subdir))
                _refresh_extra_list()

        def _add_extra_folder():
            from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QAbstractItemView
            from PyQt6.QtCore import QDir

            # Custom multi-folder picker
            picker = QFileDialog(self, "Select folders to add")
            picker.setFileMode(QFileDialog.FileMode.Directory)
            picker.setOption(QFileDialog.Option.DontUseNativeDialog, True)
            picker.setOption(QFileDialog.Option.ShowDirsOnly, True)

            # Enable multi-selection on the internal list/tree view
            for view in picker.findChildren(QAbstractItemView):
                view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

            picker.setStyleSheet(f"""
                QDialog, QFileDialog {{background:{C['BG_DARK']};color:{C['TEXT_PRIMARY']};}}
                QWidget {{background:{C['BG_DARK']};color:{C['TEXT_PRIMARY']};}}
                QListView, QTreeView {{background:{C['BG_CARD']};color:{C['TEXT_PRIMARY']};
                    border:1px solid {C['BORDER']};}}
                QListView::item:selected, QTreeView::item:selected {{background:{C['ACCENT']};}}
                QLineEdit {{background:{C['BG_INPUT']};color:{C['TEXT_PRIMARY']};
                    border:1px solid {C['BORDER']};border-radius:4px;padding:4px 8px;}}
                QPushButton {{background:{C['BG_CARD']};color:{C['TEXT_PRIMARY']};
                    border:1px solid {C['BORDER']};border-radius:4px;padding:4px 12px;}}
                QPushButton:hover {{background:{C['BORDER']};}}
                QComboBox {{background:{C['BG_CARD']};color:{C['TEXT_PRIMARY']};
                    border:1px solid {C['BORDER']};border-radius:4px;padding:3px 8px;}}
                QHeaderView::section {{background:{C['BG_PANEL']};color:{C['TEXT_MUTED']};
                    border:none;padding:4px;}}
                QLabel {{color:{C['TEXT_PRIMARY']};}}
                QSplitter::handle {{background:{C['BORDER']};}}
                QScrollBar:vertical {{background:{C['BG_CARD']};width:10px;}}
                QScrollBar::handle:vertical {{background:{C['BORDER']};border-radius:4px;}}
            """)

            if picker.exec() != QDialog.DialogCode.Accepted:
                return

            folders = picker.selectedFiles()
            # Filter: keep only actual directories
            folders = [f for f in folders if os.path.isdir(f)]
            if not folders:
                return

            if len(folders) == 1:
                label = f"📁  Folder to add: {os.path.basename(folders[0].rstrip('/'))}"
            else:
                label = f"📁  {len(folders)} folders to add: " + ", ".join(
                    os.path.basename(f.rstrip("/")) for f in folders
                )

            dlg = _extra_location_dialog(label)

            def _update_preview():
                dest = dlg._dest_edit.text().strip().rstrip("/")
                pkg  = self.f_pkg.text().strip() or "<package>"
                if len(folders) == 1:
                    fname = os.path.basename(folders[0].rstrip("/"))
                    if dlg._subdir_cb.isChecked():
                        dlg._preview_lbl.setText(f"→  {dest}/{pkg}/{fname}/")
                    else:
                        dlg._preview_lbl.setText(f"→  {dest}/{fname}/")
                else:
                    if dlg._subdir_cb.isChecked():
                        dlg._preview_lbl.setText(f"→  {dest}/{pkg}/<folder-name>/  × {len(folders)}")
                    else:
                        dlg._preview_lbl.setText(f"→  {dest}/<folder-name>/  × {len(folders)}")
            _update_preview()
            dlg._dest_edit.textChanged.connect(lambda _: _update_preview())
            dlg._subdir_cb.stateChanged.connect(lambda _: _update_preview())

            if dlg.exec() == QDialog.DialogCode.Accepted:
                dest = dlg._dest_edit.text().strip().rstrip("/")
                use_subdir = dlg._subdir_cb.isChecked()
                for folder in folders:
                    self._extra_entries.append((folder, dest, use_subdir))
                _refresh_extra_list()

        def _remove_extra():
            row = self.extra_list.currentRow()
            if row >= 0:
                self._extra_entries.pop(row)
                _refresh_extra_list()

        # Button row
        ebr = QWidget(); ebl = QHBoxLayout(ebr)
        ebl.setContentsMargins(0,0,0,0); ebl.setSpacing(6)

        add_btn = QPushButton("+ Add File")
        add_btn.setStyleSheet(f"""
            QPushButton {{background:{C['BG_CARD']};color:{C['ACCENT_LIGHT']};
                border:1px solid {C['BORDER']};border-radius:4px;padding:4px 12px;font-size:11px;}}
            QPushButton:hover {{background:{C['BORDER']};}}
        """)
        add_folder_btn = QPushButton("📁 Add Folder")
        add_folder_btn.setStyleSheet(f"""
            QPushButton {{background:{C['BG_CARD']};color:{C['ACCENT_LIGHT']};
                border:1px solid {C['BORDER']};border-radius:4px;padding:4px 12px;font-size:11px;}}
            QPushButton:hover {{background:{C['BORDER']};}}
        """)
        rem_btn = QPushButton("Remove Selected")
        rem_btn.setStyleSheet(f"""
            QPushButton {{background:transparent;color:{C['TEXT_MUTED']};border:none;font-size:11px;padding:4px 8px;}}
            QPushButton:hover {{color:{C['ERROR']};}}
        """)
        clr_btn = QPushButton("Clear")
        clr_btn.setStyleSheet(f"""
            QPushButton {{background:transparent;color:{C['TEXT_MUTED']};border:none;font-size:11px;padding:4px 8px;}}
            QPushButton:hover {{color:{C['ERROR']};}}
        """)
        ebl.addWidget(add_btn); ebl.addWidget(add_folder_btn)
        ebl.addWidget(rem_btn); ebl.addWidget(clr_btn); ebl.addStretch()
        form.addWidget(ebr)

        add_btn.clicked.connect(_add_extra)
        add_folder_btn.clicked.connect(_add_extra_folder)
        rem_btn.clicked.connect(_remove_extra)

        def _clear_extra():
            self._extra_entries.clear()
            _refresh_extra_list()
        clr_btn.clicked.connect(_clear_extra)

        # ── Dependencies ─────────────────────────────────────────
        sec("DEPENDENCIES  (Depends:)")
        dep_hint = QLabel("Comma-separated package names. Can be left empty.")
        dep_hint.setStyleSheet(f"color:{C['TEXT_MUTED']};font-size:10px;")
        form.addWidget(dep_hint)
        self.f_deps = QTextEdit()
        self.f_deps.setFixedHeight(58)
        self.f_deps.setPlaceholderText("e.g.: python3, python3-gi, python3-pyqt6, papirus-icon-theme")
        self.f_deps.setStyleSheet(f"""
            QTextEdit {{background:{C['BG_INPUT']};color:{C['TEXT_PRIMARY']};
                border:1px solid {C['BORDER']};border-radius:5px;
                padding:6px 10px;font-size:12px;}}
        """)
        form.addWidget(self.f_deps)

        # ── Options ────────────────────────────────────────────
        sec("OPTIONS")
        self.f_desktop  = QCheckBox("Create .desktop file  (appear in application menu)")
        self.f_desktop.setChecked(True)
        self.f_terminal = QCheckBox("Terminal application  (Terminal=true)")
        form.addWidget(self.f_desktop)
        form.addWidget(self.f_terminal)
        # ── Categories ──────────────────────────────────────────
        # Main categories (at least one required — to appear in menu)
        MAIN_CATS = [
            ("AudioVideo",   "Audio && Video"),
            ("Development",  "Development"),
            ("Education",    "Education"),
            ("Game",         "Game"),
            ("Graphics",     "Graphics"),
            ("HealthFitness","Health && Fitness"),
            ("Network",      "Network"),
            ("Office",       "Office"),
            ("Science",      "Science"),
            ("Settings",     "Settings"),
            ("System",       "System"),
            ("Utility",      "Utility"),
        ]
        # Sub categories (additional to main category, optional) — sorted alphabetically by label
        SUB_CATS = [
            ("2DGraphics",             "2D Graphics"),
            ("3DGraphics",             "3D Graphics"),
            ("Accessibility",          "Accessibility"),
            ("ActionGame",             "Action Game"),
            ("AdventureGame",          "Adventure Game"),
            ("ArcadeGame",             "Arcade Game"),
            ("Archiving",              "Archiving"),
            ("Art",                    "Art"),
            ("ArtificialIntelligence", "Artificial Intelligence"),
            ("Astronomy",              "Astronomy"),
            ("Audio",                  "Audio"),
            ("Backup",                 "Backup"),
            ("Biology",                "Biology"),
            ("BoardGame",              "Board Game"),
            ("Calculator",             "Calculator"),
            ("Calendar",               "Calendar"),
            ("CardGame",               "Card Game"),
            ("Chat",                   "Chat"),
            ("Chemistry",              "Chemistry"),
            ("Clock",                  "Clock"),
            ("ComputerScience",        "Computer Science"),
            ("Compression",            "Compression"),
            ("Construction",           "Construction"),
            ("ContactManagement",      "Contact Management"),
            ("DataVisualization",      "Data Visualization"),
            ("Database",               "Database"),
            ("Debugger",               "Debugger"),
            ("Dictionary",             "Dictionary"),
            ("DiscBurning",            "Disc Burning"),
            ("Documentation",          "Documentation"),
            ("Economy",                "Economy"),
            ("Electricity",            "Electricity"),
            ("Email",                  "Email"),
            ("Emulator",               "Emulator"),
            ("Engineering",            "Engineering"),
            ("FileManager",            "File Manager"),
            ("FileTools",              "File Tools"),
            ("Finance",                "Finance"),
            ("FlowChart",              "Flow Chart"),
            ("GTK",                    "GTK"),
            ("GUIDesigner",            "GUI Designer"),
            ("Geography",              "Geography"),
            ("IDE",                    "IDE"),
            ("KidsGame",               "Kids Game"),
            ("Languages",              "Languages"),
            ("LogicGame",              "Logic Game"),
            ("Maps",                   "Maps"),
            ("Math",                   "Math"),
            ("Monitor",                "Monitor"),
            ("Music",                  "Music"),
            ("News",                   "News"),
            ("OCR",                    "OCR"),
            ("P2P",                    "P2P"),
            ("PackageManager",         "Package Manager"),
            ("ParallelComputing",      "Parallel Computing"),
            ("Photography",            "Photography"),
            ("Physics",                "Physics"),
            ("Player",                 "Player"),
            ("Presentation",           "Presentation"),
            ("Printing",               "Printing"),
            ("Profiling",              "Profiling"),
            ("Publishing",             "Publishing"),
            ("Qt",                     "Qt"),
            ("RasterGraphics",         "Raster Graphics"),
            ("Recorder",               "Recorder"),
            ("RemoteAccess",           "Remote Access"),
            ("RevisionControl",        "Revision Control"),
            ("Robotics",               "Robotics"),
            ("RolePlaying",            "Role Playing"),
            ("Scanning",               "Scanning"),
            ("Security",               "Security"),
            ("Shooter",                "Shooter"),
            ("Simulation",             "Simulation"),
            ("SportsGame",             "Sports Game"),
            ("Spreadsheet",            "Spreadsheet"),
            ("StrategyGame",           "Strategy Game"),
            ("Telephony",              "Telephony"),
            ("TerminalEmulator",       "Terminal Emulator"),
            ("TextEditor",             "Text Editor"),
            ("Translation",            "Translation"),
            ("VectorGraphics",         "Vector Graphics"),
            ("Video",                  "Video"),
            ("Viewer",                 "Viewer"),
            ("WebBrowser",             "Web Browser"),
            ("WordProcessor",          "Word Processor"),
        ]
        ALL_CATS = MAIN_CATS + SUB_CATS

        self._cat_selected: set = set()
        self._cat_buttons: dict = {}

        def _chip_style(selected, is_main=False):
            if selected:
                bg  = C["ACCENT"] if not is_main else C["ACCENT"]
                brd = C["ACCENT"]
                fg  = C["TEXT_PRIMARY"]
                hbg = C["ACCENT_LIGHT"]
                return (f"QPushButton {{background:{bg};color:{fg};"
                        f"border:1px solid {brd};border-radius:4px;"
                        f"font-size:11px;font-weight:bold;padding:3px 9px;}}"
                        f"QPushButton:hover {{background:{hbg};border-color:{hbg};}}")
            else:
                fg  = C["TEXT_PRIMARY"] if is_main else C["TEXT_MUTED"]
                return (f"QPushButton {{background:{C['BG_DARK']};color:{fg};"
                        f"border:1px solid {C['BORDER']};border-radius:4px;"
                        f"font-size:11px;padding:3px 9px;}}"
                        f"QPushButton:hover {{color:{C['TEXT_PRIMARY']};border-color:{C['TEXT_MUTED']};}}")

        def _update_cats_field():
            all_keys = {k for k, _ in ALL_CATS}
            manual_raw = self.f_cats.text()
            manual_parts = [p.strip() for p in manual_raw.replace(";", " ").split() if p.strip()]
            manual_only = [p for p in manual_parts if p not in all_keys]
            # Main categories first, sub categories next, manual last
            main_keys = [k for k, _ in MAIN_CATS]
            sub_keys  = [k for k, _ in SUB_CATS]
            ordered = ([k for k in main_keys if k in self._cat_selected] +
                       [k for k in sub_keys  if k in self._cat_selected] +
                       manual_only)
            self.f_cats.setText(";".join(ordered))

        def _make_toggle(key, btn, is_main):
            def _toggle():
                if key in self._cat_selected:
                    self._cat_selected.discard(key)
                    btn.setStyleSheet(_chip_style(False, is_main))
                else:
                    self._cat_selected.add(key)
                    btn.setStyleSheet(_chip_style(True, is_main))
                _update_cats_field()
            return _toggle

        def _build_chip_row(parent_layout, cats, is_main):
            ROW_SIZE = 4 if is_main else 5
            row_w = row_l = None
            for i, (key, label) in enumerate(cats):
                if i % ROW_SIZE == 0:
                    row_w = QWidget(); row_w.setStyleSheet("background:transparent;")
                    row_l = QHBoxLayout(row_w)
                    row_l.setContentsMargins(0,0,0,0); row_l.setSpacing(5)
                    parent_layout.addWidget(row_w)
                btn = QPushButton(label)
                btn.setStyleSheet(_chip_style(False, is_main))
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                self._cat_buttons[key] = (btn, is_main)
                btn.clicked.connect(_make_toggle(key, btn, is_main))
                row_l.addWidget(btn)
            if row_l: row_l.addStretch()

        # Text box (top)
        cat_wrap = QWidget()
        cat_wrap_l = QVBoxLayout(cat_wrap)
        cat_wrap_l.setContentsMargins(0,0,0,0); cat_wrap_l.setSpacing(4)

        cat_field_lbl = QLabel("Categories (.desktop)")
        cat_field_lbl.setStyleSheet(f"color:{C['TEXT_MUTED']};font-size:11px;")
        cat_wrap_l.addWidget(cat_field_lbl)

        self.f_cats = StyledLineEdit("Select or type manually…", C)
        cat_wrap_l.addWidget(self.f_cats)
        form.addWidget(cat_wrap)

        # Main categories section
        main_lbl = QLabel("MAIN CATEGORY  —  at least one must be selected")
        main_lbl.setStyleSheet(
            f"color:{C['ACCENT_LIGHT']};font-size:10px;font-weight:bold;"
            f"letter-spacing:1px;margin-top:8px;margin-bottom:2px;")
        form.addWidget(main_lbl)

        main_container = QWidget()
        main_container.setStyleSheet(
            f"background:{C['BG_CARD']};border:1px solid {C['BORDER']};border-radius:6px;")
        main_grid = QVBoxLayout(main_container)
        main_grid.setContentsMargins(8,8,8,8); main_grid.setSpacing(5)
        _build_chip_row(main_grid, MAIN_CATS, True)
        form.addWidget(main_container)

        # Sub categories section
        sub_lbl = QLabel("SUB CATEGORY  —  optional")
        sub_lbl.setStyleSheet(
            f"color:{C['TEXT_MUTED']};font-size:10px;font-weight:bold;"
            f"letter-spacing:1px;margin-top:6px;margin-bottom:2px;")
        form.addWidget(sub_lbl)

        sub_container = QWidget()
        sub_container.setStyleSheet(
            f"background:{C['BG_CARD']};border:1px solid {C['BORDER']};border-radius:6px;")
        sub_grid = QVBoxLayout(sub_container)
        sub_grid.setContentsMargins(8,8,8,8); sub_grid.setSpacing(5)
        _build_chip_row(sub_grid, SUB_CATS, False)
        form.addWidget(sub_container)

        # Text box ↔ chip synchronization
        def _sync_chips_from_text():
            parts = set(p.strip() for p in self.f_cats.text().replace(";", " ").split() if p.strip())
            for key, (btn, is_main) in self._cat_buttons.items():
                sel = key in parts
                if sel: self._cat_selected.add(key)
                else:   self._cat_selected.discard(key)
                btn.setStyleSheet(_chip_style(sel, is_main))
        self.f_cats.textEdited.connect(_sync_chips_from_text)

        # ── postinst ──────────────────────────────────────────────
        sec("POST-INSTALLATION COMMAND  (postinst — optional)")
        self.f_postinst = QTextEdit()
        self.f_postinst.setFixedHeight(50)
        self.f_postinst.setPlaceholderText("e.g.: systemctl daemon-reload")
        self.f_postinst.setStyleSheet(f"""
            QTextEdit {{background:{C['BG_INPUT']};color:{C['TEXT_PRIMARY']};
                border:1px solid {C['BORDER']};border-radius:5px;
                padding:6px 10px;font-size:12px;font-family:monospace;}}
        """)
        form.addWidget(self.f_postinst)
        form.addStretch()

        scroll.setWidget(fw)
        ll.addWidget(scroll)

        # — build footer —
        foot = QWidget()
        foot.setFixedHeight(68)
        foot.setStyleSheet(f"background:{C['BG_CARD']};border-top:1px solid {C['BORDER']};")
        fl = QHBoxLayout(foot); fl.setContentsMargins(20, 12, 20, 12); fl.setSpacing(10)

        self.build_btn = QPushButton("  BUILD  .DEB")
        self.build_btn.setFixedHeight(44)
        self.build_btn.setStyleSheet(f"""
            QPushButton {{background:{C['ACCENT']};color:{C['TEXT_PRIMARY']};
                border:none;border-radius:6px;font-size:13px;font-weight:bold;
                letter-spacing:1px;padding:0 28px;}}
            QPushButton:hover  {{background:{C['ACCENT_LIGHT']};}}
            QPushButton:pressed {{background:{C['ACCENT_DARK']};}}
            QPushButton:disabled {{background:{C['BORDER']};color:{C['TEXT_MUTED']};}}
        """)
        self.build_btn.clicked.connect(self._start_build)
        fl.addWidget(self.build_btn)

        rst_btn = QPushButton("Reset")
        rst_btn.setFixedHeight(44)
        rst_btn.setStyleSheet(f"""
            QPushButton {{background:transparent;color:{C['TEXT_MUTED']};
                border:1px solid {C['BORDER']};border-radius:6px;
                font-size:12px;padding:0 16px;}}
            QPushButton:hover {{color:{C['TEXT_PRIMARY']};border-color:{C['TEXT_MUTED']};}}
        """)
        rst_btn.clicked.connect(self._reset)
        fl.addWidget(rst_btn)

        cfg_btn_style = f"""
            QPushButton {{background:transparent;color:{C['TEXT_MUTED']};
                border:1px solid {C['BORDER']};border-radius:6px;
                font-size:11px;font-weight:bold;letter-spacing:0.5px;padding:0 10px;}}
            QPushButton:hover {{color:{C['ACCENT_LIGHT']};border-color:{C['ACCENT_LIGHT']};}}
        """

        save_btn = QPushButton("SAVE")
        save_btn.setFixedHeight(44)
        save_btn.setToolTip("Save Configuration")
        save_btn.setStyleSheet(cfg_btn_style)
        save_btn.clicked.connect(self._save_config)
        fl.addWidget(save_btn)

        load_btn = QPushButton("LOAD")
        load_btn.setFixedHeight(44)
        load_btn.setToolTip("Load Configuration")
        load_btn.setStyleSheet(cfg_btn_style)
        load_btn.clicked.connect(self._load_config)
        fl.addWidget(load_btn)

        ll.addWidget(foot)

        root.addWidget(left)

        # ════════════════════════════════════ RIGHT PANEL ═══════════════════════
        right = QWidget()
        right.setStyleSheet(f"background:{C['BG_DARK']};")
        rl = QVBoxLayout(right); rl.setContentsMargins(0,0,0,0); rl.setSpacing(0)

        log_hdr = QWidget()
        log_hdr.setFixedHeight(64)
        log_hdr.setStyleSheet(f"background:{C['BG_CARD']};border-bottom:1px solid {C['BORDER']};")
        lhl = QHBoxLayout(log_hdr); lhl.setContentsMargins(20,0,20,0)
        lt = QLabel("BUILD LOG")
        lt.setStyleSheet(f"color:{C['ACCENT_LIGHT']};font-size:13px;font-weight:bold;letter-spacing:2px;")
        lhl.addWidget(lt); lhl.addStretch()
        clrlog = QPushButton("Clear")
        clrlog.setStyleSheet(f"background:transparent;color:{C['TEXT_MUTED']};border:none;font-size:11px;")
        clrlog.clicked.connect(lambda: self.log_area.clear())
        lhl.addWidget(clrlog)
        rl.addWidget(log_hdr)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet(f"""
            QTextEdit {{
                background:{C['BG_DARK']};color:{C['TEXT_PRIMARY']};
                border:none;padding:14px 18px;
                font-family:"JetBrains Mono","Fira Code","Courier New",monospace;
                font-size:12px;
            }}
        """)
        rl.addWidget(self.log_area)

        self.status_bar = QLabel("Ready.")
        self.status_bar.setFixedHeight(28)
        self.status_bar.setStyleSheet(
            f"background:{C['BG_CARD']};color:{C['TEXT_MUTED']};"
            f"font-size:10px;padding:0 16px;border-top:1px solid {C['BORDER']};"
        )
        rl.addWidget(self.status_bar)
        root.addWidget(right, stretch=1)

        self._log("Deb Creator ready.", "info")
        self._log("Fill in the form and click BUILD .DEB button.", "info")

    # ── Helpers ───────────────────────────────────────────────────────────

    def _arch(self):
        if self.a_arm.isChecked(): return "arm64"
        if self.a_all.isChecked(): return "all"
        return "amd64"

    def _script_type(self):
        if self.st_bash.isChecked():   return "bash"
        if self.st_binary.isChecked(): return "binary"
        return "python"

    def _cat_btn_style_off(self):
        C = self._C
        return f"""QPushButton {{
            background:{C['BG_DARK']};color:{C['TEXT_MUTED']};
            border:1px solid {C['BORDER']};border-radius:4px;
            font-size:11px;padding:3px 9px;}}
        QPushButton:hover {{color:{C['TEXT_PRIMARY']};border-color:{C['TEXT_MUTED']};}}"""

    def _normalize_depends(self, raw: str) -> str:
        """Accepts spaces, commas, or mixed separators and converts to standard 'a, b, c' format."""
        import re
        parts = [p.strip() for p in re.split(r"[,\s]+", raw) if p.strip()]
        return ", ".join(parts)

    def _log(self, msg, level="info"):
        C = self._C
        col = {"info": C["TEXT_MUTED"], "success": C["SUCCESS"],
               "error": C["ERROR"], "warn": C["WARNING"]}.get(level, C["TEXT_PRIMARY"])
        pre = {"info": "  ·  ", "success": "  ✓  ",
               "error": "  ✗  ", "warn":  "  ⚠  "}.get(level, "     ")
        self.log_area.append(
            f'<span style="color:{col};font-family:monospace;">{pre}{msg}</span>'
        )
        self.log_area.moveCursor(QTextCursor.MoveOperation.End)

    def _set_status(self, msg, color=None):
        C = self._C
        c = color or C["TEXT_MUTED"]
        self.status_bar.setStyleSheet(
            f"background:{C['BG_CARD']};color:{c};font-size:10px;"
            f"padding:0 16px;border-top:1px solid {C['BORDER']};"
        )
        self.status_bar.setText(msg)

    def _reset(self):
        for a in ["f_pkg","f_cmd","f_app","f_ver","f_maint","f_desc","f_cats"]:
            getattr(self, a).clear()
        self.f_script.setText("")
        self.f_icon.setText("")
        self.f_outdir.setText(os.path.expanduser("~"))
        self.f_deps.clear(); self.f_postinst.clear(); self._extra_entries.clear(); self.extra_list.clear()
        self.a_amd.setChecked(True); self.a_arm.setChecked(False); self.a_all.setChecked(False)
        self.f_desktop.setChecked(True); self.f_terminal.setChecked(False)
        self.st_python.setChecked(True); self.st_bash.setChecked(False); self.st_binary.setChecked(False)
        self.f_install_share.clear(); self.f_install_bin.clear()
        self.f_cats.clear(); self._cat_selected.clear()
        for key, (btn, is_main) in self._cat_buttons.items():
            C = self._C
            btn.setStyleSheet(
                f"QPushButton {{background:{C['BG_DARK']};color:{ C['TEXT_PRIMARY'] if is_main else C['TEXT_MUTED']};"
                f"border:1px solid {C['BORDER']};border-radius:4px;font-size:11px;padding:3px 9px;}}"
                f"QPushButton:hover {{color:{C['TEXT_PRIMARY']};border-color:{C['TEXT_MUTED']};}}"
            )
        self._log("Form reset.", "info")

    # ── Save / Load Configuration ──────────────────────────────────────────

    def _collect_config(self) -> dict:
        return {
            "pkg_name":       self.f_pkg.text().strip(),
            "cmd_name":       self.f_cmd.text().strip(),
            "app_name":       self.f_app.text().strip(),
            "version":        self.f_ver.text().strip(),
            "maintainer":     self.f_maint.text().strip(),
            "description":    self.f_desc.text().strip(),
            "categories":     self.f_cats.text().strip(),
            "arch":           self._arch(),
            "script_type":    self._script_type(),
            "main_script":    self.f_script.text(),
            "icon_path":      self.f_icon.text(),
            "output_dir":     self.f_outdir.text(),
            "depends":        self._normalize_depends(self.f_deps.toPlainText()),
            "postinst_cmd":   self.f_postinst.toPlainText().strip(),
            "create_desktop": self.f_desktop.isChecked(),
            "terminal_app":   self.f_terminal.isChecked(),
            "extra_files":    list(self._extra_entries),
            "install_share":  self.f_install_share.text().strip(),
            "install_bin":    self.f_install_bin.text().strip(),
        }

    def _apply_config(self, cfg: dict):
        self.f_pkg.setText(cfg.get("pkg_name", ""))
        self.f_cmd.setText(cfg.get("cmd_name", ""))
        self.f_app.setText(cfg.get("app_name", ""))
        self.f_ver.setText(cfg.get("version", ""))
        self.f_maint.setText(cfg.get("maintainer", ""))
        self.f_desc.setText(cfg.get("description", ""))
        self.f_cats.setText(cfg.get("categories", ""))
        self.f_script.setText(cfg.get("main_script", ""))
        self.f_icon.setText(cfg.get("icon_path", ""))
        self.f_outdir.setText(cfg.get("output_dir", os.path.expanduser("~")))
        self.f_deps.setPlainText(cfg.get("depends", ""))
        self.f_postinst.setPlainText(cfg.get("postinst_cmd", ""))
        self.f_desktop.setChecked(cfg.get("create_desktop", True))
        self.f_terminal.setChecked(cfg.get("terminal_app", False))

        arch = cfg.get("arch", "amd64")
        self.a_amd.setChecked(arch == "amd64")
        self.a_arm.setChecked(arch == "arm64")
        self.a_all.setChecked(arch == "all")

        stype = cfg.get("script_type", "python")
        self.st_python.setChecked(stype == "python")
        self.st_bash.setChecked(stype == "bash")
        self.st_binary.setChecked(stype == "binary")

        self._extra_entries = []
        for entry in cfg.get("extra_files", []):
            if isinstance(entry, (list, tuple)) and len(entry) == 3:
                self._extra_entries.append(tuple(entry))
            elif isinstance(entry, str):
                self._extra_entries.append((entry, "/usr/share", True))
        # refresh list — _refresh_extra_list depends on form, repeat inline
        self.extra_list.clear()
        for src, dest, subdir in self._extra_entries:
            pkg = self.f_pkg.text().strip() or "<package>"
            final = (dest.rstrip("/") + "/" + pkg + "/" + os.path.basename(src)
                     if subdir else dest.rstrip("/") + "/" + os.path.basename(src))
            self.extra_list.addItem(f"  {os.path.basename(src)}  →  {final}")
        self.f_install_share.setText(cfg.get("install_share", ""))
        self.f_install_bin.setText(cfg.get("install_bin", ""))
        # sync chips with text
        cats_text = cfg.get("categories", "")
        parts = set(p.strip() for p in cats_text.replace(";", " ").split() if p.strip())
        self._cat_selected = set()
        C = self._C
        for key, (btn, is_main) in self._cat_buttons.items():
            sel = key in parts
            if sel: self._cat_selected.add(key)
            if sel:
                style = (f"QPushButton {{background:{C['ACCENT']};color:{C['TEXT_PRIMARY']};"
                         f"border:1px solid {C['ACCENT']};border-radius:4px;"
                         f"font-size:11px;font-weight:bold;padding:3px 9px;}}"
                         f"QPushButton:hover {{background:{C['ACCENT_LIGHT']};border-color:{C['ACCENT_LIGHT']};}}")
            else:
                fg = C['TEXT_PRIMARY'] if is_main else C['TEXT_MUTED']
                style = (f"QPushButton {{background:{C['BG_DARK']};color:{fg};"
                         f"border:1px solid {C['BORDER']};border-radius:4px;"
                         f"font-size:11px;padding:3px 9px;}}"
                         f"QPushButton:hover {{color:{C['TEXT_PRIMARY']};border-color:{C['TEXT_MUTED']};}}")
            btn.setStyleSheet(style)

    def _save_config(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration",
            os.path.expanduser("~"),
            "Deb Config (*.sdcfg);;JSON (*.json)"
        )
        if not path:
            return
        if not (path.endswith(".sdcfg") or path.endswith(".json")):
            path += ".sdcfg"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._collect_config(), f, ensure_ascii=False, indent=2)
            self._log(f"Configuration saved → {path}", "success")
            self._set_status(f"✓  Saved: {os.path.basename(path)}", self._C["SUCCESS"])
        except Exception as e:
            self._log(f"Save error: {e}", "error")

    def _load_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Configuration",
            os.path.expanduser("~"),
            "Deb Config (*.sdcfg);;JSON (*.json);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self._apply_config(cfg)
            self._log(f"Configuration loaded → {path}", "success")
            self._set_status(f"✓  Loaded: {os.path.basename(path)}", self._C["SUCCESS"])
        except Exception as e:
            self._log(f"Load error: {e}", "error")
            QMessageBox.critical(self, "Error", f"Configuration could not be loaded:\n{e}")

    # ── Build ─────────────────────────────────────────────────────────────────

    def _start_build(self):
        pkg = self.f_pkg.text().strip()
        ver = self.f_ver.text().strip()
        if not pkg or not ver:
            QMessageBox.warning(self, "Missing Field", "Package name and version are required.")
            return

        config = {
            "pkg_name":       pkg,
            "app_name":       self.f_app.text().strip() or pkg,
            "version":        ver,
            "arch":           self._arch(),
            "script_type":    self._script_type(),
            "cmd_name":       self.f_cmd.text().strip(),
            "maintainer":     self.f_maint.text().strip() or "Unknown",
            "description":    self.f_desc.text().strip(),
            "main_script":    self.f_script.text(),
            "icon_path":      self.f_icon.text(),
            "output_dir":     self.f_outdir.text() or os.path.expanduser("~"),
            "depends":        self._normalize_depends(self.f_deps.toPlainText()),
            "postinst_cmd":   self.f_postinst.toPlainText().strip(),
            "create_desktop": self.f_desktop.isChecked(),
            "terminal_app":   self.f_terminal.isChecked(),
            "categories":     self.f_cats.text().strip() or "Utility",
            "extra_files":    list(self._extra_entries),
            "install_share":  self.f_install_share.text().strip(),
            "install_bin":    self.f_install_bin.text().strip(),
        }

        self.build_btn.setEnabled(False)
        self.build_btn.setText("  Building…")
        self._set_status("Build in progress…", self._C["WARNING"])
        self._log("─" * 38, "info")
        self._log(f"Build: {pkg}  v{ver}  [{config['arch']}]", "info")

        self._worker = BuildWorker(config)
        self._worker.log.connect(self._log)
        self._worker.finished.connect(self._on_done)
        self._worker.start()

    def _on_done(self, success, out):
        self.build_btn.setEnabled(True)
        self.build_btn.setText("  BUILD  .DEB")
        if success:
            self._set_status(f"✓  {out}", self._C["SUCCESS"])
            self._log("─" * 38, "success")
            QMessageBox.information(self, "Completed",
                f"Package created:\n\n{out}\n\nTo install:\n  sudo apt install \"{out}\"")
        else:
            self._set_status("✗  Build failed.", self._C["ERROR"])
            self._log("Build failed. Check the log.", "error")
            QMessageBox.critical(self, "Error", "Package could not be created.\nCheck the log.")


# ── CLI Build ─────────────────────────────────────────────────────────────────

def _cli_build(args) -> int:
    """Build a .deb from a config file without launching the GUI. Returns exit code."""

    config_path = args.file
    quiet       = args.quiet
    dry_run     = args.dry_run

    def out(msg, level="info"):
        if quiet and level == "info":
            return
        prefix = {"success": "  ✓ ", "error": "  ✗ ", "warn": "  ! "}.get(level, "    ")
        stream = sys.stderr if level == "error" else sys.stdout
        print(f"{prefix}{msg}", file=stream)

    if not os.path.isfile(config_path):
        print(f"[error] Config file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        print(f"[error] Could not read config: {e}", file=sys.stderr)
        return 1

    # ── Apply CLI overrides ────────────────────────────────────────────────────
    if args.pkg_name:
        cfg["pkg_name"] = args.pkg_name
    if args.version:
        cfg["version"] = args.version
    if args.arch:
        cfg["arch"] = args.arch
    if args.output:
        cfg["output_dir"] = args.output
    if args.no_desktop:
        cfg["create_desktop"] = False

    # ── Validate required fields ───────────────────────────────────────────────
    pkg = cfg.get("pkg_name", "").strip()
    ver = cfg.get("version", "").strip()
    arch = cfg.get("arch", "amd64").strip()

    if not pkg or not ver:
        print("[error] Config is missing 'pkg_name' or 'version'.", file=sys.stderr)
        return 1

    # Normalize depends (same logic as GUI)
    raw_deps = cfg.get("depends", "")
    if isinstance(raw_deps, list):
        cfg["depends"] = ", ".join(raw_deps)
    else:
        cfg["depends"] = raw_deps

    output_dir = os.path.expandvars(os.path.expanduser(cfg.get("output_dir") or "~"))
    output_deb = os.path.join(output_dir, f"{pkg}_{ver}_{arch}.deb")

    # ── Dry-run: just print what would happen and exit ─────────────────────────
    if dry_run:
        print("─" * 50)
        print("  [DRY RUN]  No package will be built.")
        print("─" * 50)
        print(f"  Config      : {config_path}")
        print(f"  Package     : {pkg}")
        print(f"  Version     : {ver}")
        print(f"  Arch        : {arch}")
        print(f"  Maintainer  : {cfg.get('maintainer', 'Unknown')}")
        print(f"  Description : {cfg.get('description', '—')}")
        print(f"  Script type : {cfg.get('script_type', '—')}")
        print(f"  Main script : {cfg.get('main_script', '—')}")
        print(f"  Depends     : {cfg.get('depends', '—') or '—'}")
        print(f"  Desktop file: {'yes' if cfg.get('create_desktop') else 'no'}")
        print(f"  Output      : {output_deb}")
        extra = cfg.get("extra_files", [])
        if extra:
            print(f"  Extra files : {len(extra)} entry/entries")
            for e in extra:
                if isinstance(e, (list, tuple)) and len(e) == 3:
                    print(f"    {e[0]}  →  {e[1]}")
                else:
                    print(f"    {e}")
        print("─" * 50)
        print("  Dry run complete. Use without --dry-run to build.")
        return 0

    # ── Normal build ───────────────────────────────────────────────────────────
    if not quiet:
        print("─" * 50)
        print(f"  Building : {pkg}  v{ver}  [{arch}]")
        print(f"  Config   : {config_path}")
        print(f"  Output   : {output_deb}")
        print("─" * 50)

    success_flag = [False]
    output_path  = [""]

    class _CLIWorker(BuildWorker):
        def _log(self, msg, level="info"):
            out(msg, level)

    worker = _CLIWorker(cfg)

    def _on_finished(ok, o):
        success_flag[0] = ok
        output_path[0]  = o

    worker.finished.connect(_on_finished)

    # Run synchronously — BuildWorker.run() is plain Python, no event loop needed
    worker.run()

    print("─" * 50)
    if success_flag[0]:
        print(f"  ✓  Package created: {output_path[0]}")
        print(f"     Install with  : sudo apt install \"{output_path[0]}\"")
        # ── Auto-install ───────────────────────────────────────────────────────
        if args.install:
            print("─" * 50)
            print("  Running: sudo apt install ...")
            ret = subprocess.run(
                ["sudo", "apt", "install", "-y", output_path[0]]
            ).returncode
            if ret == 0:
                print("  ✓  Installation successful.")
            else:
                print("  ✗  Installation failed (apt returned non-zero).", file=sys.stderr)
                return 1
        return 0
    else:
        print("  ✗  Build failed.", file=sys.stderr)
        return 1


# ── Argument Parser ───────────────────────────────────────────────────────────

def _build_parser() -> "argparse.ArgumentParser":
    import argparse

    parser = argparse.ArgumentParser(
        prog="deb-creator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Deb Creator\n"
            "─────────────────────────────────────────────\n"
            "GUI mode  :  run with no arguments\n"
            "CLI mode  :  run with -f / --file <config>\n"
        ),
        epilog=(
            "examples:\n"
            "  # Open GUI\n"
            "  python3 deb-creator.py\n"
            "\n"
            "  # Build from config\n"
            "  python3 deb-creator.py -f myapp.sdcfg\n"
            "\n"
            "  # Override version and output directory\n"
            "  python3 deb-creator.py -f myapp.sdcfg --version 2.1.0 -o ~/packages\n"
            "\n"
            "  # Preview what would happen without building\n"
            "  python3 deb-creator.py -f myapp.sdcfg --dry-run\n"
            "\n"
            "  # Build quietly, then auto-install\n"
            "  python3 deb-creator.py -f myapp.sdcfg -q --install\n"
            "\n"
            "  # Override arch for cross-packaging\n"
            "  python3 deb-creator.py -f myapp.sdcfg --arch arm64\n"
            "\n"
            "config file format:\n"
            "  .sdcfg / .json — save from the GUI via File → Save Configuration\n"
            "  CLI overrides (--version, --arch, etc.) take priority over the config file.\n"
        )
    )

    # ── Required for CLI ───────────────────────────────────────────────────────
    parser.add_argument(
        "-f", "--file",
        metavar="CONFIG",
        help="path to a .sdcfg or .json config file  (required for CLI mode)"
    )

    # ── Output override ────────────────────────────────────────────────────────
    parser.add_argument(
        "-o", "--output",
        metavar="DIR",
        help="output directory for the .deb file  (overrides config)"
    )

    # ── Package metadata overrides ─────────────────────────────────────────────
    override = parser.add_argument_group("config overrides")
    override.add_argument(
        "--version",
        metavar="VER",
        help="package version string, e.g. 1.2.0  (overrides config)"
    )
    override.add_argument(
        "--arch",
        metavar="ARCH",
        choices=["amd64", "arm64", "armhf", "i386", "all"],
        help="target architecture  (overrides config)  choices: amd64 arm64 armhf i386 all"
    )
    override.add_argument(
        "--pkg-name",
        metavar="NAME",
        help="package name  (overrides config)"
    )
    override.add_argument(
        "--no-desktop",
        action="store_true",
        help="skip .desktop file creation even if config enables it"
    )

    # ── Behaviour flags ────────────────────────────────────────────────────────
    behaviour = parser.add_argument_group("behaviour")
    behaviour.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="suppress info-level log lines; only show warnings, errors and the final result"
    )
    behaviour.add_argument(
        "--dry-run",
        action="store_true",
        help="parse and validate config, print a summary, then exit without building"
    )
    behaviour.add_argument(
        "--install",
        action="store_true",
        help="after a successful build run 'sudo apt install' on the produced .deb"
    )

    return parser


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = _build_parser()

    # Positional-arg backwards-compat:
    # old usage: python3 deb-creator.py mypackage.sdcfg
    # Detect this case (single arg that looks like a file, not a flag) and
    # transparently redirect to --file so existing scripts don't break.
    if len(sys.argv) == 2 and not sys.argv[1].startswith("-"):
        sys.argv = [sys.argv[0], "--file", sys.argv[1]]

    args = parser.parse_args()

    # No arguments → GUI mode
    if args.file is None and not args.dry_run:
        app = QApplication(sys.argv)
        app.setFont(QFont("Segoe UI", 10))
        win = DebCreator()
        win.show()
        sys.exit(app.exec())

    # CLI mode — require --file
    if args.file is None:
        parser.error("--file / -f is required in CLI mode")

    sys.exit(_cli_build(args))