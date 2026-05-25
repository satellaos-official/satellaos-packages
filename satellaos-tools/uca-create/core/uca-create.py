#!/usr/bin/env python3
"""
uca-create-v3.py — Thunar Custom Actions (uca.xml) Generator
GUI + CLI modes.

GUI mode  :  python3 uca-create-v3.py
CLI mode  :  python3 uca-create-v3.py --cli [number(s) | all]
             e.g.  python3 uca-create-v3.py --cli all
             e.g.  python3 uca-create-v3.py --cli 1 3 9 12
"""

import os
import sys
import subprocess


# ── Action definitions ────────────────────────────────────────────────────────

ACTIONS = {
    1: {
        "name":    "Open Terminal Here",
        "submenu": "",
        "group":   None,
        "xml": """\t<action>
\t\t<icon>utilities-terminal</icon>
\t\t<name>Open Terminal Here</name>
\t\t<submenu></submenu>
\t\t<unique-id>1769597937281634-1</unique-id>
\t\t<command>exo-open --working-directory %f --launch TerminalEmulator</command>
\t\t<description>Open terminal in the selected folder</description>
\t\t<range></range>
\t\t<patterns>*</patterns>
\t\t<startup-notify/>
\t\t<directories/>
\t</action>""",
    },
    2: {
        "name":    "Open as Root",
        "submenu": "",
        "group":   None,
        "xml": """\t<action>
\t\t<icon>folder-violet</icon>
\t\t<name>Open as Root</name>
\t\t<submenu></submenu>
\t\t<unique-id>1770219086580287-1</unique-id>
\t\t<command>pkexec thunar %F</command>
\t\t<description>Open the folder with administration privileges</description>
\t\t<range></range>
\t\t<patterns>*</patterns>
\t\t<directories/>
\t</action>""",
    },
    3: {
        "name":    "Create a Link",
        "submenu": "",
        "group":   None,
        "xml": """\t<action>
\t\t<icon>emblem-symbolic-link</icon>
\t\t<name>Create a Link</name>
\t\t<submenu></submenu>
\t\t<unique-id>1770219212901542-2</unique-id>
\t\t<command>ln -s %f &apos;Link to %n&apos;</command>
\t\t<description>Create a symbolic link for each selected item</description>
\t\t<range></range>
\t\t<patterns>*</patterns>
\t\t<directories/>
\t\t<other-files/>
\t</action>""",
    },
    4: {
        "name":    "Verify (ISO files)",
        "submenu": "",
        "group":   None,
        "xml": """\t<action>
\t\t<icon>view-certificate</icon>
\t\t<name>Verify (ISO files)</name>
\t\t<submenu></submenu>
\t\t<unique-id>1770219273064615-3</unique-id>
\t\t<command>mint-iso-verify %f</command>
\t\t<description>Verify the authenticity and integrity of the image</description>
\t\t<range></range>
\t\t<patterns>*.iso;*.ISO</patterns>
\t\t<audio-files/>
\t\t<image-files/>
\t\t<other-files/>
\t\t<video-files/>
\t</action>""",
    },
    5: {
        "name":    "Share with LocalSend",
        "submenu": "",
        "group":   None,
        "xml": """\t<action>
\t\t<icon>localsend_app</icon>
\t\t<name>Share with LocalSend</name>
\t\t<submenu></submenu>
\t\t<unique-id>1772531131988710-1</unique-id>
\t\t<command>localsend_app %F || flatpak run org.localsend.localsend_app %F</command>
\t\t<description>Send selected files to local devices via LocalSend</description>
\t\t<range>*</range>
\t\t<patterns>*</patterns>
\t\t<directories/>
\t\t<audio-files/>
\t\t<image-files/>
\t\t<other-files/>
\t\t<text-files/>
\t\t<video-files/>
\t</action>""",
    },
    6: {
        "name":    "Run Python Script",
        "submenu": "Python",
        "group":   "Python",
        "xml": """\t<action>
\t\t<icon>python</icon>
\t\t<name>Run Python Script</name>
\t\t<submenu>Python</submenu>
\t\t<unique-id>1776434918635266-6</unique-id>
\t\t<command>xfce4-terminal --hold --command=DQUOT;python3 %fDQUOT;</command>
\t\t<description>Run Python script in terminal (keeps terminal open)</description>
\t\t<range>*</range>
\t\t<patterns>*.py</patterns>
\t\t<other-files/>
\t\t<text-files/>
\t</action>""",
    },
    7: {
        "name":    "Run Python Script (No Log)",
        "submenu": "Python",
        "group":   "Python",
        "xml": """\t<action>
\t\t<icon>python</icon>
\t\t<name>Run Python Script (No Log)</name>
\t\t<submenu>Python</submenu>
\t\t<unique-id>1776433126123484-1</unique-id>
\t\t<command>xfce4-terminal -e DQUOT;python3 %fDQUOT;</command>
\t\t<description>Run Python script in terminal (closes when done)</description>
\t\t<range>*</range>
\t\t<patterns>*.py</patterns>
\t\t<other-files/>
\t\t<text-files/>
\t</action>""",
    },
    8: {
        "name":    "Run Python Script (No Terminal)",
        "submenu": "Python",
        "group":   "Python",
        "xml": """\t<action>
\t\t<icon>python</icon>
\t\t<name>Run Python Script (No Terminal)</name>
\t\t<submenu>Python</submenu>
\t\t<unique-id>1776434918635266-8</unique-id>
\t\t<command>python3 %f</command>
\t\t<description>Run Python script directly without opening a terminal</description>
\t\t<range>*</range>
\t\t<patterns>*.py</patterns>
\t\t<other-files/>
\t\t<text-files/>
\t</action>""",
    },
    9: {
        "name":    "Run Bash Script",
        "submenu": "Bash",
        "group":   "Bash",
        "xml": """\t<action>
\t\t<icon>utilities-terminal</icon>
\t\t<name>Run Bash Script</name>
\t\t<submenu>Bash</submenu>
\t\t<unique-id>1776434619126830-5</unique-id>
\t\t<command>xfce4-terminal --hold --command=DQUOT;bash %fDQUOT;</command>
\t\t<description>Run Bash script in terminal (keeps terminal open)</description>
\t\t<range>*</range>
\t\t<patterns>*.sh</patterns>
\t\t<other-files/>
\t\t<text-files/>
\t</action>""",
    },
    10: {
        "name":    "Run Bash Script (No Log)",
        "submenu": "Bash",
        "group":   "Bash",
        "xml": """\t<action>
\t\t<icon>utilities-terminal</icon>
\t\t<name>Run Bash Script (No Log)</name>
\t\t<submenu>Bash</submenu>
\t\t<unique-id>1776433216082635-2</unique-id>
\t\t<command>xfce4-terminal -e DQUOT;bash %fDQUOT;</command>
\t\t<description>Run Bash script in terminal (closes when done)</description>
\t\t<range>*</range>
\t\t<patterns>*.sh</patterns>
\t\t<other-files/>
\t\t<text-files/>
\t</action>""",
    },
    11: {
        "name":    "Run Bash Script (No Terminal)",
        "submenu": "Bash",
        "group":   "Bash",
        "xml": """\t<action>
\t\t<icon>utilities-terminal</icon>
\t\t<name>Run Bash Script (No Terminal)</name>
\t\t<submenu>Bash</submenu>
\t\t<unique-id>1776433216082635-11</unique-id>
\t\t<command>bash %f</command>
\t\t<description>Run Bash script directly without opening a terminal</description>
\t\t<range>*</range>
\t\t<patterns>*.sh</patterns>
\t\t<other-files/>
\t\t<text-files/>
\t</action>""",
    },
    12: {
        "name":    "Install .deb Package",
        "submenu": "Debian",
        "group":   "Debian",
        "xml": """\t<action>
\t\t<icon>distributor-logo-debian</icon>
\t\t<name>Install .deb Package</name>
\t\t<submenu>Debian</submenu>
\t\t<unique-id>1776433572647529-3</unique-id>
\t\t<command>xfce4-terminal --hold --command=DQUOT;sudo apt install --no-install-recommends -y %fDQUOT;</command>
\t\t<description>Install Debian package (keeps terminal open)</description>
\t\t<range>*</range>
\t\t<patterns>*.deb</patterns>
\t\t<other-files/>
\t\t<text-files/>
\t</action>""",
    },
    13: {
        "name":    "Install .deb Package (No Log)",
        "submenu": "Debian",
        "group":   "Debian",
        "xml": """\t<action>
\t\t<icon>distributor-logo-debian</icon>
\t\t<name>Install .deb Package (No Log)</name>
\t\t<submenu>Debian</submenu>
\t\t<unique-id>1776434074190285-4</unique-id>
\t\t<command>xfce4-terminal -e DQUOT;sudo apt install --no-install-recommends -y %fDQUOT;</command>
\t\t<description>Install Debian package (closes when done)</description>
\t\t<range>*</range>
\t\t<patterns>*.deb</patterns>
\t\t<other-files/>
\t\t<text-files/>
\t</action>""",
    },
    14: {
        "name":    "Edit with Nano",
        "submenu": "",
        "group":   None,
        "xml": """\t<action>
\t\t<icon>accessories-text-editor</icon>
\t\t<name>Edit with Nano</name>
\t\t<submenu></submenu>
\t\t<unique-id>1776434074190285-14</unique-id>
\t\t<command>xfce4-terminal --hold --command=DQUOT;nano %fDQUOT;</command>
\t\t<description>Edit file with nano in terminal</description>
\t\t<range>*</range>
\t\t<patterns>*</patterns>
\t\t<other-files/>
\t\t<text-files/>
\t</action>""",
    },
}

GROUPS = [
    (None,     [1, 2, 3, 4, 5, 14]),
    ("Python", [6, 7, 8]),
    ("Bash",   [9, 10, 11]),
    ("Debian", [12, 13]),
]


# ── XML writer ────────────────────────────────────────────────────────────────

def write_xml(selected: list[int]) -> tuple[bool, str, bool]:
    output_dir  = os.path.expanduser("~/.config/Thunar")
    output_file = os.path.join(output_dir, "uca.xml")
    skel_dir    = "/etc/skel/.config/Thunar"
    skel_file   = os.path.join(skel_dir, "uca.xml")

    os.makedirs(output_dir, exist_ok=True)

    lines = ['<?xml version="1.0" encoding="UTF-8"?>\n', "<actions>\n"]
    for num in sorted(selected):
        lines.append(ACTIONS[num]["xml"].replace("DQUOT;", "&quot;") + "\n")
    lines.append("</actions>\n")

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except OSError as e:
        return False, str(e), False

    try:
        result = subprocess.run(
            ["pkexec", "sh", "-c",
             f"mkdir -p '{skel_dir}' && cp '{output_file}' '{skel_file}'"],
            capture_output=True
        )
        skel_ok = result.returncode == 0
    except Exception:
        skel_ok = False

    return True, output_file, skel_ok


# ── CLI mode ──────────────────────────────────────────────────────────────────

CYAN   = "\033[1;36m"
GREEN  = "\033[1;32m"
YELLOW = "\033[1;33m"
RED    = "\033[0;31m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def run_whiptail_checklist() -> list[str] | None:
    """Runs whiptail checklist dialog and returns selected tokens."""
    cmd = [
        "whiptail", "--title", "Thunar Custom Actions Generator",
        "--checklist", "\nEklenecek eylemleri boşluk (Space) tuşu ile seçin:",
        "20", "75", "14"
    ]
    
    # Generate checklist items (Tag, Item, Status) without submenu/group icons
    for num, data in ACTIONS.items():
        cmd.extend([str(num), data["name"], "OFF"])
        
    try:
        # Whiptail outputs the selection to stderr
        result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            # Parse output like "1" "3" "9" or 1 3 9
            output = result.stderr.strip().replace('"', '')
            return output.split()
        else:
            # User cancelled or hit ESC
            return None
    except FileNotFoundError:
        # Whiptail is not installed, fallback to classic text input
        return None

def cli_main(args: list[str]) -> int:
    # If parameters (like numbers or 'all') are passed directly in command line, skip whiptail
    if args:
        raw_input = " ".join(args)
        raw_input = raw_input.replace(",", " ")
        if raw_input.strip().lower() == "all":
            tokens = [str(n) for n in ACTIONS.keys()]
        else:
            tokens = raw_input.split()
    else:
        # Interactive mode: Try whiptail first
        tokens = run_whiptail_checklist()
        
        # Fallback to pure text mode if whiptail is cancelled or missing
        if tokens is None:
            print(f"{CYAN}╔══════════════════════════════════════════════════════╗{RESET}")
            print(f"{CYAN}║       Thunar Custom Actions Generator (uca.xml)      ║{RESET}")
            print(f"{CYAN}╚══════════════════════════════════════════════════════╝{RESET}")
            print()
            print(f"{BOLD}Select the actions you want to add.{RESET}")
            print(f"{YELLOW}Separate multiple numbers with spaces or commas.{RESET}")
            print(f"{YELLOW}To select all actions type: {BOLD}all{RESET}")
            print()
            print(f"{GREEN}┌────────────────────────────────────────────────────────────────────────┐{RESET}")
            print(f"{GREEN}│  #   Action Name                                                       │{RESET}")
            print(f"{GREEN}├────────────────────────────────────────────────────────────────────────┤{RESET}")
            for num, data in ACTIONS.items():
                sub = f"[submenu: {data['group']}]" if data["group"] else ""
                print(f"{GREEN}│ {num:2})  {data['name']:<45} {sub:<20}│{RESET}")
            print(f"{GREEN}└────────────────────────────────────────────────────────────────────────┘{RESET}")
            print()
            raw_input = input(f"{BOLD}Your selection: {RESET}").strip()
            raw_input = raw_input.replace(",", " ")
            if raw_input.strip().lower() == "all":
                tokens = [str(n) for n in ACTIONS.keys()]
            else:
                tokens = raw_input.split()

    valid   = []
    invalid = []
    for t in tokens:
        if t.isdigit() and 1 <= int(t) <= 14:
            n = int(t)
            if n not in valid:
                valid.append(n)
        else:
            invalid.append(t)

    if invalid:
        print()
        print(f"{RED}Invalid selection(s) ignored: {' '.join(invalid)}{RESET}")

    if not valid:
        print()
        print(f"{RED}No valid selection made. Exiting.{RESET}")
        return 1

    valid.sort()

    success, output_file, skel_ok = write_xml(valid)

    if not success:
        print(f"\n{RED}✗  Failed to write uca.xml: {output_file}{RESET}")
        return 1

    print()
    print(f"{CYAN}══════════════════════════════════════════════════════{RESET}")
    print(f"{GREEN}✔  uca.xml generated successfully!{RESET}")
    print(f"{CYAN}══════════════════════════════════════════════════════{RESET}")
    print()
    print(f"{BOLD}Actions added:{RESET}")
    for num in valid:
        sub = f"[submenu: {ACTIONS[num]['group']}]" if ACTIONS[num]["group"] else ""
        print(f"  {GREEN}✔{RESET}  {num}) {ACTIONS[num]['name']} {sub}")

    skel_path = "/etc/skel/.config/Thunar/uca.xml"
    print()
    print(f"{YELLOW}📄 File location: {output_file}{RESET}")
    if skel_ok:
        print(f"{YELLOW}📄 File location: {skel_path}{RESET}")
    else:
        print(f"{RED}⚠  Could not write to {skel_path} (requires root){RESET}")
    print()
    print(f"{BOLD}To restart Thunar:{RESET}")
    print(f"  {CYAN}thunar -q && thunar &{RESET}")
    print()
    return 0


# ── GTK color reader (shared with GUI) ───────────────────────────────────────

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
            r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
            r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
            return "#{:02x}{:02x}{:02x}".format(
                int(r1 * (1 - t) + r2 * t),
                int(g1 * (1 - t) + g2 * t),
                int(b1 * (1 - t) + b2 * t),
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
    except Exception:
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


# ── GUI mode ──────────────────────────────────────────────────────────────────

def gui_main():
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
        QLabel, QPushButton, QCheckBox, QFrame, QScrollArea, QMessageBox,
    )
    from PyQt6.QtCore import Qt

    C = get_gtk_colors()

    class UCACreator(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Thunar Custom Actions Generator")
            self.setMinimumSize(700, 560)
            self._checkboxes: dict[int, QCheckBox] = {}
            self._apply_global_style()
            self._build_ui()

        def _apply_global_style(self):
            self.setStyleSheet(f"""
                QMainWindow, QWidget#central {{
                    background-color: {C['BG_DARK']};
                }}
                QFrame#left_panel {{
                    background-color: {C['BG_PANEL']};
                    border: 1px solid {C['BORDER']};
                    border-radius: 8px;
                }}
                QFrame#right_panel {{
                    background-color: {C['BG_PANEL']};
                    border: 1px solid {C['BORDER']};
                    border-radius: 8px;
                }}
                QFrame#group_card {{
                    background-color: {C['BG_CARD']};
                    border: 1px solid {C['BORDER']};
                    border-radius: 6px;
                }}
                QCheckBox {{
                    color: {C['TEXT_PRIMARY']};
                    font-size: 13px;
                    spacing: 8px;
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border: 1px solid {C['BORDER']};
                    border-radius: 3px;
                    background-color: {C['BG_INPUT']};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {C['ACCENT']};
                    border-color: {C['ACCENT']};
                }}
                QCheckBox::indicator:hover {{
                    border-color: {C['ACCENT_LIGHT']};
                }}
                QLabel {{ color: {C['TEXT_PRIMARY']}; }}
                QScrollArea {{ border: none; background: transparent; }}
                QScrollBar:vertical {{
                    background: {C['BG_DARK']};
                    width: 8px;
                    border-radius: 4px;
                }}
                QScrollBar::handle:vertical {{
                    background: {C['BORDER']};
                    border-radius: 4px;
                    min-height: 20px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: {C['TEXT_MUTED']};
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
            """)

        def _build_ui(self):
            central = QWidget(objectName="central")
            self.setCentralWidget(central)
            root = QHBoxLayout(central)
            root.setContentsMargins(14, 14, 14, 14)
            root.setSpacing(12)

            left = QFrame(objectName="left_panel")
            left.setFixedWidth(360)
            left_layout = QVBoxLayout(left)
            left_layout.setContentsMargins(12, 12, 12, 12)
            left_layout.setSpacing(10)

            hdr = QLabel("ACTIONS")
            hdr.setStyleSheet(
                f"color: {C['ACCENT_LIGHT']}; font-size: 10px; font-weight: bold; "
                f"letter-spacing: 1px;"
            )
            left_layout.addWidget(hdr)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll_widget = QWidget()
            scroll_widget.setStyleSheet(f"background: transparent;")
            scroll_layout = QVBoxLayout(scroll_widget)
            scroll_layout.setContentsMargins(0, 0, 4, 0)
            scroll_layout.setSpacing(8)

            for group_name, ids in GROUPS:
                card = QFrame(objectName="group_card")
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(10, 8, 10, 8)
                card_layout.setSpacing(4)

                if group_name:
                    lbl = QLabel(group_name.upper())
                    lbl.setStyleSheet(
                        f"color: {C['ACCENT_LIGHT']}; font-size: 9px; "
                        f"font-weight: bold; letter-spacing: 1px;"
                    )
                    card_layout.addWidget(lbl)

                for num in ids:
                    cb = QCheckBox(ACTIONS[num]["name"])
                    cb.setChecked(False)
                    self._checkboxes[num] = cb
                    card_layout.addWidget(cb)

                scroll_layout.addWidget(card)

            scroll_layout.addStretch()
            scroll.setWidget(scroll_widget)
            left_layout.addWidget(scroll)

            btn_row = QWidget()
            btn_row.setStyleSheet("background: transparent;")
            btn_row_layout = QHBoxLayout(btn_row)
            btn_row_layout.setContentsMargins(0, 0, 0, 0)
            btn_row_layout.setSpacing(8)

            for label, checked in [("Select All", True), ("Deselect All", False)]:
                b = QPushButton(label)
                b.setFixedHeight(30)
                state = checked
                b.setStyleSheet(self._btn_style_secondary())
                b.clicked.connect(lambda _, s=state: self._set_all(s))
                btn_row_layout.addWidget(b)

            left_layout.addWidget(btn_row)
            root.addWidget(left)

            right = QFrame(objectName="right_panel")
            right_layout = QVBoxLayout(right)
            right_layout.setContentsMargins(14, 14, 14, 14)
            right_layout.setSpacing(12)

            title = QLabel("uca.xml Generator")
            title.setStyleSheet(
                f"color: {C['ACCENT_LIGHT']}; font-size: 18px; font-weight: bold;"
            )
            title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            right_layout.addWidget(title)

            subtitle = QLabel("Thunar Custom Actions for Debian / XFCE")
            subtitle.setStyleSheet(f"color: {C['TEXT_MUTED']}; font-size: 11px;")
            subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            right_layout.addWidget(subtitle)

            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet(f"color: {C['BORDER']};")
            right_layout.addWidget(sep)

            self.summary_label = QLabel("No actions selected.")
            self.summary_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            self.summary_label.setWordWrap(True)
            self.summary_label.setStyleSheet(
                f"color: {C['TEXT_MUTED']}; font-size: 12px; "
                f"background: {C['BG_CARD']}; border: 1px solid {C['BORDER']}; "
                f"border-radius: 6px; padding: 10px;"
            )
            self.summary_label.setMinimumHeight(160)
            right_layout.addWidget(self.summary_label, stretch=1)

            self.status_label = QLabel("")
            self.status_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.status_label.setStyleSheet(
                f"color: {C['TEXT_MUTED']}; font-size: 12px; font-style: italic;"
            )
            right_layout.addWidget(self.status_label)

            self.path_label = QLabel("")
            self.path_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.path_label.setWordWrap(True)
            self.path_label.setStyleSheet(
                f"color: {C['TEXT_MUTED']}; font-size: 11px;"
            )
            right_layout.addWidget(self.path_label)

            right_layout.addStretch()

            self.gen_btn = QPushButton("  GENERATE  uca.xml")
            self.gen_btn.setFixedHeight(46)
            self.gen_btn.setStyleSheet(self._btn_style_primary())
            self.gen_btn.clicked.connect(self._generate)
            right_layout.addWidget(self.gen_btn)

            root.addWidget(right, stretch=1)

            for cb in self._checkboxes.values():
                cb.stateChanged.connect(self._update_summary)

        def _btn_style_primary(self) -> str:
            return (
                f"QPushButton {{"
                f"  background-color: {C['ACCENT']}; color: {C['TEXT_PRIMARY']};"
                f"  border: none; border-radius: 6px; font-weight: bold;"
                f"  font-size: 13px; padding: 0 16px;"
                f"}}"
                f"QPushButton:hover {{ background-color: {C['ACCENT_LIGHT']}; }}"
                f"QPushButton:disabled {{ background-color: {C['BORDER']}; color: {C['TEXT_MUTED']}; }}"
            )

        def _btn_style_secondary(self) -> str:
            return (
                f"QPushButton {{"
                f"  background-color: {C['BG_DARK']}; color: {C['TEXT_MUTED']};"
                f"  border: 1px solid {C['BORDER']}; border-radius: 5px;"
                f"  font-size: 11px; padding: 4px 10px;"
                f"}}"
                f"QPushButton:hover {{ color: {C['TEXT_PRIMARY']}; border-color: {C['TEXT_MUTED']}; }}"
            )

        def _set_all(self, state: bool):
            for cb in self._checkboxes.values():
                cb.setChecked(state)

        def _selected(self) -> list[int]:
            return sorted(n for n, cb in self._checkboxes.items() if cb.isChecked())

        def _update_summary(self):
            sel = self._selected()
            self.status_label.setText("")
            self.path_label.setText("")
            if not sel:
                self.summary_label.setText("No actions selected.")
                self.summary_label.setStyleSheet(
                    f"color: {C['TEXT_MUTED']}; font-size: 12px; "
                    f"background: {C['BG_CARD']}; border: 1px solid {C['BORDER']}; "
                    f"border-radius: 6px; padding: 10px;"
                )
                return

            lines = [f"<b style='color:{C['ACCENT_LIGHT']}'>Selected ({len(sel)}):</b><br>"]
            for num in sel:
                a = ACTIONS[num]
                sub = f" <span style='color:{C['TEXT_MUTED']}'>→ {a['group']}</span>" if a["group"] else ""
                lines.append(
                    f"&nbsp;&nbsp;<span style='color:{C['SUCCESS']}'>✔</span>&nbsp;"
                    f"<span style='color:{C['TEXT_PRIMARY']}'>{num}) {a['name']}</span>{sub}<br>"
                )
            self.summary_label.setText("".join(lines))
            self.summary_label.setStyleSheet(
                f"color: {C['TEXT_PRIMARY']}; font-size: 12px; "
                f"background: {C['BG_CARD']}; border: 1px solid {C['BORDER']}; "
                f"border-radius: 6px; padding: 10px;"
            )

        def _generate(self):
            sel = self._selected()
            if not sel:
                QMessageBox.warning(self, "No Selection", "Please select at least one action.")
                return

            self.gen_btn.setEnabled(False)
            self.gen_btn.setText("  Writing…")
            self.status_label.setText("Generating uca.xml…")
            self.status_label.setStyleSheet(
                f"color: {C['WARNING']}; font-size: 12px; font-style: italic;"
            )

            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()

            success, output_file, skel_ok = write_xml(sel)

            self.gen_btn.setEnabled(True)
            self.gen_btn.setText("  GENERATE  uca.xml")

            if not success:
                self.status_label.setText(f"✗  Error: {output_file}")
                self.status_label.setStyleSheet(
                    f"color: {C['ERROR']}; font-size: 12px; font-style: italic;"
                )
                QMessageBox.critical(self, "Error", f"Could not write uca.xml:\n\n{output_file}")
                return

            self.status_label.setText("✔  uca.xml generated successfully!")
            self.status_label.setStyleSheet(
                f"color: {C['SUCCESS']}; font-size: 12px; font-style: italic;"
            )

            skel_path = "/etc/skel/.config/Thunar/uca.xml"
            path_text = f"📄 {output_file}"
            if skel_ok:
                path_text += f"\n📄 {skel_path}"
            else:
                path_text += f"\n⚠  {skel_path} not written (requires root)"
            self.path_label.setText(path_text)
            self.path_label.setStyleSheet(
                f"color: {C['TEXT_MUTED']}; font-size: 11px;"
            )

            msg = (
                f"{len(sel)} action(s) written to:\n{output_file}\n\n"
                + (f"Also copied to:\n{skel_path}\n\n" if skel_ok else "")
                + "Restart Thunar to apply:\n  thunar -q && thunar &"
            )
            QMessageBox.information(self, "Done", msg)

    app = __import__("PyQt6.QtWidgets", fromlist=["QApplication"]).QApplication(sys.argv)
    app.setFont(__import__("PyQt6.QtGui", fromlist=["QFont"]).QFont("Segoe UI", 10))
    win = UCACreator()
    win.show()
    app.exec()


# ── Entry point ───────────────────────────────────────────────────────────────

def print_help():
    print("Usage:")
    print("  GUI mode  :  python3 uca-create-v3.py")
    print("  CLI mode  :  python3 uca-create-v3.py --cli [numbers | all]")
    print()
    print("Examples:")
    print("  python3 uca-create-v3.py --cli all")
    print("  python3 uca-create-v3.py --cli 1 3 9 12")
    print("  python3 uca-create-v3.py --cli          # interactive whiptail prompt")


if __name__ == "__main__":
    args = sys.argv[1:]

    if args and args[0] in ("-h", "--help"):
        print_help()
        sys.exit(0)

    if args and args[0] == "--cli":
        sys.exit(cli_main(args[1:]))

    # Default: GUI
    gui_main()