#!/bin/bash

# 承認音を再生するスクリプト
# macOSのafplayコマンドを使用してシステムサウンドを再生

# システムサウンドのパス
SOUND_PATH="/System/Library/Sounds/Glass.aiff"

# サウンドを再生
if [ -f "$SOUND_PATH" ]; then
    afplay "$SOUND_PATH" &
else
    # 代替音（Ping）
    afplay "/System/Library/Sounds/Ping.aiff" &
fi