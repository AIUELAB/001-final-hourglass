#!/usr/bin/env python3
"""
Apple App Store Guidelines準拠コード品質チェックツール

App Store Review Guidelinesに準拠したコード品質を自動チェック
Guidelines 2.5: プライベートAPI使用禁止
Guidelines 5.1: プライバシー要件
Guidelines 2.1: アプリの完全性
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


@dataclass
class CodeIssue:
    """コード品質問題を表すデータクラス"""
    file_path: str
    line_number: int
    issue_type: str
    severity: str  # 'error', 'warning', 'info'
    message: str
    guideline_ref: str  # App Store Guidelines参照
    suggestion: str = ""

class AppStoreCodeQualityChecker:
    """App Store Guidelines準拠のコード品質チェッカー"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.issues: List[CodeIssue] = []
        
        # App Store Guidelines違反パターン
        self.private_api_patterns = [
            # Guidelines 2.5.1: プライベートAPI使用禁止
            r'_[A-Z][a-zA-Z]*\s*\(',  # プライベートメソッド呼び出し
            r'UIApplication\.shared\._[a-zA-Z]',  # UIApplicationのプライベートプロパティ
            r'NSBundle\._[a-zA-Z]',  # NSBundleのプライベートAPI
            r'UIDevice\._[a-zA-Z]',  # UIDeviceのプライベートAPI
            r'_UIAlertController',  # プライベートクラス使用
        ]
        
        # プライバシー関連パターン（Guidelines 5.1）
        self.privacy_violation_patterns = [
            r'UIDevice\.current\.identifierForVendor',  # デバイス識別子
            r'ASIdentifierManager\.shared\(\)\.advertisingIdentifier',  # 広告識別子
            r'CTTelephonyNetworkInfo',  # 通信事業者情報
            r'CLLocationManager.*requestAlwaysAuthorization',  # 常時位置情報要求
            r'AVCaptureDevice.*requestAccess.*\.microphone',  # マイクアクセス
            r'AVCaptureDevice.*requestAccess.*\.video',  # カメラアクセス
            r'CNContactStore',  # 連絡先アクセス
            r'PHPhotoLibrary',  # 写真ライブラリアクセス
        ]
        
        # パフォーマンス問題パターン（Guidelines 2.4）
        self.performance_issue_patterns = [
            r'synchronousRequest',  # 同期通信
            r'performSelector.*onMainThread',  # メインスレッドでの重い処理
            r'for.*in.*array.*{.*sleep',  # ループ内でのスリープ
            r'UIImage\(named:.*\).*\.jpegData',  # 毎回画像変換
        ]
        
        # セキュリティ問題パターン（Guidelines 5.1.3）
        self.security_issue_patterns = [
            r'UserDefaults\.standard\.set.*password',  # パスワードのUserDefaults保存
            r'http://.*\.com',  # HTTP通信（HTTPS必須）
            r'NSLog.*password',  # ログにパスワード出力
            r'print.*token',  # 認証トークンのprint
        ]

    def run_quality_check(self) -> Dict[str, Any]:
        """品質チェックを実行"""
        print("🔍 App Store Guidelines準拠コード品質チェックを開始...")
        
        # 1. Swiftファイルの解析
        swift_files = self._find_swift_files()
        for swift_file in swift_files:
            self._analyze_swift_file(swift_file)
        
        # 2. Info.plistの検証
        self._check_info_plist()
        
        # 3. Entitlementsの検証
        self._check_entitlements()
        
        # 4. Xcodeプロジェクト設定の検証
        self._check_xcode_settings()
        
        # 5. 依存関係の検証
        self._check_dependencies()
        
        # 6. リソースファイルの検証
        self._check_resources()
        
        return self._generate_report()

    def _find_swift_files(self) -> List[Path]:
        """Swiftファイルを再帰的に検索"""
        swift_files = []
        for root, dirs, files in os.walk(self.project_path):
            # 除外ディレクトリ
            dirs[:] = [d for d in dirs if d not in ['.git', 'Pods', 'DerivedData', '.build']]
            
            for file in files:
                if file.endswith('.swift'):
                    swift_files.append(Path(root) / file)
        
        return swift_files

    def _analyze_swift_file(self, file_path: Path):
        """個別Swiftファイルの解析"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    # プライベートAPI使用チェック
                    self._check_private_api_usage(file_path, line_num, line)
                    
                    # プライバシー違反チェック
                    self._check_privacy_violations(file_path, line_num, line)
                    
                    # パフォーマンス問題チェック
                    self._check_performance_issues(file_path, line_num, line)
                    
                    # セキュリティ問題チェック
                    self._check_security_issues(file_path, line_num, line)
                    
                    # その他のApp Store Guidelines違反
                    self._check_other_violations(file_path, line_num, line)
                
        except Exception as e:
            self.issues.append(CodeIssue(
                file_path=str(file_path),
                line_number=0,
                issue_type="file_read_error",
                severity="error",
                message=f"ファイル読み込みエラー: {str(e)}",
                guideline_ref="N/A"
            ))

    def _check_private_api_usage(self, file_path: Path, line_num: int, line: str):
        """プライベートAPI使用をチェック（Guidelines 2.5.1）"""
        for pattern in self.private_api_patterns:
            if re.search(pattern, line):
                self.issues.append(CodeIssue(
                    file_path=str(file_path),
                    line_number=line_num,
                    issue_type="private_api_usage",
                    severity="error",
                    message=f"プライベートAPI使用の可能性: {line.strip()}",
                    guideline_ref="2.5.1",
                    suggestion="公開されているAPIを使用してください。プライベートAPIの使用はApp Storeリジェクトの原因となります。"
                ))

    def _check_privacy_violations(self, file_path: Path, line_num: int, line: str):
        """プライバシー違反をチェック（Guidelines 5.1）"""
        privacy_checks = [
            (r'UIDevice\.current\.identifierForVendor', "デバイス識別子の使用は適切なプライバシー説明が必要"),
            (r'ASIdentifierManager.*advertisingIdentifier', "広告識別子使用にはApp Tracking Transparency対応必須"),
            (r'CLLocationManager.*requestWhenInUseAuthorization', "位置情報使用理由をInfo.plistに記載"),
            (r'AVCaptureDevice.*requestAccess.*microphone', "マイクアクセス理由をInfo.plistに記載"),
            (r'AVCaptureDevice.*requestAccess.*video', "カメラアクセス理由をInfo.plistに記載"),
            (r'PHPhotoLibrary.*requestAuthorization', "写真ライブラリアクセス理由をInfo.plistに記載"),
        ]
        
        for pattern, suggestion in privacy_checks:
            if re.search(pattern, line):
                self.issues.append(CodeIssue(
                    file_path=str(file_path),
                    line_number=line_num,
                    issue_type="privacy_violation",
                    severity="warning",
                    message=f"プライバシー関連API使用: {line.strip()}",
                    guideline_ref="5.1",
                    suggestion=suggestion
                ))

    def _check_performance_issues(self, file_path: Path, line_num: int, line: str):
        """パフォーマンス問題をチェック（Guidelines 2.4）"""
        performance_checks = [
            (r'URLSession\.shared\.synchronousDataTask', "同期通信はメインスレッドをブロックします"),
            (r'\.synchronousRequest', "同期リクエストの使用は避けてください"),
            (r'DispatchQueue\.main\.sync', "メインキューでの同期実行は避けてください"),
            (r'Thread\.sleep', "UIスレッドでのスリープは避けてください"),
        ]
        
        for pattern, suggestion in performance_checks:
            if re.search(pattern, line):
                self.issues.append(CodeIssue(
                    file_path=str(file_path),
                    line_number=line_num,
                    issue_type="performance_issue",
                    severity="warning",
                    message=f"パフォーマンス問題: {line.strip()}",
                    guideline_ref="2.4",
                    suggestion=suggestion
                ))

    def _check_security_issues(self, file_path: Path, line_num: int, line: str):
        """セキュリティ問題をチェック（Guidelines 5.1.3）"""
        security_checks = [
            (r'UserDefaults.*\.set.*password', "パスワードはUserDefaultsではなくKeychainに保存"),
            (r'http://(?!127\.0\.0\.1|localhost)', "本番環境ではHTTPS通信を使用してください"),
            (r'NSLog.*(?:password|token|secret)', "機密情報をログ出力しないでください"),
            (r'print.*(?:password|token|secret)', "機密情報をprint文で出力しないでください"),
        ]
        
        for pattern, suggestion in security_checks:
            if re.search(pattern, line, re.IGNORECASE):
                self.issues.append(CodeIssue(
                    file_path=str(file_path),
                    line_number=line_num,
                    issue_type="security_issue",
                    severity="error",
                    message=f"セキュリティ問題: {line.strip()}",
                    guideline_ref="5.1.3",
                    suggestion=suggestion
                ))

    def _check_other_violations(self, file_path: Path, line_num: int, line: str):
        """その他のGuidelines違反をチェック"""
        other_checks = [
            (r'UIApplication\.shared\.openURL.*itms-apps', "他アプリのApp Store評価ページへの直接誘導は制限される場合があります"),
            (r'SKStoreReviewController\.requestReview', "レビュー要求は適切なタイミングで行ってください"),
            (r'exit\(', "アプリの強制終了は避けてください"),
            (r'abort\(\)', "アプリの異常終了は避けてください"),
        ]
        
        for pattern, suggestion in other_checks:
            if re.search(pattern, line):
                severity = "error" if "exit" in pattern or "abort" in pattern else "warning"
                self.issues.append(CodeIssue(
                    file_path=str(file_path),
                    line_number=line_num,
                    issue_type="guideline_violation",
                    severity=severity,
                    message=f"Guidelines違反の可能性: {line.strip()}",
                    guideline_ref="Various",
                    suggestion=suggestion
                ))

    def _check_info_plist(self):
        """Info.plistの検証"""
        info_plist_path = self.project_path / "Info.plist"
        
        # 複数の可能な場所を検索
        possible_paths = [
            self.project_path / "Info.plist",
            self.project_path / "Supporting Files" / "Info.plist",
            next(self.project_path.glob("**/Info.plist"), None)
        ]
        
        info_plist_path = None
        for path in possible_paths:
            if path and path.exists():
                info_plist_path = path
                break
        
        if not info_plist_path:
            self.issues.append(CodeIssue(
                file_path="Info.plist",
                line_number=0,
                issue_type="missing_file",
                severity="error",
                message="Info.plistファイルが見つかりません",
                guideline_ref="2.1",
                suggestion="Info.plistファイルは必須です"
            ))
            return
        
        try:
            # plistlib使用（Pythonビルトイン）
            import plistlib
            with open(info_plist_path, 'rb') as f:
                plist_data = plistlib.load(f)
            
            self._validate_info_plist_content(plist_data, info_plist_path)
            
        except Exception as e:
            self.issues.append(CodeIssue(
                file_path=str(info_plist_path),
                line_number=0,
                issue_type="plist_parse_error",
                severity="error",
                message=f"Info.plistの解析エラー: {str(e)}",
                guideline_ref="2.1"
            ))

    def _validate_info_plist_content(self, plist_data: dict, file_path: Path):
        """Info.plistの内容検証"""
        required_keys = [
            ("CFBundleIdentifier", "Bundle Identifierは必須です"),
            ("CFBundleVersion", "Bundle Versionは必須です"),
            ("CFBundleShortVersionString", "Version Stringは必須です"),
            ("CFBundleName", "Bundle Nameは必須です"),
        ]
        
        for key, message in required_keys:
            if key not in plist_data:
                self.issues.append(CodeIssue(
                    file_path=str(file_path),
                    line_number=0,
                    issue_type="missing_plist_key",
                    severity="error",
                    message=f"必須キーが不足: {key}",
                    guideline_ref="2.1",
                    suggestion=message
                ))
        
        # プライバシー関連Usage Description検証
        privacy_keys = {
            "NSCameraUsageDescription": "カメラ使用時",
            "NSMicrophoneUsageDescription": "マイク使用時",
            "NSLocationWhenInUseUsageDescription": "位置情報使用時",
            "NSLocationAlwaysAndWhenInUseUsageDescription": "常時位置情報使用時",
            "NSPhotoLibraryUsageDescription": "写真ライブラリアクセス時",
            "NSContactsUsageDescription": "連絡先アクセス時",
            "NSCalendarsUsageDescription": "カレンダーアクセス時",
        }
        
        # 実際にこれらのAPIが使用されているかチェック（簡易版）
        # より詳細な実装では、コード解析結果との照合が必要
        
        for key, usage_context in privacy_keys.items():
            if key in plist_data:
                description = plist_data[key]
                if not description or len(description.strip()) < 10:
                    self.issues.append(CodeIssue(
                        file_path=str(file_path),
                        line_number=0,
                        issue_type="insufficient_privacy_description",
                        severity="warning",
                        message=f"プライバシー説明が不十分: {key}",
                        guideline_ref="5.1.1",
                        suggestion=f"{usage_context}の明確な説明が必要です"
                    ))

    def _check_entitlements(self):
        """Entitlementsファイルの検証"""
        entitlements_files = list(self.project_path.glob("**/*.entitlements"))
        
        for entitlements_file in entitlements_files:
            try:
                import plistlib
                with open(entitlements_file, 'rb') as f:
                    entitlements_data = plistlib.load(f)
                
                self._validate_entitlements(entitlements_data, entitlements_file)
                
            except Exception as e:
                self.issues.append(CodeIssue(
                    file_path=str(entitlements_file),
                    line_number=0,
                    issue_type="entitlements_parse_error",
                    severity="error",
                    message=f"Entitlementsの解析エラー: {str(e)}",
                    guideline_ref="2.5"
                ))

    def _validate_entitlements(self, entitlements_data: dict, file_path: Path):
        """Entitlementsの内容検証"""
        # 危険なEntitlementsのチェック
        dangerous_entitlements = [
            "com.apple.private.security.no-container",
            "com.apple.private.skip-library-validation",
            "com.apple.rootless.install.heritable",
        ]
        
        for entitlement in dangerous_entitlements:
            if entitlement in entitlements_data and entitlements_data[entitlement]:
                self.issues.append(CodeIssue(
                    file_path=str(file_path),
                    line_number=0,
                    issue_type="dangerous_entitlement",
                    severity="error",
                    message=f"危険なEntitlement使用: {entitlement}",
                    guideline_ref="2.5.1",
                    suggestion="プライベートEntitlementの使用はApp Storeでリジェクトされます"
                ))

    def _check_xcode_settings(self):
        """Xcodeプロジェクト設定の検証"""
        project_files = list(self.project_path.glob("**/*.xcodeproj/project.pbxproj"))
        
        for project_file in project_files:
            try:
                with open(project_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # デバッグ設定が本番に残っていないかチェック
                if 'DEBUG = 1' in content and 'RELEASE' in content:
                    # より詳細な解析が必要
                    pass
                
                # HTTPSの使用確認
                if 'NSAppTransportSecurity' in content:
                    self._check_ats_settings(content, project_file)
                
            except Exception as e:
                self.issues.append(CodeIssue(
                    file_path=str(project_file),
                    line_number=0,
                    issue_type="xcode_settings_error",
                    severity="warning",
                    message=f"Xcode設定の解析エラー: {str(e)}",
                    guideline_ref="2.5"
                ))

    def _check_ats_settings(self, content: str, file_path: Path):
        """App Transport Security設定の確認"""
        if 'NSAllowsArbitraryLoads' in content:
            self.issues.append(CodeIssue(
                file_path=str(file_path),
                line_number=0,
                issue_type="ats_disabled",
                severity="warning",
                message="App Transport Securityが無効化されています",
                guideline_ref="5.1.3",
                suggestion="本番環境ではHTTPS通信を使用し、ATSを有効にしてください"
            ))

    def _check_dependencies(self):
        """依存関係の検証"""
        # CocoaPods
        podfile_path = self.project_path / "Podfile"
        if podfile_path.exists():
            self._check_cocoapods_dependencies(podfile_path)
        
        # Swift Package Manager
        package_swift_path = self.project_path / "Package.swift"
        if package_swift_path.exists():
            self._check_spm_dependencies(package_swift_path)
        
        # Carthage
        cartfile_path = self.project_path / "Cartfile"
        if cartfile_path.exists():
            self._check_carthage_dependencies(cartfile_path)

    def _check_cocoapods_dependencies(self, podfile_path: Path):
        """CocoaPods依存関係のチェック"""
        try:
            with open(podfile_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 古いバージョンやセキュリティリスクのあるライブラリ検出
            risky_pods = [
                ("AFNetworking", "2.0", "古いバージョンのAFNetworkingにはセキュリティリスクがあります"),
                ("Alamofire", "4.0", "古いバージョンのAlamofireを使用しています"),
            ]
            
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                for pod_name, risky_version, message in risky_pods:
                    if pod_name in line and risky_version in line:
                        self.issues.append(CodeIssue(
                            file_path=str(podfile_path),
                            line_number=line_num,
                            issue_type="risky_dependency",
                            severity="warning",
                            message=f"リスクのある依存関係: {line.strip()}",
                            guideline_ref="2.5.3",
                            suggestion=message
                        ))
                        
        except Exception as e:
            self.issues.append(CodeIssue(
                file_path=str(podfile_path),
                line_number=0,
                issue_type="dependency_check_error",
                severity="warning",
                message=f"依存関係チェックエラー: {str(e)}",
                guideline_ref="N/A"
            ))

    def _check_spm_dependencies(self, package_swift_path: Path):
        """Swift Package Manager依存関係のチェック"""
        # Swift Package Managerの依存関係チェック実装
        pass

    def _check_carthage_dependencies(self, cartfile_path: Path):
        """Carthage依存関係のチェック"""
        # Carthageの依存関係チェック実装
        pass

    def _check_resources(self):
        """リソースファイルの検証"""
        # アイコンファイルのチェック
        self._check_app_icons()
        
        # Launch Storyboardのチェック
        self._check_launch_storyboard()
        
        # 不要なファイルのチェック
        self._check_unnecessary_files()

    def _check_app_icons(self):
        """アプリアイコンのチェック"""
        # App Iconディレクトリの検索
        icon_dirs = list(self.project_path.glob("**/AppIcon.appiconset"))
        
        if not icon_dirs:
            self.issues.append(CodeIssue(
                file_path="AppIcon.appiconset",
                line_number=0,
                issue_type="missing_app_icon",
                severity="error",
                message="アプリアイコンが見つかりません",
                guideline_ref="2.1",
                suggestion="AppIcon.appiconsetディレクトリと必要なサイズのアイコンを追加してください"
            ))
        else:
            for icon_dir in icon_dirs:
                self._validate_app_icon_set(icon_dir)

    def _validate_app_icon_set(self, icon_dir: Path):
        """アプリアイコンセットの検証"""
        contents_json = icon_dir / "Contents.json"
        if not contents_json.exists():
            self.issues.append(CodeIssue(
                file_path=str(icon_dir),
                line_number=0,
                issue_type="missing_contents_json",
                severity="error",
                message="Contents.jsonが見つかりません",
                guideline_ref="2.1",
                suggestion="Contents.jsonファイルが必要です"
            ))
            return
        
        try:
            with open(contents_json, 'r', encoding='utf-8') as f:
                contents = json.load(f)
            
            # 必要なサイズの確認
            required_sizes = ["60x60", "76x76", "83.5x83.5", "1024x1024"]  # iOS用基本サイズ
            
            images = contents.get("images", [])
            available_sizes = set()
            
            for image in images:
                size = image.get("size", "")
                if size:
                    available_sizes.add(size)
                
                # ファイル名の確認
                filename = image.get("filename", "")
                if filename:
                    icon_file_path = icon_dir / filename
                    if not icon_file_path.exists():
                        self.issues.append(CodeIssue(
                            file_path=str(contents_json),
                            line_number=0,
                            issue_type="missing_icon_file",
                            severity="error",
                            message=f"アイコンファイルが見つかりません: {filename}",
                            guideline_ref="2.1"
                        ))
            
            for required_size in required_sizes:
                if required_size not in available_sizes:
                    self.issues.append(CodeIssue(
                        file_path=str(contents_json),
                        line_number=0,
                        issue_type="missing_icon_size",
                        severity="warning",
                        message=f"必要なアイコンサイズが不足: {required_size}",
                        guideline_ref="2.1",
                        suggestion=f"{required_size}サイズのアイコンを追加してください"
                    ))
                        
        except Exception as e:
            self.issues.append(CodeIssue(
                file_path=str(contents_json),
                line_number=0,
                issue_type="icon_validation_error",
                severity="error",
                message=f"アイコン検証エラー: {str(e)}",
                guideline_ref="2.1"
            ))

    def _check_launch_storyboard(self):
        """Launch Storyboardのチェック"""
        launch_storyboards = list(self.project_path.glob("**/LaunchScreen.storyboard"))
        
        if not launch_storyboards:
            self.issues.append(CodeIssue(
                file_path="LaunchScreen.storyboard",
                line_number=0,
                issue_type="missing_launch_storyboard",
                severity="warning",
                message="Launch Storyboardが見つかりません",
                guideline_ref="2.1",
                suggestion="Launch Storyboardを追加することを推奨します"
            ))

    def _check_unnecessary_files(self):
        """不要なファイルのチェック"""
        unnecessary_patterns = [
            "*.DS_Store",
            "Thumbs.db",
            "*.tmp",
            "*.log",
            "*.bak",
            "*.orig",
        ]
        
        for pattern in unnecessary_patterns:
            unnecessary_files = list(self.project_path.glob(f"**/{pattern}"))
            for file_path in unnecessary_files:
                self.issues.append(CodeIssue(
                    file_path=str(file_path),
                    line_number=0,
                    issue_type="unnecessary_file",
                    severity="info",
                    message=f"不要なファイル: {file_path.name}",
                    guideline_ref="2.1",
                    suggestion="不要なファイルは削除してください"
                ))

    def _generate_report(self) -> Dict[str, Any]:
        """品質チェック結果のレポート生成"""
        # 問題の分類
        errors = [issue for issue in self.issues if issue.severity == "error"]
        warnings = [issue for issue in self.issues if issue.severity == "warning"]
        infos = [issue for issue in self.issues if issue.severity == "info"]
        
        # 統計情報
        stats = {
            "total_issues": len(self.issues),
            "errors": len(errors),
            "warnings": len(warnings),
            "infos": len(infos),
            "files_checked": len(self._find_swift_files()),
        }
        
        # スコア計算（100点満点）
        score = max(0, 100 - (len(errors) * 10) - (len(warnings) * 3) - (len(infos) * 1))
        
        # ガイドライン別の問題集計
        guideline_breakdown = {}
        for issue in self.issues:
            guideline = issue.guideline_ref
            if guideline not in guideline_breakdown:
                guideline_breakdown[guideline] = {"errors": 0, "warnings": 0, "infos": 0}
            guideline_breakdown[guideline][issue.severity + "s"] += 1
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "project_path": str(self.project_path),
            "quality_score": score,
            "statistics": stats,
            "issues": [
                {
                    "file_path": issue.file_path,
                    "line_number": issue.line_number,
                    "issue_type": issue.issue_type,
                    "severity": issue.severity,
                    "message": issue.message,
                    "guideline_ref": issue.guideline_ref,
                    "suggestion": issue.suggestion
                }
                for issue in self.issues
            ],
            "guideline_breakdown": guideline_breakdown,
            "recommendations": self._generate_recommendations(errors, warnings)
        }
        
        return report

    def _generate_recommendations(self, errors: List[CodeIssue], warnings: List[CodeIssue]) -> List[str]:
        """改善推奨事項の生成"""
        recommendations = []
        
        if errors:
            recommendations.append("🚨 エラー項目の修正が最優先です。これらはApp Storeリジェクトの原因となります。")
        
        if warnings:
            recommendations.append("⚠️ 警告項目の確認と修正を推奨します。")
        
        # よくある問題の対策提案
        private_api_errors = [e for e in errors if e.issue_type == "private_api_usage"]
        if private_api_errors:
            recommendations.append("📱 プライベートAPIの使用を削除し、公開APIに置き換えてください。")
        
        privacy_warnings = [w for w in warnings if w.issue_type == "privacy_violation"]
        if privacy_warnings:
            recommendations.append("🔒 プライバシー関連APIの使用理由をInfo.plistに記載してください。")
        
        security_errors = [e for e in errors if e.issue_type == "security_issue"]
        if security_errors:
            recommendations.append("🛡️ セキュリティ問題を修正してください。機密情報の適切な管理が必要です。")
        
        return recommendations

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="App Store Guidelines準拠コード品質チェック")
    parser.add_argument("project_path", help="プロジェクトパス")
    parser.add_argument("-o", "--output", help="出力ファイルパス", default="quality_report.json")
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細出力")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.project_path):
        print(f"エラー: プロジェクトパス '{args.project_path}' が見つかりません")
        sys.exit(1)
    
    # 品質チェック実行
    checker = AppStoreCodeQualityChecker(args.project_path)
    report = checker.run_quality_check()
    
    # 結果出力
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # コンソール出力
    print(f"\n{'='*60}")
    print("📊 App Store Guidelines準拠 品質チェック結果")
    print(f"{'='*60}")
    print(f"品質スコア: {report['quality_score']}/100")
    print(f"チェック対象ファイル数: {report['statistics']['files_checked']}")
    print(f"発見された問題数: {report['statistics']['total_issues']}")
    print(f"  - エラー: {report['statistics']['errors']}")
    print(f"  - 警告: {report['statistics']['warnings']}")
    print(f"  - 情報: {report['statistics']['infos']}")
    
    if args.verbose:
        print("\n📋 問題詳細:")
        for issue in report['issues']:
            severity_icon = {"error": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(issue['severity'], "")
            print(f"{severity_icon} {issue['file_path']}:{issue['line_number']}")
            print(f"   {issue['message']}")
            print(f"   Guidelines: {issue['guideline_ref']}")
            if issue['suggestion']:
                print(f"   💡 {issue['suggestion']}")
            print()
    
    if report['recommendations']:
        print("\n💡 推奨事項:")
        for rec in report['recommendations']:
            print(f"   {rec}")
    
    print(f"\n詳細レポート: {args.output}")
    
    # 終了コード設定
    if report['statistics']['errors'] > 0:
        sys.exit(1)
    elif report['statistics']['warnings'] > 0:
        sys.exit(2)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()