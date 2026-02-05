#!/bin/bash
set -e

echo "=== Xcode Cloud: Initializing submodules ==="
cd "$CI_PRIMARY_REPOSITORY_PATH"
git submodule update --init --recursive

echo "=== Submodule contents ==="
ls -la ios-apps/final-hourglass/

echo "=== Verifying workspace exists ==="
if [ -d "ios-apps/final-hourglass/FinalHourglass.xcworkspace" ]; then
    echo "✅ Workspace found!"
else
    echo "❌ Workspace not found!"
    exit 1
fi

echo "=== Done ==="
