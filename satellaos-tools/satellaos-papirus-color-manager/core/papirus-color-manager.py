#!/usr/bin/env python3
"""
Papirus Color Manager
─────────────────────
GUI + CLI aracı: Papirus ikon temasının klasör renklerini yönetir.

Kullanım:
  python3 papirus-color-manager.py              → Grafik arayüzü açar
  python3 papirus-color-manager.py --gui         → Grafik arayüzü açar
  python3 papirus-color-manager.py --cli         → Etkileşimli terminal arayüzü
  python3 papirus-color-manager.py --color <ad>  → Doğrudan renk uygular
  python3 papirus-color-manager.py --list        → Mevcut renkleri listeler
  python3 papirus-color-manager.py --help        → Bu yardım mesajını gösterir
"""

import subprocess
import os
import sys


# ─── Sabitler ────────────────────────────────────────────────────────────────

COLORS = [
    "adwaita", "blue", "breeze", "carmine", "darkcyan", "green",
    "indigo", "nordic", "palebrown", "pink", "teal", "white",
    "yellow", "black", "bluegrey", "brown", "cyan", "deeporange",
    "grey", "magenta", "orange", "paleorange", "red", "violet", "yaru",
]

BANNER = r"""
  ____            _                  ____      _            
 |  _ \ __ _ _ __(_)_ __ _   _ ___ / ___|___ | | ___  _ __ 
 | |_) / _` | '_ \ | '__| | | / __| |   / _ \| |/ _ \| '__|
 |  __/ (_| | |_) | | |  | |_| \__ \ |__| (_) | | (_) | |  
 |_|   \__,_| .__/|_|_|   \__,_|___/\____\___/|_|\___/|_|  
            |_|          M a n a g e r                       
"""

# ─── Renk Uygulama (ortak) ───────────────────────────────────────────────────

def apply_color(color: str, verbose: bool = True) -> bool:
    """Rengi sisteme uygular; başarılıysa True döner."""
    if color not in COLORS:
        print(f"[HATA] '{color}' geçerli bir renk değil. --list ile renkleri görebilirsiniz.")
        return False

    if verbose:
        print(f"[→] '{color}' uygulanıyor...")

    cmd = (
        f"pkexec sh -c '"
        f"papirus-folders -C {color} --theme Papirus && "
        f"gtk-update-icon-cache -f /usr/share/icons/Papirus'"
    )
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError:
        print("[HATA] Renk uygulanamadı. pkexec / papirus-folders kurulu mu?")
        return False

    if verbose:
        print("[→] Thunar kapatılıyor...")
    subprocess.run(["thunar", "-q"], stderr=subprocess.DEVNULL)

    if verbose:
        print("[→] XFCE panel yenileniyor...")
    subprocess.run(["xfce4-panel", "-r"], stderr=subprocess.DEVNULL)

    if verbose:
        print("[→] Masaüstü yenileniyor...")
    subprocess.run(["xfdesktop", "--reload"], stderr=subprocess.DEVNULL)

    subprocess.Popen(
        ["thunar", "--daemon"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    if verbose:
        print(f"[✓] '{color}' başarıyla uygulandı!")
    return True

# ─── CLI Modu ────────────────────────────────────────────────────────────────

def install_papirus_folders():
    print("[→] papirus-folders kuruluyor/güncelleniyor...")
    try:
        subprocess.run(
            "wget -qO- https://git.io/papirus-folders-install | sh",
            shell=True, check=True
        )
        print("[✓] papirus-folders hazır.")
    except subprocess.CalledProcessError:
        print("[UYARI] papirus-folders kurulumu başarısız olabilir, devam ediliyor...")


def cli_mode():
    print(BANNER)
    print("=" * 60)
    print("  Etkileşimli Terminal Modu")
    print("=" * 60)

    # Kurulum
    install_choice = input("\npapirus-folders kurulsun/güncellensin mi? [e/H]: ").strip().lower()
    if install_choice in ("e", "evet", "y", "yes"):
        install_papirus_folders()

    # Renk listesi
    print("\nMevcut renkler:\n")
    cols = 5
    for i, color in enumerate(COLORS, start=1):
        print(f"  {i:>2}) {color:<14}", end="" if i % cols else "\n")
    if len(COLORS) % cols:
        print()

    # Seçim
    print()
    try:
        raw = input("Renk numarasını girin: ").strip()
        choice_num = int(raw)
    except (ValueError, EOFError):
        print("[HATA] Geçersiz giriş.")
        sys.exit(1)

    if not (1 <= choice_num <= len(COLORS)):
        print(f"[HATA] 1 ile {len(COLORS)} arasında bir sayı girin.")
        sys.exit(1)

    chosen = COLORS[choice_num - 1]
    print(f"\nSeçilen renk: {chosen}")

    success = apply_color(chosen)
    if success:
        print("\nDeğişiklikler oturum kapatmadan da görünür olmalı.")
        print("Görünmüyorsa oturumu kapatıp açmayı deneyin.")
    sys.exit(0 if success else 1)


def list_mode():
    print("Mevcut Papirus renkleri:\n")
    for i, color in enumerate(COLORS, start=1):
        print(f"  {i:>2}. {color}")
    print(f"\nToplam: {len(COLORS)} renk")


# ─── GTK Renk Okuma (GUI için) ───────────────────────────────────────────────

def get_gtk_colors() -> dict:
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk
        ctx = Gtk.Window().get_style_context()

        def rgba_to_hex(rgba) -> str:
            r, g, b = int(rgba.red * 255), int(rgba.green * 255), int(rgba.blue * 255)
            return f"#{r:02x}{g:02x}{b:02x}"

        def mix(c1: str, c2: str, t: float) -> str:
            r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
            r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
            return "#{:02x}{:02x}{:02x}".format(
                int(r1 * (1 - t) + r2 * t),
                int(g1 * (1 - t) + g2 * t),
                int(b1 * (1 - t) + b2 * t),
            )

        def lighten(c: str, amount: float) -> str:
            return mix(c, "#ffffff", amount)

        bg_raw  = ctx.lookup_color("theme_bg_color")
        fg_raw  = ctx.lookup_color("theme_fg_color")
        sel_raw = ctx.lookup_color("theme_selected_bg_color")
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
    except Exception:
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

# ─── GUI – İkon Yükleyici Thread ─────────────────────────────────────────────

def _gui_imports():
    """GUI bağımlılıklarını yalnızca gerektiğinde import eder."""
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
        QLabel, QListWidget, QListWidgetItem, QPushButton, QMessageBox,
        QFrame,
    )
    from PyQt6.QtGui import QPixmap
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    return locals()


def gui_mode():
    try:
        from PyQt6.QtWidgets import (
            QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
            QLabel, QListWidget, QListWidgetItem, QPushButton, QMessageBox,
            QFrame,
        )
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt, QThread, pyqtSignal
    except ImportError:
        print("[HATA] PyQt6 bulunamadı. Kurmak için: pip install PyQt6")
        sys.exit(1)

    # ── İkon Yükleyici ───────────────────────────────────────────────────────
    class IconLoader(QThread):
        finished = pyqtSignal(list, str)

        def __init__(self, color, tmp_dir):
            super().__init__()
            self.color = color
            self.tmp_dir = tmp_dir

        def run(self):
            base_raw_url = (
                "https://raw.githubusercontent.com/satellaos-official/"
                "satellaos-packages/main/satellaos-tools/satellaos-papirus-color-manager/icons/"
            )
            files = [
                f"folder-{self.color}.svg",
                f"user-{self.color}-home.svg",
                f"folder-{self.color}-download.svg",
            ]
            pixmaps = []
            color_tmp_path = os.path.join(self.tmp_dir, self.color)
            os.makedirs(color_tmp_path, exist_ok=True)

            for name in files:
                svg_path = os.path.join(color_tmp_path, name)
                png_path = svg_path.replace(".svg", ".png")
                download_url = f"{base_raw_url}/{self.color}/{name}"
                try:
                    if not os.path.exists(svg_path):
                        subprocess.run(
                            ["curl", "-sL", download_url, "-o", svg_path], check=True
                        )
                    if not os.path.exists(png_path):
                        subprocess.run(
                            ["rsvg-convert", "-w", "128", "-h", "128", svg_path, "-o", png_path],
                            check=True,
                        )
                    px = QPixmap(png_path).scaled(
                        120, 120,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    pixmaps.append(px)
                except Exception:
                    pixmaps.append(None)

            self.finished.emit(pixmaps, self.color)

    # ── Ana Pencere ──────────────────────────────────────────────────────────
    class PapirusGUI(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Papirus Color Manager")
            self.setMinimumSize(850, 600)
            self.tmp_dir = "/tmp/papirus_gui"
            os.makedirs(self.tmp_dir, exist_ok=True)
            self._loader = None
            self._current_color = None

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
                QMainWindow, QWidget#central {{ background-color: {self.BG_DARK}; }}
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
                    outline: none;
                }}
                QListWidget::item {{ padding: 6px 12px; border-radius: 4px; }}
                QListWidget::item:selected {{
                    background-color: {self.ACCENT};
                    color: {self.TEXT_PRIMARY};
                }}
                QPushButton#apply_btn {{
                    background-color: {self.ACCENT};
                    color: {self.TEXT_PRIMARY};
                    border: none;
                    border-radius: 6px;
                    font-weight: bold;
                }}
                QPushButton#apply_btn:hover {{ background-color: {self.ACCENT_LIGHT}; }}
                QLabel {{ color: {self.TEXT_PRIMARY}; }}
            """)

        def _build_ui(self):
            central = QWidget(objectName="central")
            self.setCentralWidget(central)
            root_layout = QHBoxLayout(central)
            root_layout.setContentsMargins(15, 15, 15, 15)
            root_layout.setSpacing(15)

            # Sol panel
            left_frame = QFrame(objectName="left_panel")
            left_frame.setFixedWidth(240)
            left_layout = QVBoxLayout(left_frame)
            lbl_library = QLabel("LIBRARY")
            lbl_library.setStyleSheet(
                f"color: {self.ACCENT_LIGHT}; font-size: 10px; font-weight: bold;"
            )
            left_layout.addWidget(lbl_library)
            self.listbox = QListWidget()
            for color in COLORS:
                self.listbox.addItem(QListWidgetItem(f"  {color}"))
            self.listbox.currentRowChanged.connect(self._on_select)
            left_layout.addWidget(self.listbox)
            root_layout.addWidget(left_frame)

            # Sağ panel
            right_widget = QWidget()
            right_layout = QVBoxLayout(right_widget)
            lbl_title = QLabel("Icon Preview")
            lbl_title.setStyleSheet(
                f"color: {self.ACCENT_LIGHT}; font-size: 18px; font-weight: bold;"
            )
            lbl_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            right_layout.addWidget(lbl_title)

            self.icon_labels = []
            icon_row = QWidget()
            icon_row_layout = QHBoxLayout(icon_row)
            for _ in range(3):
                lbl = QLabel()
                lbl.setFixedSize(120, 120)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.icon_labels.append(lbl)
                icon_row_layout.addWidget(lbl)
            right_layout.addWidget(icon_row)

            self.status_label = QLabel("Select a color to preview")
            self.status_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.status_label.setStyleSheet(
                f"color: {self.TEXT_MUTED}; font-size: 13px; font-style: italic;"
            )
            right_layout.addWidget(self.status_label)
            right_layout.addStretch()

            self.apply_btn = QPushButton("APPLY TO SYSTEM")
            self.apply_btn.setObjectName("apply_btn")
            self.apply_btn.setFixedHeight(46)
            self.apply_btn.clicked.connect(self._apply_color)
            right_layout.addWidget(self.apply_btn)
            root_layout.addWidget(right_widget, stretch=1)

        def _on_select(self, row):
            if row < 0:
                return
            color = COLORS[row]
            self._current_color = color
            self.status_label.setText(f"Preparing {color}...")
            for lbl in self.icon_labels:
                lbl.clear()
            if self._loader and self._loader.isRunning():
                self._loader.terminate()
            self._loader = IconLoader(color, self.tmp_dir)
            self._loader.finished.connect(self._on_icons_loaded)
            self._loader.start()

        def _on_icons_loaded(self, pixmaps, color):
            if color != self._current_color:
                return
            for i, px in enumerate(pixmaps):
                if px:
                    self.icon_labels[i].setPixmap(px)
                else:
                    self.icon_labels[i].setText("N/A")
            self.status_label.setText(f"Selected: {color.upper()}")

        def _apply_color(self):
            if not self._current_color:
                return
            color = self._current_color
            self.status_label.setText("Refreshing system cache & UI...")
            QApplication.processEvents()
            success = apply_color(color, verbose=False)
            if success:
                QMessageBox.information(
                    self, "Başarılı",
                    f"{color.capitalize()} uygulandı!\nThunar ve XFCE arayüzü yenilendi.",
                )
                self.status_label.setText(f"✓ {color.upper()} uygulandı")
            else:
                QMessageBox.critical(self, "Hata", "Renk uygulanamadı veya arayüz yenilenemedi.")

    app = QApplication(sys.argv)
    window = PapirusGUI()
    window.show()
    sys.exit(app.exec())


# ─── ANSI Renk Kodları ───────────────────────────────────────────────────────

GREEN  = "\033[32m"          # green – parametreler & komutlar
DIM    = "\033[2m"           # soluk       – ikincil bilgi
BOLD   = "\033[1m"           # kalın
RESET  = "\033[0m"           # sıfırla


# ─── Özel Yardım Ekranı ──────────────────────────────────────────────────────

def print_help():
    G, D, B, R = GREEN, DIM, BOLD, RESET

    print(f"""
{B}Papirus Color Manager{R}
Manage folder colors for the Papirus icon theme.

{B}USAGE{R}
  {G}python3 papirus-color-manager.py{R} {D}[OPTION]{R}

{B}OPTIONS{R}
  {G}--gui{R}              Launch the graphical interface {D}(default when no option is given){R}
  {G}--cli{R}              Launch the interactive terminal interface
  {G}--color {R}{G}<name>{R}     Apply a color directly without opening any interface
  {G}--list{R}             Print all available color names and exit
  {G}--help{R}             Show this help message and exit

{B}EXAMPLES{R}
  {G}python3 papirus-color-manager.py{R}
    {D}# Opens the GUI (default){R}

  {G}python3 papirus-color-manager.py --gui{R}
    {D}# Opens the GUI explicitly{R}

  {G}python3 papirus-color-manager.py --cli{R}
    {D}# Interactive terminal mode — pick a color by number{R}

  {G}python3 papirus-color-manager.py --list{R}
    {D}# Print all 25 available colors{R}

  {G}python3 papirus-color-manager.py --color violet{R}
    {D}# Apply 'violet' immediately, no interface{R}

  {G}python3 papirus-color-manager.py --color teal{R}
    {D}# Apply 'teal' immediately, no interface{R}

{B}NOTES{R}
  {D}--gui, --cli, --color, and --list are mutually exclusive.
  Applying a color requires pkexec and papirus-folders to be installed.
  Use --list to see all valid color names before using --color.{R}
""")


# ─── Giriş Noktası ───────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    # Argümansız → GUI
    if not args:
        gui_mode()
        return

    flag = args[0].lower()

    if flag in ("-h", "--help"):
        print_help()

    elif flag == "--list":
        list_mode()

    elif flag == "--color":
        if len(args) < 2:
            print(f"[ERROR] --color requires a color name. Use --list to see options.")
            sys.exit(1)
        success = apply_color(args[1])
        sys.exit(0 if success else 1)

    elif flag == "--cli":
        cli_mode()

    elif flag == "--gui":
        gui_mode()

    else:
        print(f"[ERROR] Unknown option: '{args[0]}'. Use --help for usage.")
        sys.exit(1)


if __name__ == "__main__":
    main()
