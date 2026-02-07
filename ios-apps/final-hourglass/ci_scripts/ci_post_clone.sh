#!/bin/bash
set -e

echo "=== Xcode Cloud: Build Environment ==="
echo "CI_PRIMARY_REPOSITORY_PATH: $CI_PRIMARY_REPOSITORY_PATH"
echo "CI_WORKSPACE: $CI_WORKSPACE"

# SwiftLint インストール（Xcode Cloud 環境用）
echo "=== Installing SwiftLint ==="
if which brew >/dev/null; then
    brew install swiftlint 2>/dev/null || echo "✅ SwiftLint already installed or skipped"
    if which swiftlint >/dev/null; then
        echo "✅ SwiftLint version: $(swiftlint version)"
    fi
else
    echo "⚠️ Homebrew not available, skipping SwiftLint installation"
fi

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
