#!/bin/sh
# Build pixel-td_<version>_all.deb  (needs only dpkg-deb, gzip, python3).  Usage: ./packaging/debian/build-deb.sh
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$ROOT/src/pixel_td/__init__.py")
PKG=pixel-td
OUT="$ROOT/dist"
STAGE="$ROOT/build/deb/${PKG}_${VERSION}_all"
rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN" "$STAGE/usr/games" "$STAGE/usr/lib/python3/dist-packages" \
         "$STAGE/usr/share/applications" "$STAGE/usr/share/man/man6" "$STAGE/usr/share/doc/$PKG" "$OUT"

# python package (no caches)
cp -r "$ROOT/src/pixel_td" "$STAGE/usr/lib/python3/dist-packages/pixel_td"
find "$STAGE" -name '__pycache__' -type d -prune -exec rm -rf {} +

# launcher (Debian policy: games live in /usr/games)
cat > "$STAGE/usr/games/$PKG" <<'LAUNCH'
#!/usr/bin/python3
import sys
from pixel_td.__main__ import main
sys.exit(main())
LAUNCH
chmod 755 "$STAGE/usr/games/$PKG"

# desktop entry + icons + man page
install -m 644 "$HERE/pixel-td.desktop" "$STAGE/usr/share/applications/pixel-td.desktop"
for s in 48 128 256; do
  d="$STAGE/usr/share/icons/hicolor/${s}x${s}/apps"; mkdir -p "$d"
  install -m 644 "$ROOT/packaging/icons/pixel-td-$s.png" "$d/pixel-td.png"
done
gzip -9n -c "$HERE/pixel-td.6" > "$STAGE/usr/share/man/man6/pixel-td.6.gz"

# docs
install -m 644 "$ROOT/README.md" "$STAGE/usr/share/doc/$PKG/README.md"
DATE=$(date -R)
{ printf '%s (%s) unstable; urgency=low\n\n  * Release %s. See CHANGELOG.md upstream.\n\n -- Pixel TD Maintainers <pixel-td@example.invalid>  %s\n' "$PKG" "$VERSION" "$VERSION" "$DATE"; } \
  | gzip -9n > "$STAGE/usr/share/doc/$PKG/changelog.Debian.gz"
cat > "$STAGE/usr/share/doc/$PKG/copyright" <<COPY
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: pixel-td

Files: *
Copyright: 2026 Pixel TD contributors
License: Expat
 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:
 .
 The above copyright notice and this permission notice shall be included in
 all copies or substantial portions of the Software.
 .
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 SOFTWARE.
COPY

# control + maintainer scripts
SIZE=$(du -sk "$STAGE" | cut -f1)
cat > "$STAGE/DEBIAN/control" <<CTRL
Package: $PKG
Version: $VERSION
Section: games
Priority: optional
Architecture: all
Depends: python3 (>= 3.9), python3-pygame (>= 2.0), python3-numpy (>= 1.19)
Installed-Size: $SIZE
Maintainer: Pixel TD Maintainers <pixel-td@example.invalid>
Homepage: https://github.com/OWNER/pixel-td
Description: pixel-art tower defense with infinite waves and absurd numbers
 Build towers anywhere off the road and survive endless, exponentially
 growing waves (numbers reach millions, billions, trillions and beyond).
 Ten tower types, a dozen enemy types and bosses, free placement,
 Ascension (prestige) upgrades, autosave and a main menu.
CTRL
cat > "$STAGE/DEBIAN/postinst" <<'POST'
#!/bin/sh
set -e
if [ "$1" = configure ]; then
    python3 -m compileall -q -f /usr/lib/python3/dist-packages/pixel_td >/dev/null 2>&1 || true
    command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t /usr/share/icons/hicolor 2>/dev/null || true
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q 2>/dev/null || true
fi
exit 0
POST
cat > "$STAGE/DEBIAN/postrm" <<'POSTRM'
#!/bin/sh
set -e
case "$1" in
    remove|purge) rm -rf /usr/lib/python3/dist-packages/pixel_td ;;
esac
exit 0
POSTRM
chmod 755 "$STAGE/DEBIAN/postinst" "$STAGE/DEBIAN/postrm"
find "$STAGE" -type d -exec chmod 755 {} +

dpkg-deb --build --root-owner-group "$STAGE" "$OUT/${PKG}_${VERSION}_all.deb" >/dev/null
echo "Built $OUT/${PKG}_${VERSION}_all.deb"
