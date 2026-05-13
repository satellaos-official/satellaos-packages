#!/usr/bin/env python3
import subprocess
import os
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QPushButton, QMessageBox,
    QFrame
)
from PyQt6.QtGui import QPixmap, QFont, QColor
from PyQt6.QtCore import Qt, QThread, pyqtSignal


def get_gtk_colors() -> dict:
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk, Gdk

        ctx = Gtk.Window().get_style_context()

        def rgba_to_hex(rgba) -> str:
            r = int(rgba.red   * 255)
            g = int(rgba.green * 255)
            b = int(rgba.blue  * 255)
            return f"#{r:02x}{g:02x}{b:02x}"

        def mix(c1: str, c2: str, t: float) -> str:
            r1,g1,b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
            r2,g2,b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
            return "#{:02x}{:02x}{:02x}".format(
                int(r1*(1-t)+r2*t),
                int(g1*(1-t)+g2*t),
                int(b1*(1-t)+b2*t),
            )

        def lighten(c: str, amount: float) -> str:
            return mix(c, "#ffffff", amount)

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
            "ACCENT":       sel,
            "ACCENT_LIGHT": lighten(sel, 0.25),
            "TEXT_PRIMARY": fg,
            "TEXT_MUTED":   mix(fg, base, 0.45),
            "BORDER":       mix(base, fg, 0.12),
        }

    except Exception as e:
        print(f"[GTK renk okuma başarısız, fallback kullanılıyor]: {e}")
        return {
            "BG_DARK":      "#1e1e1e",
            "BG_PANEL":     "#252525",
            "BG_CARD":      "#2b2b2b",
            "ACCENT":       "#4a90d9",
            "ACCENT_LIGHT": "#74b3f5",
            "TEXT_PRIMARY": "#eeeeee",
            "TEXT_MUTED":   "#888888",
            "BORDER":       "#3a3a3a",
        }


class IconLoader(QThread):
    finished = pyqtSignal(list, str)

    def __init__(self, color, tmp_dir):
        super().__init__()
        self.color = color
        self.tmp_dir = tmp_dir

    def run(self):
        base_url = (
            "https://cdn.jsdelivr.net/gh/PapirusDevelopmentTeam/"
            "papirus-icon-theme@master/Papirus/48x48/places"
        )
        files = [
            f"folder-{self.color}.svg",
            f"user-{self.color}-home.svg",
            f"folder-{self.color}-download.svg",
        ]
        pixmaps = []
        for name in files:
            svg_path = os.path.join(self.tmp_dir, name)
            png_path = svg_path.replace(".svg", ".png")
            try:
                if not os.path.exists(svg_path):
                    subprocess.run(
                        ["curl", "-sL", f"{base_url}/{name}", "-o", svg_path],
                        check=True
                    )
                if not os.path.exists(png_path):
                    subprocess.run(
                        ["rsvg-convert", "-w", "128", "-h", "128", svg_path, "-o", png_path],
                        check=True
                    )
                px = QPixmap(png_path).scaled(
                    120, 120,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                pixmaps.append(px)
            except Exception:
                pixmaps.append(None)
        self.finished.emit(pixmaps, self.color)


class PapirusGUI(QMainWindow):

    COLORS = [
        "adwaita", "blue", "breeze", "carmine", "darkcyan", "green",
        "indigo", "nordic", "palebrown", "pink", "teal", "white",
        "yellow", "black", "bluegrey", "brown", "cyan", "deeporange",
        "grey", "magenta", "orange", "paleorange", "red", "violet", "yaru",
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Papirus Color Manager")
        self.setMinimumSize(850, 600)
        self.resize(850, 600)

        self.tmp_dir = "/tmp/papirus_gui"
        os.makedirs(self.tmp_dir, exist_ok=True)

        self._loader: IconLoader | None = None
        self._current_color: str | None = None

        colors = get_gtk_colors()
        self.BG_DARK      = colors["BG_DARK"]
        self.BG_PANEL     = colors["BG_PANEL"]
        self.BG_CARD      = colors["BG_CARD"]
        self.ACCENT       = colors["ACCENT"]
        self.ACCENT_LIGHT = colors["ACCENT_LIGHT"]
        self.TEXT_PRIMARY = colors["TEXT_PRIMARY"]
        self.TEXT_MUTED   = colors["TEXT_MUTED"]
        self.BORDER       = colors["BORDER"]

        self._apply_global_style()
        self._build_ui()

    def _apply_global_style(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget#central {{
                background-color: {self.BG_DARK};
            }}

            QFrame#left_panel {{
                background-color: {self.BG_PANEL};
                border: 1px solid {self.BORDER};
                border-radius: 8px;
            }}

            QListWidget {{
                background-color: {self.BG_CARD};
                color: {self.TEXT_PRIMARY};
                border: none;
                border-radius: 6px;
                font-size: 13px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 6px 12px;
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {self.ACCENT};
                color: {self.TEXT_PRIMARY};
            }}
            QListWidget::item:hover:!selected {{
                background-color: {self.BORDER};
            }}

            QPushButton#apply_btn {{
                background-color: {self.ACCENT};
                color: {self.TEXT_PRIMARY};
                border: none;
                border-radius: 6px;
                padding: 12px 30px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton#apply_btn:hover {{
                background-color: {self.ACCENT_LIGHT};
            }}
            QPushButton#apply_btn:pressed {{
                background-color: {self.ACCENT};
            }}

            QLabel {{
                color: {self.TEXT_PRIMARY};
                background: transparent;
            }}
        """)

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(15, 15, 15, 15)
        root_layout.setSpacing(15)

        left_frame = QFrame()
        left_frame.setObjectName("left_panel")
        left_frame.setFixedWidth(240)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(10, 15, 10, 10)
        left_layout.setSpacing(6)

        lbl_library = QLabel("LIBRARY")
        lbl_library.setStyleSheet(
            f"color: {self.ACCENT_LIGHT}; font-size: 10px; font-weight: bold; letter-spacing: 1px;"
        )
        left_layout.addWidget(lbl_library)

        self.listbox = QListWidget()
        for color in self.COLORS:
            item = QListWidgetItem(f"  {color}")
            self.listbox.addItem(item)
        self.listbox.currentRowChanged.connect(self._on_select)
        left_layout.addWidget(self.listbox)

        root_layout.addWidget(left_frame)

        right_widget = QWidget()
        right_widget.setObjectName("right_panel")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 20, 0, 0)
        right_layout.setSpacing(0)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        lbl_title = QLabel("Icon Preview")
        lbl_title.setStyleSheet(
            f"color: {self.ACCENT_LIGHT}; font-size: 18px; font-weight: bold;"
        )
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        right_layout.addWidget(lbl_title)
        right_layout.addSpacing(40)

        icon_row = QWidget()
        icon_row_layout = QHBoxLayout(icon_row)
        icon_row_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_row_layout.setSpacing(30)

        self.icon_labels: list[QLabel] = []
        for _ in range(3):
            lbl = QLabel()
            lbl.setFixedSize(120, 120)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("background: transparent;")
            self.icon_labels.append(lbl)
            icon_row_layout.addWidget(lbl)

        right_layout.addWidget(icon_row)
        right_layout.addSpacing(20)

        self.status_label = QLabel("Select a color to preview")
        self.status_label.setStyleSheet(
            f"color: {self.TEXT_MUTED}; font-size: 13px; font-style: italic;"
        )
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        right_layout.addWidget(self.status_label)

        right_layout.addStretch()

        self.apply_btn = QPushButton("APPLY TO SYSTEM")
        self.apply_btn.setObjectName("apply_btn")
        self.apply_btn.setFixedHeight(46)
        self.apply_btn.clicked.connect(self._apply_color)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        btn_row.addWidget(self.apply_btn)
        right_layout.addLayout(btn_row)
        right_layout.addSpacing(30)

        root_layout.addWidget(right_widget, stretch=1)

    def _on_select(self, row: int):
        if row < 0:
            return
        color = self.COLORS[row]
        self._current_color = color
        self.status_label.setText(f"Preparing {color}…")
        self.status_label.setStyleSheet(
            f"color: {self.TEXT_MUTED}; font-size: 13px; font-style: italic;"
        )
        for lbl in self.icon_labels:
            lbl.clear()
            lbl.setText("")

        if self._loader and self._loader.isRunning():
            self._loader.finished.disconnect()
            self._loader.quit()

        self._loader = IconLoader(color, self.tmp_dir)
        self._loader.finished.connect(self._on_icons_loaded)
        self._loader.start()

    def _on_icons_loaded(self, pixmaps: list, color: str):
        if color != self._current_color:
            return
        for i, px in enumerate(pixmaps):
            if px and not px.isNull():
                self.icon_labels[i].setPixmap(px)
                self.icon_labels[i].setText("")
            else:
                self.icon_labels[i].clear()
                self.icon_labels[i].setText("N/A")
                self.icon_labels[i].setStyleSheet(
                    f"color: {self.ACCENT_LIGHT}; font-size: 12px;"
                )
        self.status_label.setText(f"Selected: {color.upper()}")
        self.status_label.setStyleSheet(
            f"color: {self.TEXT_PRIMARY}; font-size: 14px; font-weight: bold;"
        )

    def _apply_color(self):
        if not self._current_color:
            return
        color = self._current_color
        cmd = (
            f"pkexec sh -c 'wget -qO- https://git.io/papirus-folders-install | sh "
            f"&& papirus-folders -C {color} --theme Papirus "
            f"&& gtk-update-icon-cache -f /usr/share/icons/*'"
        )
        self.status_label.setText("Updating system, please authenticate…")
        QApplication.processEvents()
        try:
            subprocess.run(cmd, shell=True, check=True)
            QMessageBox.information(
                self,
                "Success",
                f"{color.capitalize()} applied successfully!\nPlease relog to see all changes.",
            )
        except subprocess.CalledProcessError:
            QMessageBox.critical(
                self,
                "Auth Error",
                "Action cancelled or permission denied.",
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = PapirusGUI()
    window.show()
    sys.exit(app.exec())