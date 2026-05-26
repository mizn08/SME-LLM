#!/usr/bin/env bash
# Build Flutter web on Render (Static Site). Matches .github/workflows/deploy-web.yml
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_BASE="${API_BASE:-https://sme-advisor-api.onrender.com}"

export FLUTTER_VERSION="${FLUTTER_VERSION:-3.24.5}"
FLUTTER_DIR="${FLUTTER_DIR:-$HOME/flutter}"

if ! command -v flutter >/dev/null 2>&1; then
  echo "Installing Flutter ${FLUTTER_VERSION}..."
  git clone https://github.com/flutter/flutter.git -b stable --depth 1 "$FLUTTER_DIR"
  export PATH="$FLUTTER_DIR/bin:$PATH"
  cd "$FLUTTER_DIR"
  git fetch --depth 1 origin "refs/tags/${FLUTTER_VERSION}" 2>/dev/null || true
  git checkout "${FLUTTER_VERSION}" 2>/dev/null || git checkout "refs/tags/${FLUTTER_VERSION}" 2>/dev/null || true
  cd "$ROOT"
  flutter precache --web
fi

export PATH="${FLUTTER_DIR}/bin:${PATH}"
flutter --version
echo "Git commit: $(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"

cd "$ROOT/mobile_app"
flutter pub get

echo "Building web with API_BASE=${API_BASE}"
LOG="/tmp/flutter_web_build.log"
if ! flutter build web --release --dart-define="API_BASE=${API_BASE}" 2>&1 | tee "$LOG"; then
  echo "=== flutter build web FAILED — last 100 lines ==="
  tail -n 100 "$LOG" || true
  exit 1
fi

INDEX_HTML="$ROOT/mobile_app/build/web/index.html"
if [[ -f "$INDEX_HTML" ]] && grep -q 'name="api-base"' "$INDEX_HTML"; then
  sed -i.bak "s|<meta name=\"api-base\" content=\"[^\"]*\">|<meta name=\"api-base\" content=\"${API_BASE}\">|" "$INDEX_HTML"
  rm -f "${INDEX_HTML}.bak"
fi

echo "Output: $ROOT/mobile_app/build/web"
ls -la "$ROOT/mobile_app/build/web" | head -20
