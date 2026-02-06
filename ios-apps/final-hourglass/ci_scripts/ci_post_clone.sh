#!/bin/bash
set -e

echo "=== Xcode Cloud: Build Environment ==="
echo "CI_PRIMARY_REPOSITORY_PATH: $CI_PRIMARY_REPOSITORY_PATH"
echo "CI_WORKSPACE: $CI_WORKSPACE"

echo "=== Verifying workspace exists ==="
WORKSPACE_PATH="$CI_PRIMARY_REPOSITORY_PATH/ios-apps/final-hourglass/FinalHourglass.xcworkspace"
if [ -d "$WORKSPACE_PATH" ]; then
    echo "✅ Workspace found at: $WORKSPACE_PATH"
    ls -la "$CI_PRIMARY_REPOSITORY_PATH/ios-apps/final-hourglass/"
else
    echo "❌ Workspace not found!"
    exit 1
fi

echo "=== Done ==="
