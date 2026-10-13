#!/usr/bin/env bash
# Desfaz o install.sh. O wallpaper original volta quando o serviço para.
systemctl --user disable --now xadrez-wallpaper.service 2>/dev/null || true
rm -rf "$HOME/.local/share/xadrez-wallpaper"
rm -f "$HOME/.config/systemd/user/xadrez-wallpaper.service" \
      "$HOME/.local/share/applications/io.github.xadrez_wallpaper.desktop" \
      "$HOME/.local/share/applications/xadrez-wallpaper.desktop" \
      "$HOME/.local/share/icons/hicolor/scalable/apps/xadrez-wallpaper.svg" \
      "$HOME/.local/bin/xadrez-wallpaper"
systemctl --user daemon-reload
echo "Desinstalado. Suas preferências ficam em ~/.config/xadrez-wallpaper (apague se quiser)."
