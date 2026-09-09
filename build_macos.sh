#!/bin/zsh
set -euo pipefail

PROJECT_DIR="${0:A:h}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$PROJECT_DIR"
export PYINSTALLER_CONFIG_DIR="$PROJECT_DIR/.pyinstaller-cache"
mkdir -p "$PYINSTALLER_CONFIG_DIR"
"$PYTHON_BIN" scripts/build_icns.py assets/app_icon.iconset assets/app_icon.icns
"$PYTHON_BIN" -m PyInstaller --noconfirm --clean UrlHeat.spec

APP_PATH="$PROJECT_DIR/dist/链接热度抓取.app"
ZIP_PATH="$PROJECT_DIR/dist/URLHeat-0.6.7-macOS-arm64.zip"

if [[ ! -d "$APP_PATH" ]]; then
  print -u2 "未找到构建结果：$APP_PATH"
  exit 1
fi

rm -f "$ZIP_PATH"
/usr/bin/ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"
(
  cd "$PROJECT_DIR/dist"
  shasum -a 256 "${ZIP_PATH:t}" > "${ZIP_PATH:t}.sha256"
)
print "已生成：$APP_PATH"
print "已生成：$ZIP_PATH"
