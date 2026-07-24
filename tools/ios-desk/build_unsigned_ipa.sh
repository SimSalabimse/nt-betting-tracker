#!/usr/bin/env bash
# Build unsigned NTDesk.ipa for sideloading (no code signing).
# Pattern matches Documents/GitHub/build_unsigned_ipa.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PROJECT="$ROOT/NTDesk/NTDesk.xcodeproj"
SCHEME="NTDesk"
BUILD_DIR="$ROOT/build_unsigned"
DERIVED_DATA="$BUILD_DIR/DerivedData"

if [[ ! -d "$PROJECT" ]]; then
  echo "Missing Xcode project: $PROJECT" >&2
  exit 1
fi

mkdir -p "$DERIVED_DATA"
echo "Building $SCHEME (Release, iphoneos, unsigned)…"

xcodebuild \
  -project "$PROJECT" \
  -scheme "$SCHEME" \
  -configuration Release \
  -sdk iphoneos \
  -derivedDataPath "$DERIVED_DATA" \
  clean build \
  CODE_SIGN_IDENTITY="" \
  CODE_SIGNING_REQUIRED=NO \
  CODE_SIGNING_ALLOWED=NO \
  PRODUCT_BUNDLE_IDENTIFIER="com.simsalabim.ntdesk"

APP="$(find "$DERIVED_DATA/Build/Products/Release-iphoneos" -name 'NTDesk.app' -type d | head -1)"
if [[ -z "$APP" ]]; then
  echo "Build failed: NTDesk.app not found" >&2
  exit 1
fi

PAYLOAD="$BUILD_DIR/Payload"
rm -rf "$PAYLOAD" "$BUILD_DIR/NTDesk.ipa"
mkdir -p "$PAYLOAD"
cp -R "$APP" "$PAYLOAD/"
(
  cd "$BUILD_DIR"
  zip -qr NTDesk.ipa Payload
)
echo "Wrote $BUILD_DIR/NTDesk.ipa"
echo "Sideload with your preferred tool (unsigned)."
