#!/usr/bin/env python3
"""
SuperClaude Project Configuration Override System
プロジェクト別設定オーバーライド機能
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field, asdict
import yaml
import re


@dataclass
class ProjectConfig:
    """プロジェクト固有の設定"""
    project_name: str
    project_path: str
    
    # フラグのオーバーライド
    default_flags: List[str] = field(default_factory=list)
    disabled_flags: List[str] = field(default_factory=list)
    
    # モードのデフォルト設定
    default_mode: Optional[str] = None
    mode_preferences: Dict[str, bool] = field(default_factory=dict)
    
    # MCPサーバー設定
    enabled_mcp_servers: List[str] = field(default_factory=list)
    disabled_mcp_servers: List[str] = field(default_factory=list)
    mcp_server_config: Dict[str, Any] = field(default_factory=dict)
    
    # ツール設定
    preferred_tools: Dict[str, str] = field(default_factory=dict)
    tool_shortcuts: Dict[str, str] = field(default_factory=dict)
    
    # パフォーマンス設定
    max_parallel_tasks: int = 10
    token_limit: int = 100000
    auto_token_efficiency: bool = True
    
    # コーディング規約
    code_style: Dict[str, Any] = field(default_factory=dict)
    naming_conventions: Dict[str, str] = field(default_factory=dict)
    file_patterns: Dict[str, str] = field(default_factory=dict)
    
    # カスタムルール
    custom_rules: List[Dict[str, Any]] = field(default_factory=list)
    validation_rules: List[str] = field(default_factory=list)
    
    # 自動化設定
    auto_sync: bool = True
    auto_test: bool = True
    auto_commit: bool = False
    auto_format: bool = True
    
    # 環境変数
    env_vars: Dict[str, str] = field(default_factory=dict)
    
    # メタデータ
    created_at: str = ""
    updated_at: str = ""
    version: str = "1.0.0"


class ProjectConfigManager:
    """プロジェクト設定管理システム"""
    
    CONFIG_FILENAMES = [
        ".superclaude.json",
        ".superclaude.yaml",
        ".claude/config.json",
        ".claude/config.yaml",
        "claude.config.json",
        "claude.config.yaml"
    ]
    
    def __init__(self, global_config_dir: str = "~/.claude"):
        self.global_config_dir = Path(global_config_dir).expanduser()
        self.projects_config_dir = self.global_config_dir / "projects"
        self.projects_config_dir.mkdir(parents=True, exist_ok=True)
        
        # グローバル設定を読み込み
        self.global_config = self._load_global_config()
        
        # プロジェクト設定キャッシュ
        self.project_configs: Dict[str, ProjectConfig] = {}
        
        # 現在のプロジェクト
        self.current_project: Optional[ProjectConfig] = None
    
    def _load_global_config(self) -> Dict[str, Any]:
        """グローバル設定を読み込み"""
        global_config_file = self.global_config_dir / "CLAUDE.md"
        config = {
            "default_flags": [],
            "default_mode": None,
            "enabled_mcp_servers": [],
            "max_parallel_tasks": 10,
            "token_limit": 100000
        }
        
        # FLAGS.mdから設定を抽出
        flags_file = self.global_config_dir / "FLAGS.md"
        if flags_file.exists():
            with open(flags_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # デフォルトフラグを抽出
                if "Default flags:" in content:
                    flags_match = re.search(r"Default flags:\s*\[(.*?)\]", content)
                    if flags_match:
                        config["default_flags"] = [f.strip() for f in flags_match.group(1).split(",")]
        
        return config
    
    def detect_project_config(self, project_path: str) -> Optional[ProjectConfig]:
        """プロジェクト設定ファイルを検出して読み込み"""
        project_path = Path(project_path).resolve()
        
        # キャッシュチェック
        path_str = str(project_path)
        if path_str in self.project_configs:
            return self.project_configs[path_str]
        
        # 設定ファイルを探す
        for config_name in self.CONFIG_FILENAMES:
            config_file = project_path / config_name
            if config_file.exists():
                config = self._load_config_file(config_file)
                if config:
                    # プロジェクト設定オブジェクトを作成
                    project_config = self._create_project_config(path_str, config)
                    self.project_configs[path_str] = project_config
                    return project_config
        
        # 保存された設定をチェック
        saved_config = self._load_saved_config(path_str)
        if saved_config:
            self.project_configs[path_str] = saved_config
            return saved_config
        
        return None
    
    def create_project_config(self, project_path: str, config_data: Optional[Dict[str, Any]] = None) -> ProjectConfig:
        """新しいプロジェクト設定を作成"""
        project_path = Path(project_path).resolve()
        project_name = project_path.name
        
        # デフォルト設定を作成
        config = ProjectConfig(
            project_name=project_name,
            project_path=str(project_path),
            created_at=self._get_timestamp(),
            updated_at=self._get_timestamp()
        )
        
        # カスタム設定を適用
        if config_data:
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        # グローバル設定を継承
        config.default_flags = self.global_config.get("default_flags", [])
        config.max_parallel_tasks = self.global_config.get("max_parallel_tasks", 10)
        config.token_limit = self.global_config.get("token_limit", 100000)
        
        # 保存
        self._save_project_config(config)
        self.project_configs[str(project_path)] = config
        
        return config
    
    def get_active_config(self, project_path: Optional[str] = None) -> Dict[str, Any]:
        """現在アクティブな設定を取得（マージ済み）"""
        if project_path:
            project_config = self.detect_project_config(project_path)
            if project_config:
                self.current_project = project_config
        
        if not self.current_project:
            return self.global_config
        
        # グローバル設定とプロジェクト設定をマージ
        merged = self.global_config.copy()
        project_dict = asdict(self.current_project)
        
        # プロジェクト設定で上書き
        for key, value in project_dict.items():
            if value is not None and value != [] and value != {}:
                if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key].update(value)
                elif key in merged and isinstance(merged[key], list) and isinstance(value, list):
                    # リストは結合ではなく置き換え
                    merged[key] = value
                else:
                    merged[key] = value
        
        # 無効化されたフラグを除外
        if "disabled_flags" in project_dict:
            merged["default_flags"] = [f for f in merged.get("default_flags", []) 
                                     if f not in project_dict["disabled_flags"]]
        
        # 無効化されたMCPサーバーを除外
        if "disabled_mcp_servers" in project_dict:
            merged["enabled_mcp_servers"] = [s for s in merged.get("enabled_mcp_servers", [])
                                            if s not in project_dict["disabled_mcp_servers"]]
        
        return merged
    
    def update_project_config(self, project_path: str, updates: Dict[str, Any]) -> ProjectConfig:
        """プロジェクト設定を更新"""
        config = self.detect_project_config(project_path)
        
        if not config:
            config = self.create_project_config(project_path, updates)
        else:
            # 既存設定を更新
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            config.updated_at = self._get_timestamp()
            
            # 保存
            self._save_project_config(config)
        
        return config
    
    def add_custom_rule(self, project_path: str, rule: Dict[str, Any]) -> None:
        """カスタムルールを追加"""
        config = self.detect_project_config(project_path)
        
        if not config:
            config = self.create_project_config(project_path)
        
        config.custom_rules.append(rule)
        config.updated_at = self._get_timestamp()
        
        self._save_project_config(config)
    
    def set_tool_shortcut(self, project_path: str, shortcut: str, command: str) -> None:
        """ツールショートカットを設定"""
        config = self.detect_project_config(project_path)
        
        if not config:
            config = self.create_project_config(project_path)
        
        config.tool_shortcuts[shortcut] = command
        config.updated_at = self._get_timestamp()
        
        self._save_project_config(config)
    
    def export_config(self, project_path: str, output_path: Optional[str] = None) -> str:
        """プロジェクト設定をエクスポート"""
        config = self.detect_project_config(project_path)
        
        if not config:
            raise ValueError(f"No configuration found for project: {project_path}")
        
        if not output_path:
            output_path = Path(project_path) / ".superclaude.json"
        
        output_path = Path(output_path)
        
        # JSON形式でエクスポート
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(config), f, indent=2, ensure_ascii=False)
        
        return str(output_path)
    
    def import_config(self, project_path: str, config_file: str) -> ProjectConfig:
        """設定ファイルをインポート"""
        config_data = self._load_config_file(Path(config_file))
        
        if not config_data:
            raise ValueError(f"Invalid configuration file: {config_file}")
        
        return self.create_project_config(project_path, config_data)
    
    def _load_config_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """設定ファイルを読み込み"""
        try:
            if file_path.suffix in ['.json']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            elif file_path.suffix in ['.yaml', '.yml']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading config file {file_path}: {e}")
        
        return None
    
    def _create_project_config(self, project_path: str, config_data: Dict[str, Any]) -> ProjectConfig:
        """設定データからProjectConfigを作成"""
        # プロジェクト名を推測
        project_name = config_data.get("project_name", Path(project_path).name)
        
        config = ProjectConfig(
            project_name=project_name,
            project_path=project_path
        )
        
        # 設定データを適用
        for key, value in config_data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        if not config.created_at:
            config.created_at = self._get_timestamp()
        config.updated_at = self._get_timestamp()
        
        return config
    
    def _save_project_config(self, config: ProjectConfig) -> None:
        """プロジェクト設定を保存"""
        # プロジェクトパスのハッシュを使ってファイル名を作成
        import hashlib
        project_hash = hashlib.md5(config.project_path.encode()).hexdigest()[:12]
        
        config_file = self.projects_config_dir / f"{project_hash}.json"
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(config), f, indent=2, ensure_ascii=False)
    
    def _load_saved_config(self, project_path: str) -> Optional[ProjectConfig]:
        """保存された設定を読み込み"""
        import hashlib
        project_hash = hashlib.md5(project_path.encode()).hexdigest()[:12]
        
        config_file = self.projects_config_dir / f"{project_hash}.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return ProjectConfig(**data)
            except Exception:
                pass
        
        return None
    
    def _get_timestamp(self) -> str:
        """タイムスタンプを取得"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_project_summary(self, project_path: str) -> Dict[str, Any]:
        """プロジェクト設定のサマリーを取得"""
        config = self.detect_project_config(project_path)
        
        if not config:
            return {"status": "No configuration found"}
        
        return {
            "project_name": config.project_name,
            "project_path": config.project_path,
            "active_flags": config.default_flags,
            "default_mode": config.default_mode,
            "mcp_servers": len(config.enabled_mcp_servers),
            "custom_rules": len(config.custom_rules),
            "tool_shortcuts": len(config.tool_shortcuts),
            "auto_features": {
                "sync": config.auto_sync,
                "test": config.auto_test,
                "format": config.auto_format,
                "commit": config.auto_commit
            },
            "last_updated": config.updated_at
        }


# グローバルインスタンス
config_manager = ProjectConfigManager()


# 便利な関数
def get_project_config(project_path: Optional[str] = None) -> Dict[str, Any]:
    """現在のプロジェクト設定を取得"""
    if not project_path:
        project_path = os.getcwd()
    
    return config_manager.get_active_config(project_path)


def update_project_setting(key: str, value: Any, project_path: Optional[str] = None) -> None:
    """プロジェクト設定を更新"""
    if not project_path:
        project_path = os.getcwd()
    
    config_manager.update_project_config(project_path, {key: value})


if __name__ == "__main__":
    # テスト実行
    manager = ProjectConfigManager()
    
    # テストプロジェクトの設定を作成
    test_config = manager.create_project_config(
        "/test/ultra-think",
        {
            "default_flags": ["--ultrathink", "--parallel"],
            "default_mode": "orchestration",
            "enabled_mcp_servers": ["serena", "github", "context7"],
            "auto_sync": True,
            "auto_test": True,
            "code_style": {
                "indent": 2,
                "quotes": "single",
                "semicolons": False
            },
            "tool_shortcuts": {
                "sync": "python3 auto_startup_sync.py",
                "test": "pytest tests/ -v",
                "format": "ruff format src/"
            }
        }
    )
    
    print("Created project config:")
    print(json.dumps(manager.get_project_summary("/test/ultra-think"), indent=2, ensure_ascii=False))
    
    # アクティブな設定を取得
    active = manager.get_active_config("/test/ultra-think")
    print("\nActive configuration:")
    print(json.dumps(active, indent=2, ensure_ascii=False))