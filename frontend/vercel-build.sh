#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${API_BASE_URL:-}" ]]; then
  echo "API_BASE_URL is required. Set it in the Vercel project environment." >&2
  exit 1
fi

FLUTTER_VERSION="${FLUTTER_VERSION:-3.41.9}"
FLUTTER_ROOT="${HOME}/flutter-${FLUTTER_VERSION}"

if [[ ! -x "${FLUTTER_ROOT}/bin/flutter" ]]; then
  git clone \
    --depth 1 \
    --branch "${FLUTTER_VERSION}" \
    https://github.com/flutter/flutter.git \
    "${FLUTTER_ROOT}"
fi

export PATH="${FLUTTER_ROOT}/bin:${PATH}"
export PUB_CACHE="${HOME}/.pub-cache"

flutter config --enable-web --no-analytics
flutter pub get
flutter build web \
  --release \
  --dart-define="API_BASE_URL=${API_BASE_URL}"
