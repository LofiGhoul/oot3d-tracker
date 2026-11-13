#!/usr/bin/env bash
# Adds "OoT3D 100% Tracker" to your app launcher (per-user, no root needed).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
icons="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
mkdir -p "$apps" "$icons" "$HOME/.local/bin"

chmod +x "$here/oot3d_tracker.py"
ln -sf "$here/oot3d_tracker.py" "$HOME/.local/bin/oot3d-tracker"
cp "$here/io.github.oot3d_tracker.svg" "$icons/"

cat > "$apps/io.github.oot3d_tracker.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=OoT3D 100% Tracker
Comment=Track your Ocarina of Time 3D progress toward 100%: heart pieces, Gold Skulltulas, items and more
Exec=python3 "$here/oot3d_tracker.py" %f
Icon=io.github.oot3d_tracker
Terminal=false
Categories=Game;
Keywords=zelda;ocarina;oot3d;heart;skulltula;3ds;save;
StartupWMClass=io.github.oot3d_tracker
EOF

command -v update-desktop-database >/dev/null && update-desktop-database "$apps" || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q "${icons%/scalable/apps}" 2>/dev/null || true
echo "Installed. Launch 'OoT3D 100% Tracker' from your app launcher, or run: oot3d-tracker"
