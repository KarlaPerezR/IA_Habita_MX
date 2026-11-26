#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OTP_DIR="$ROOT_DIR/.runtime/otp"
JAVA_BIN=${JAVA_BIN:-/opt/homebrew/opt/openjdk/bin/java}
exec "$JAVA_BIN" -Xmx4G -jar "$OTP_DIR/otp-shaded-2.10.0.jar" --build --save "$OTP_DIR"
