#!/usr/bin/env bash
# Build Flutter web on Render (Static Site) or Linux CI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Default: paired API host when web is sme-advisor-web-XXXX.onrender.com
API_BASE="${API_BASE:-https://sme-advisor-api.onrender.com}"
# If Render assigned a suffix, set API_BASE in Static Site env to e.g. https://sme-advisor-api-38lz.onrender.com

export FLUTTER_VERSION="${FLUTTER_VERSION:-3.24.5}"
FLUTTER_DIR="${FLUTTER_DIR:-$HOME/flutter}"

if ! command -v flutter >/dev/null 2>&1; then
  echo "Installing Flutter ${FLUTTER_VERSION}..."
  git clone https://github.com/flutter/flutter.git -b stable --depth 1 "$FLUTTER_DIR"
  export PATH="$FLUTTER_DIR/bin:$PATH"
  flutter precache --web
fi

flutter --version
cd "$ROOT/mobile_app"
flutter pub get
echo "Building web with API_BASE=${API_BASE}"
flutter build web --release --dart-define="API_BASE=${API_BASE}"

# Ensure built index.html points at the API (runtime meta + cache-friendly)
INDEX_HTML="$ROOT/mobile_app/build/web/index.html"
if [[ -f "$INDEX_HTML" ]]; then
  sed -i.bak "s|<meta name=\"api-base\" content=\"[^\"]*\">|<meta name=\"api-base\" content=\"${API_BASE}\">|" "$INDEX_HTML"
  rm -f "${INDEX_HTML}.bak"
fi

echo "Output: $ROOT/mobile_app/build/web"
echo "API_BASE in build: ${API_BASE}"
