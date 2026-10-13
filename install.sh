#!/usr/bin/env bash
# Instala o Xadrez Wallpaper só para o seu usuário, sem sudo.
# (No Ubuntu, prefira o .deb da página de Releases.)
set -euo pipefail

ORIGEM="$(cd "$(dirname "$0")" && pwd)"
DESTINO="$HOME/.local/share/xadrez-wallpaper"
BIN="$HOME/.local/bin/xadrez-wallpaper"
APP_ID=io.github.xadrez_wallpaper

# 1. Dependências do sistema
faltando=()
checar() { python3 -c "$1" 2>/dev/null || faltando+=("$2"); }
command -v python3 >/dev/null || { echo "Instale o Python 3 primeiro."; exit 1; }
checar "import gi" python3-gi
checar "import PIL" python3-pil
checar "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk" gir1.2-gtk-4.0
checar "import gi; gi.require_version('Adw', '1'); from gi.repository import Adw; assert Adw.MINOR_VERSION >= 4" gir1.2-adw-1
checar "import gi; gi.require_version('GdkPixbuf', '2.0'); from gi.repository import GdkPixbuf; assert any(f.get_name() == 'svg' for f in GdkPixbuf.Pixbuf.get_formats())" librsvg2-common
if [ ${#faltando[@]} -gt 0 ]; then
    echo "Faltam pacotes do sistema. No Ubuntu/Debian, rode:"
    echo
    echo "    sudo apt install ${faltando[*]}"
    echo
    echo "(libadwaita 1.4+ exige Ubuntu 24.04 ou mais novo.)"
    exit 1
fi

# 2. Código
rm -rf "$DESTINO"
mkdir -p "$DESTINO"
cp -r "$ORIGEM/xadrez_wallpaper" "$DESTINO/"
find "$DESTINO" -name __pycache__ -prune -exec rm -rf {} +

mkdir -p "$(dirname "$BIN")"
cat > "$BIN" <<SH
#!/bin/sh
export PYTHONPATH="$DESTINO\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m xadrez_wallpaper "\$@"
SH
chmod +x "$BIN"

# 3. Atalho, ícone e serviço
mkdir -p "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/scalable/apps" "$HOME/.config/systemd/user"
rm -f "$HOME/.local/share/applications/xadrez-wallpaper.desktop"  # nome antigo
sed "s|@BIN@|$BIN|" "$ORIGEM/data/xadrez-wallpaper.desktop.in" > "$HOME/.local/share/applications/$APP_ID.desktop"
cp "$ORIGEM/data/xadrez-wallpaper.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/"
sed "s|@BIN@|$BIN|" "$ORIGEM/data/xadrez-wallpaper.service.in" > "$HOME/.config/systemd/user/xadrez-wallpaper.service"

systemctl --user daemon-reload
systemctl --user enable xadrez-wallpaper.service
systemctl --user restart xadrez-wallpaper.service

echo "Pronto! Abra \"Xadrez Wallpaper\" no menu de aplicativos."
echo "Pode apagar esta pasta: tudo foi copiado para $DESTINO"
