#!/usr/bin/env python3
"""
Ultra Think 通知システム
Claude Code承認時の音声通知を管理する高度なシステム
"""

import os
import subprocess
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import logging

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UltraThinkNotificationSystem:
    """Ultra Think通知管理システム"""
    
    def __init__(self):
        """初期化"""
        self.hooks_dir = Path.home() / ".claude" / "hooks"
        self.sounds_dir = Path("/System/Library/Sounds")
        self.config_file = Path.home() / ".claude" / "notification_config.json"
        
        # デフォルト設定
        self.default_config = {
            "approval_sound": "/System/Library/Sounds/Glass.aiff",
            "error_sound": "/System/Library/Sounds/Basso.aiff",
            "success_sound": "/System/Library/Sounds/Hero.aiff",
            "warning_sound": "/System/Library/Sounds/Ping.aiff",
            "volume": 0.7,
            "enabled": True
        }
        
        # 設定を読み込み
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """設定を読み込む"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"設定読み込みエラー: {e}")
        return self.default_config.copy()
    
    def save_config(self):
        """設定を保存"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"設定を保存: {self.config_file}")
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
    
    def list_available_sounds(self) -> List[str]:
        """利用可能なサウンドをリスト"""
        sounds = []
        if self.sounds_dir.exists():
            for sound_file in self.sounds_dir.glob("*.aiff"):
                sounds.append(str(sound_file))
        return sorted(sounds)
    
    def create_hook(self, hook_name: str, sound_path: str, message: str = ""):
        """フックスクリプトを作成"""
        hook_path = self.hooks_dir / hook_name
        
        script_content = f"""#!/bin/bash
# Ultra Think Notification Hook: {hook_name}
# Generated: {datetime.now().isoformat()}
# Message: {message}

# Play notification sound
afplay "{sound_path}" &

# Optional: Display notification (macOS)
if command -v osascript &> /dev/null; then
    osascript -e 'display notification "{message}" with title "Claude Code" sound name "Glass"' 2>/dev/null &
fi

# Log the event
echo "[$(date)] Hook '{hook_name}' triggered" >> ~/.claude/hooks.log

# Exit successfully
exit 0
"""
        
        try:
            # ディレクトリを作成
            self.hooks_dir.mkdir(parents=True, exist_ok=True)
            
            # スクリプトを書き込み
            with open(hook_path, 'w') as f:
                f.write(script_content)
            
            # 実行権限を付与
            os.chmod(hook_path, 0o755)
            
            logger.info(f"フック作成: {hook_path}")
            return True
            
        except Exception as e:
            logger.error(f"フック作成エラー: {e}")
            return False
    
    def setup_all_hooks(self):
        """すべての標準フックを設定"""
        hooks = {
            "tool-use-blocked": {
                "sound": self.config["approval_sound"],
                "message": "承認が必要です"
            },
            "tool-use-approved": {
                "sound": self.config["success_sound"],
                "message": "承認されました"
            },
            "tool-use-denied": {
                "sound": self.config["warning_sound"],
                "message": "拒否されました"
            },
            "user-prompt-submit-hook": {
                "sound": self.config["approval_sound"],
                "message": "プロンプトを送信中"
            },
            "completion-hook": {
                "sound": self.config["success_sound"],
                "message": "処理完了"
            },
            "error-hook": {
                "sound": self.config["error_sound"],
                "message": "エラーが発生しました"
            }
        }
        
        success_count = 0
        for hook_name, settings in hooks.items():
            if self.create_hook(hook_name, settings["sound"], settings["message"]):
                success_count += 1
        
        logger.info(f"フック設定完了: {success_count}/{len(hooks)}")
        return success_count == len(hooks)
    
    def test_sound(self, sound_path: str):
        """サウンドをテスト再生"""
        try:
            subprocess.run(["afplay", sound_path], check=True)
            logger.info(f"サウンドテスト成功: {sound_path}")
            return True
        except Exception as e:
            logger.error(f"サウンドテストエラー: {e}")
            return False
    
    def create_advanced_hook(self, hook_name: str):
        """高度な条件付きフックを作成"""
        hook_path = self.hooks_dir / hook_name
        
        script_content = f'''#!/usr/bin/env python3
"""
Ultra Think Advanced Hook: {hook_name}
条件に応じて異なる通知を行う高度なフック
"""

import os
import sys
import json
import subprocess
from datetime import datetime

def play_sound(sound_path):
    """サウンドを再生"""
    subprocess.run(["afplay", sound_path], capture_output=True)

def log_event(message):
    """イベントをログに記録"""
    log_file = os.path.expanduser("~/.claude/hooks.log")
    with open(log_file, "a") as f:
        f.write(f"[{{datetime.now().isoformat()}}] {{message}}\\n")

def main():
    # 環境変数から情報を取得
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "unknown")
    tool_params = os.environ.get("CLAUDE_TOOL_PARAMS", "{{}}")
    
    # 設定を読み込み
    config_file = os.path.expanduser("~/.claude/notification_config.json")
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            config = json.load(f)
    else:
        config = {{
            "approval_sound": "/System/Library/Sounds/Glass.aiff",
            "error_sound": "/System/Library/Sounds/Basso.aiff",
            "success_sound": "/System/Library/Sounds/Hero.aiff"
        }}
    
    # ツールに応じて異なるサウンドを再生
    if "bash" in tool_name.lower():
        if "rm" in tool_params or "delete" in tool_params:
            # 削除操作には警告音
            play_sound("/System/Library/Sounds/Funk.aiff")
            log_event(f"警告: 削除操作 - {{tool_name}}")
        else:
            play_sound(config["approval_sound"])
    elif "write" in tool_name.lower() or "edit" in tool_name.lower():
        # ファイル編集には特別な音
        play_sound("/System/Library/Sounds/Pop.aiff")
        log_event(f"ファイル編集: {{tool_name}}")
    else:
        # デフォルト
        play_sound(config["approval_sound"])
        log_event(f"ツール実行: {{tool_name}}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
        
        try:
            with open(hook_path, 'w') as f:
                f.write(script_content)
            os.chmod(hook_path, 0o755)
            logger.info(f"高度なフック作成: {hook_path}")
            return True
        except Exception as e:
            logger.error(f"高度なフック作成エラー: {e}")
            return False
    
    def generate_report(self):
        """通知システムレポートを生成"""
        report = f"""# Ultra Think 通知システムレポート

## 生成日時
{datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}

## 現在の設定
```json
{json.dumps(self.config, indent=2, ensure_ascii=False)}
```

## インストール済みフック
"""
        if self.hooks_dir.exists():
            for hook in self.hooks_dir.glob("*"):
                if hook.is_file():
                    report += f"- ✅ {hook.name}\n"
        else:
            report += "- ❌ フックディレクトリが存在しません\n"
        
        report += f"""
## 利用可能なシステムサウンド
"""
        for sound in self.list_available_sounds()[:10]:  # 最初の10個
            report += f"- {Path(sound).name}\n"
        
        report += f"""
## 動作確認
1. Claude Codeで承認が必要な操作を実行
2. Glass.aiffサウンドが再生されることを確認
3. 承認/拒否時に適切なサウンドが再生されることを確認

## トラブルシューティング
- サウンドが再生されない場合:
  - macOSのサウンド設定を確認
  - フックファイルの実行権限を確認: `ls -la ~/.claude/hooks/`
  - ログファイルを確認: `cat ~/.claude/hooks.log`

## カスタマイズ
設定ファイル: `~/.claude/notification_config.json`
を編集してサウンドをカスタマイズできます。
"""
        
        report_file = "NOTIFICATION_SYSTEM_REPORT.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"レポート生成: {report_file}")
        return report_file


def main():
    """メイン実行関数"""
    logger.info("=" * 60)
    logger.info("Ultra Think 通知システム セットアップ")
    logger.info("=" * 60)
    
    # システムを初期化
    notification_system = UltraThinkNotificationSystem()
    
    # すべてのフックを設定
    logger.info("フックを設定中...")
    if notification_system.setup_all_hooks():
        logger.info("✅ すべてのフックが正常に設定されました")
    else:
        logger.warning("⚠️ 一部のフックの設定に失敗しました")
    
    # Glass.aiffをテスト
    logger.info("\nGlass.aiffサウンドをテスト中...")
    if notification_system.test_sound("/System/Library/Sounds/Glass.aiff"):
        logger.info("✅ サウンドテスト成功")
    else:
        logger.error("❌ サウンドテスト失敗")
    
    # 高度なフックも作成
    logger.info("\n高度なフックを作成中...")
    notification_system.create_advanced_hook("tool-use-conditional")
    
    # 設定を保存
    notification_system.save_config()
    
    # レポートを生成
    report_file = notification_system.generate_report()
    logger.info(f"\n✅ セットアップ完了！")
    logger.info(f"詳細レポート: {report_file}")
    
    logger.info("\n" + "=" * 60)
    logger.info("Claude Codeを再起動して設定を反映してください")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()