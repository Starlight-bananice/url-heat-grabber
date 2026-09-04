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
ZIP_PATH="$PROJECT_DIR/dist/链接热度抓取-macOS-arm64.zip"

if [[ ! -d "$APP_PATH" ]]; then
  print -u2 "未找到构建结果：$APP_PATH"
  exit 1
fi

rm -f "$ZIP_PATH"
(
  cd "$PROJECT_DIR/dist"
  zip -q -r -X "$ZIP_PATH" "链接热度抓取.app"
)
print "已生成：$APP_PATH"
print "已生成：$ZIP_PATH"
