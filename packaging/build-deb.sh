#!/usr/bin/env bash
# Gera dist/xadrez-wallpaper_<versão>_all.deb
# Uso: packaging/build-deb.sh [versão]   (padrão: a versão em xadrez_wallpaper/__init__.py)
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
VERSAO="${1:-$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$RAIZ/xadrez_wallpaper/__init__.py")}"
VERSAO="${VERSAO#v}"
MANTENEDOR="${MANTENEDOR:-Xadrez Wallpaper <xadrez-wallpaper@users.noreply.github.com>}"
HOMEPAGE="${HOMEPAGE:-}"

PKG="$(mktemp -d)"
trap 'rm -rf "$PKG"' EXIT
BIN=/usr/bin/xadrez-wallpaper
APP_ID=io.github.xadrez_wallpaper

# Código (python-chess embutido junto)
install -d "$PKG/usr/share/xadrez-wallpaper"
cp -r "$RAIZ/xadrez_wallpaper" "$PKG/usr/share/xadrez-wallpaper/"
find "$PKG" -name __pycache__ -prune -exec rm -rf {} +
sed -i "s/^__version__ = .*/__version__ = \"$VERSAO\"/" "$PKG/usr/share/xadrez-wallpaper/xadrez_wallpaper/__init__.py"

# Executável
install -d "$PKG/usr/bin"
cat > "$PKG$BIN" <<SH
#!/bin/sh
export PYTHONPATH=/usr/share/xadrez-wallpaper\${PYTHONPATH:+:\$PYTHONPATH}
exec /usr/bin/python3 -m xadrez_wallpaper "\$@"
SH

# Atalho, ícone e serviço (o serviço vem desligado; cada usuário liga pelo app)
install -d "$PKG/usr/share/applications" "$PKG/usr/share/icons/hicolor/scalable/apps" \
           "$PKG/usr/lib/systemd/user" "$PKG/usr/share/doc/xadrez-wallpaper"
sed "s|@BIN@|$BIN|" "$RAIZ/data/xadrez-wallpaper.desktop.in" > "$PKG/usr/share/applications/$APP_ID.desktop"
cp "$RAIZ/data/xadrez-wallpaper.svg" "$PKG/usr/share/icons/hicolor/scalable/apps/"
sed "s|@BIN@|$BIN|" "$RAIZ/data/xadrez-wallpaper.service.in" > "$PKG/usr/lib/systemd/user/xadrez-wallpaper.service"
cat > "$PKG/usr/share/doc/xadrez-wallpaper/copyright" <<TXT
Xadrez Wallpaper — GPL-3.0-or-later
Inclui python-chess (https://github.com/niklasf/python-chess), GPL-3.0-or-later.
Texto completo da licença: /usr/share/common-licenses/GPL-3
TXT

# Permissões padrão
find "$PKG" -type d -exec chmod 755 {} +
find "$PKG" -type f -exec chmod 644 {} +
chmod 755 "$PKG$BIN"

install -d "$PKG/DEBIAN"
cat > "$PKG/DEBIAN/control" <<CTRL
Package: xadrez-wallpaper
Version: $VERSAO
Section: games
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-gi, python3-pil, gir1.2-gtk-4.0 (>= 4.12), gir1.2-adw-1 (>= 1.4), gir1.2-gdkpixbuf-2.0, librsvg2-common, gsettings-desktop-schemas
Installed-Size: $(du -sk "$PKG/usr" | cut -f1)
Maintainer: $MANTENEDOR
${HOMEPAGE:+Homepage: $HOMEPAGE
}Description: Partidas lendárias de xadrez no seu papel de parede
 Transforma o wallpaper do GNOME num tabuleiro que reproduz partidas
 históricas lance a lance — A Imortal, a Partida do Século, a Ópera de
 Morphy e outras — com um app para escolher a fila, a velocidade e o visual.
CTRL

cat > "$PKG/DEBIAN/postinst" <<'POST'
#!/bin/sh
set -e
if [ "$1" = configure ]; then
    command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true
    command -v update-desktop-database >/dev/null && update-desktop-database -q /usr/share/applications || true
fi
POST
chmod 755 "$PKG/DEBIAN/postinst"

install -d "$RAIZ/dist"
SAIDA="$RAIZ/dist/xadrez-wallpaper_${VERSAO}_all.deb"
dpkg-deb --build --root-owner-group -Zxz "$PKG" "$SAIDA" >/dev/null
echo "$SAIDA"
