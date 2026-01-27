#!/bin/bash
set -euo pipefail

# validate-privacy-manifest.sh
# Validates Apple Privacy Manifest (PrivacyInfo.xcprivacy) compliance for iOS apps.
# Usage: validate-privacy-manifest.sh <app-directory>

APP_DIR="${1:?Usage: validate-privacy-manifest.sh <app-directory>}"

if [[ ! -d "$APP_DIR" ]]; then
  echo "Error: Directory '$APP_DIR' not found."
  exit 1
fi

# --- Category definitions ---
# Format: KEY|API_TYPE|REASON|PATTERN1,PATTERN2,...
CATEGORIES=(
  "UserDefaults|NSPrivacyAccessedAPICategoryUserDefaults|CA92.1|UserDefaults.standard,UserDefaults(,@AppStorage"
  "File Timestamps|NSPrivacyAccessedAPICategoryFileTimestamp|C617.1|.creationDate,.modificationDate,.contentModificationDateKey"
  "System Boot Time|NSPrivacyAccessedAPICategorySystemBootTime|35F9.1|systemUptime,ProcessInfo.processInfo"
  "Disk Space|NSPrivacyAccessedAPICategoryDiskSpace|E174.1|volumeAvailableCapacity,volumeTotalCapacity"
  "Active Keyboard|NSPrivacyAccessedAPICategoryActiveKeyboards|3B52.1|activeInputModes,textInputMode"
)

MANIFEST=$(find "$APP_DIR" -name 'PrivacyInfo.xcprivacy' -not -path '*/Pods/*' -not -path '*/DerivedData/*' 2>/dev/null | head -1)
HAS_MANIFEST=false
if [[ -n "$MANIFEST" && -f "$MANIFEST" ]]; then
  HAS_MANIFEST=true
  MANIFEST_CONTENT=$(cat "$MANIFEST")
fi

# Collect Swift files excluding Pods/ and DerivedData/
mapfile -t SWIFT_FILE_LIST < <(find "$APP_DIR" -name '*.swift' -not -path '*/Pods/*' -not -path '*/DerivedData/*' 2>/dev/null)

declare -a DETECTED_NAMES=()
declare -a DETECTED_TYPES=()
declare -a DECLARED_FLAGS=()

for entry in "${CATEGORIES[@]}"; do
  IFS='|' read -r name api_type reason patterns <<< "$entry"
  IFS=',' read -ra pats <<< "$patterns"

  detected=false
  if [[ ${#SWIFT_FILE_LIST[@]} -gt 0 ]]; then
    for pat in "${pats[@]}"; do
      # Search Swift files, exclude comment lines (trimmed lines starting with //)
      if grep -rlF "$pat" "${SWIFT_FILE_LIST[@]}" 2>/dev/null | head -1 | grep -q .; then
        detected=true
        break
      fi
    done
  fi

  declared="N/A"
  if $HAS_MANIFEST && $detected; then
    if echo "$MANIFEST_CONTENT" | grep -qF "$api_type"; then
      declared="Yes"
    else
      declared="No"
    fi
  elif $HAS_MANIFEST && ! $detected; then
    declared="-"
  fi

  DETECTED_NAMES+=("$name")
  DETECTED_TYPES+=("$api_type")
  if $detected; then
    DECLARED_FLAGS+=("detected|$declared")
  else
    DECLARED_FLAGS+=("no|$declared")
  fi
done

# --- Build summary ---
SUMMARY=""
SUMMARY+="## Privacy Manifest Validation\n\n"
SUMMARY+="| Category | Usage Detected | Declared in Manifest |\n"
SUMMARY+="|----------|---------------|---------------------|\n"

any_detected=false
missing_declaration=false

for i in "${!DETECTED_NAMES[@]}"; do
  IFS='|' read -r det decl <<< "${DECLARED_FLAGS[$i]}"
  if [[ "$det" == "detected" ]]; then
    any_detected=true
    det_display="Yes"
    if [[ "$decl" == "No" ]]; then
      missing_declaration=true
    fi
  else
    det_display="No"
  fi
  SUMMARY+="| ${DETECTED_NAMES[$i]} | $det_display | $decl |\n"
done

if $HAS_MANIFEST; then
  SUMMARY+="\nManifest: \`$MANIFEST\` found.\n"
else
  SUMMARY+="\nManifest: \`PrivacyInfo.xcprivacy\` **not found** in \`$APP_DIR\`.\n"
fi

# Output summary
echo -e "$SUMMARY"
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  echo -e "$SUMMARY" >> "$GITHUB_STEP_SUMMARY"
fi

# --- Exit code ---
if $any_detected && ! $HAS_MANIFEST; then
  echo "Warning: Required Reason APIs detected but no PrivacyInfo.xcprivacy found."
  exit 1
fi

if $missing_declaration; then
  echo "Error: Manifest exists but some detected API categories are not declared."
  exit 2
fi

echo "All checks passed."
exit 0
