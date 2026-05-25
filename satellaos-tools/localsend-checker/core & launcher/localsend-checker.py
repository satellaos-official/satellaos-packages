#!/usr/bin/env python3
"""
localsend-launcher.py
Thunar custom action için LocalSend başlatıcı.
Kullanım: localsend-launcher.py %F
"""

import sys
import subprocess
import shutil

# Deb paketi /usr/bin/localsend_app olarak kurulur.
# Fallback olarak diğer olası binary adları da denenir.
LOCALSEND_CANDIDATES = [
    "localsend_app",
    "localsend",
]

INSTALL_CMD = r"""
#!/bin/bash
set -e
set -u

PKG_DIR=$(mktemp -d /tmp/localsend-install-XXXXXX)
trap 'rm -rf "$PKG_DIR"' EXIT

LOCALSEND_URL=$(curl -s https://api.github.com/repos/localsend/localsend/releases/latest \
    | grep "browser_download_url" | grep "linux-x86-64.deb" | cut -d '"' -f 4)

LOCALSEND_FILE=$(basename "$LOCALSEND_URL")

wget -O "$PKG_DIR/$LOCALSEND_FILE" "$LOCALSEND_URL"
sudo apt update
sudo apt install -y "$PKG_DIR/$LOCALSEND_FILE"
"""


def find_localsend_binary() -> str | None:
    """
    Bilinen binary adlarını sırayla arar, bulunanı döner.
    Bulunamazsa None döner.
    """
    for name in LOCALSEND_CANDIDATES:
        if shutil.which(name):
            return name
    return None


def is_localsend_installed() -> bool:
    """LocalSend'in kurulu olup olmadığını kontrol eder."""
    return find_localsend_binary() is not None


def launch_localsend(files: list[str]) -> None:
    """LocalSend'i verilen dosyalarla başlatır."""
    binary = find_localsend_binary()
    cmd = [binary] + files
    subprocess.Popen(cmd)


def show_not_installed_dialog() -> bool:
    """
    zenity ile kurulum öneri diyaloğu gösterir.
    Kullanıcı 'Kur' derse True, 'İptal' derse False döner.
    """
    result = subprocess.run(
        [
            "zenity",
            "--question",
            "--title=LocalSend Bulunamadı",
            "--text=LocalSend sisteminizde kurulu değil.\n\nKurmak ister misiniz?",
            "--ok-label=Kur",
            "--cancel-label=İptal",
            "--width=340",
        ],
        capture_output=True,
    )
    return result.returncode == 0


def run_install_in_terminal() -> None:
    """
    Kurulum scriptini bir terminal emülatöründe çalıştırır.
    xfce4-terminal, xterm, gnome-terminal sırasıyla denenir.
    """
    # Geçici script dosyası oluştur
    import tempfile, os, stat

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".sh",
        prefix="localsend-install-",
        delete=False,
    ) as f:
        f.write(INSTALL_CMD)
        script_path = f.name

    # Çalıştırma izni ver
    os.chmod(script_path, stat.S_IRWXU)

    terminals = [
        ["xfce4-terminal", "--hold", "-e", f"bash {script_path}"],
        ["xterm", "-hold", "-e", f"bash {script_path}"],
        ["gnome-terminal", "--wait", "--", "bash", "-c", f"bash {script_path}; read -p 'Çıkmak için Enter...'"],
    ]

    for term_cmd in terminals:
        if shutil.which(term_cmd[0]):
            subprocess.run(term_cmd)
            break
    else:
        # Hiç terminal bulunamazsa zenity ile hata göster
        subprocess.run([
            "zenity", "--error",
            "--title=Terminal Bulunamadı",
            "--text=Kurulum için uygun bir terminal emülatörü bulunamadı.\n\n"
                   "Lütfen aşağıdaki komutu elle çalıştırın:\n\n"
                   "xfce4-terminal veya xterm kurun.",
            "--width=400",
        ])


def show_install_success_dialog() -> None:
    subprocess.run([
        "zenity", "--info",
        "--title=Kurulum Tamamlandı",
        "--text=LocalSend başarıyla kuruldu!\n\nDosyalarınızı göndermek için lütfen tekrar deneyin.",
        "--width=340",
    ])


def main() -> None:
    files = sys.argv[1:]  # Thunar %F ile gelen dosya yolları

    if is_localsend_installed():
        launch_localsend(files)
        return

    # LocalSend kurulu değil → kullanıcıya sor
    if show_not_installed_dialog():
        run_install_in_terminal()

        # Kurulum sonrası tekrar kontrol
        if is_localsend_installed():
            show_install_success_dialog()
        # Kurulum tamamlansa da kullanıcı manuel tekrar denemeli;
        # otomatik başlatmıyoruz çünkü terminal --hold ile açık kalıyor olabilir.
    # İptal → sessizce çık


if __name__ == "__main__":
    main()
