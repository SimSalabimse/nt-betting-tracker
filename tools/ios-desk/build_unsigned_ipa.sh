#!/usr/bin/env bash
# Build unsigned NTDesk.ipa for sideloading (no code signing).
# Pattern matches Documents/GitHub/build_unsigned_ipa.sh
#
# Env overrides (defaults = current scaffold IPA):
#   SCHEME=NTDesk|NTDesk-Legacy
#   CONFIGURATION=Release|LegacyRelease|Debug|LegacyDebug
#
# Recovery (pre-HIG / Legacy UI):
#   SCHEME=NTDesk-Legacy CONFIGURATION=LegacyRelease ./tools/ios-desk/build_unsigned_ipa.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PROJECT="$ROOT/NTDesk/NTDesk.xcodeproj"
SCHEME="${SCHEME:-NTDesk}"
CONFIGURATION="${CONFIGURATION:-Release}"
BUILD_DIR="$ROOT/build_unsigned"
DERIVED_DATA="$BUILD_DIR/DerivedData"

if [[ ! -d "$PROJECT" ]]; then
  echo "Missing Xcode project: $PROJECT" >&2
  exit 1
fi

mkdir -p "$DERIVED_DATA"
echo "Building $SCHEME ($CONFIGURATION, iphoneos, unsigned)…"

xcodebuild \
  -project "$PROJECT" \
  -scheme "$SCHEME" \
  -configuration "$CONFIGURATION" \
  -sdk iphoneos \
  -derivedDataPath "$DERIVED_DATA" \
  clean build \
  CODE_SIGN_IDENTITY="" \
  CODE_SIGNING_REQUIRED=NO \
  CODE_SIGNING_ALLOWED=NO \
  PRODUCT_BUNDLE_IDENTIFIER="com.simsalabim.ntdesk"

# Products land under <Configuration>-iphoneos (e.g. Release-iphoneos, LegacyRelease-iphoneos).
APP="$(find "$DERIVED_DATA/Build/Products/${CONFIGURATION}-iphoneos" -name 'NTDesk.app' -type d 2>/dev/null | head -1)"
if [[ -z "$APP" ]]; then
  # Fallback: any NTDesk.app under Products (handles unexpected product dirs).
  APP="$(find "$DERIVED_DATA/Build/Products" -name 'NTDesk.app' -type d 2>/dev/null | head -1)"
fi
if [[ -z "$APP" ]]; then
  echo "Build failed: NTDesk.app not found under ${CONFIGURATION}-iphoneos" >&2
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
echo "Wrote $BUILD_DIR/NTDesk.ipa (scheme=$SCHEME configuration=$CONFIGURATION)"
echo "Sideload with your preferred tool (unsigned)."
