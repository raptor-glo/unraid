#!/usr/bin/env bash
# Store an icon you downloaded (e.g. from Flaticon) as a folder icon.
#
#   scripts/add-icon.sh <file> <name> ["credit"]
#   scripts/add-icon.sh ~/inbox/rocket.gif gaming "Freepik, Flaticon"
#       -> icons/folders/gaming.gif, resized to 128 px, credited in icons/CREDITS.md
#
# Name icons after their folder (lower case, dashes), so replacing a folder's
# icon is just running this again with the same name. Animated GIFs keep every
# frame; PNG, WebP and SVG are stored as they are.
# Free Flaticon icons need a credit: give the author's name as the third argument.
set -euo pipefail
cd "$(dirname "$0")/.."

src="${1:?file to add}"
name="${2:?name, e.g. gaming}"
credit="${3:-}"
size="${ICON_SIZE:-128}"
[ -f "$src" ] || { echo "✗ No file at $src" >&2; exit 1; }
[[ $name =~ ^[a-z0-9-]+$ ]] || { echo "✗ Use lower case and dashes for the name, e.g. media-server" >&2; exit 1; }

ext="$(echo "${src##*.}" | tr 'A-Z' 'a-z')"
mkdir -p icons/folders
rm -f icons/folders/"$name".{gif,png,webp,svg}
out="icons/folders/$name.$ext"

case "$ext" in
  gif)
    command -v gifsicle >/dev/null || { echo "Needs gifsicle: sudo apt-get install gifsicle" >&2; exit 1; }
    gifsicle -O3 --resize-fit "${size}x${size}" "$src" -o "$out" ;;
  png|webp|svg)
    cp "$src" "$out" ;;
  *)
    echo "✗ Use a .gif, .png, .webp or .svg file" >&2; exit 1 ;;
esac
echo "✓ $out ($(du -h "$out" | cut -f1), from $(du -h "$src" | cut -f1))"

# One credit row per file, replaced when the icon is.
touch icons/CREDITS.md
grep -vF "| \`$name." icons/CREDITS.md > icons/CREDITS.md.tmp || true
mv icons/CREDITS.md.tmp icons/CREDITS.md
echo "| \`$name.$ext\` | ${credit:-Flaticon (add the author)} | $(date +%Y-%m-%d) |" >> icons/CREDITS.md

echo "Next: point the folder at \"folders/$name.$ext\" in docker-tab/layout.json if it isn't already, commit, push, apply."
