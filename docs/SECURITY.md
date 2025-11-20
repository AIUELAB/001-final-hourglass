# セキュリティガイドライン

このドキュメントでは、プロジェクトのセキュリティベストプラクティスと脆弱性報告手順を説明します。

## 📋 目次

1. [セキュリティポリシー](#セキュリティポリシー)
2. [認証とアクセス管理](#認証とアクセス管理)
3. [シークレット管理](#シークレット管理)
4. [脆弱性報告](#脆弱性報告)
5. [セキュリティチェックリスト](#セキュリティチェックリスト)

---

## セキュリティポリシー

### サポートされるバージョン

| バージョン | サポート状況 |
|----------|------------|
| main     | ✅ フルサポート |
| develop  | ⚠️ テスト段階 |
| その他   | ❌ サポート外 |

### セキュリティアップデート

- **Critical**: 24時間以内に対応
- **High**: 7日以内に対応
- **Medium**: 30日以内に対応
- **Low**: 次回リリースで対応

---

## 認証とアクセス管理

### GitHub認証

#### 🔐 SSH鍵ベース認証（推奨）

**利点**:
- トークン漏洩リスクがない
- 公開鍵暗号方式で高セキュリティ
- パスフレーズで二重保護可能

**設定方法**:
```bash
# ed25519形式で鍵生成（RSAより安全）
ssh-keygen -t ed25519 -C "your_email@example.com"

# パスフレーズ設定を強く推奨
# 推奨: 16文字以上、英数字記号混在
```

**セキュリティチェック**:
```bash
# 鍵のパーミッション確認
ls -la ~/.ssh/id_ed25519
# 期待値: -rw------- (600)

# グループ・他者からの読み取り不可
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
```

#### 🔑 Personal Access Token（PAT）

**トークン生成のベストプラクティス**:

1. **Fine-grained tokensを使用**（Classic tokensは避ける）
2. **最小権限の原則**:
   ```
   Repository permissions:
   ✅ Contents: Read and write  # コード操作に必要
   ✅ Issues: Read and write    # Issue管理に必要
   ✅ Pull requests: Read and write  # PR操作に必要
   ❌ Administration: 不要
   ❌ Secrets: 不要
   ❌ Workflows: 必要な場合のみ
   ```

3. **有効期限設定**:
   - 推奨: **90日**
   - 最長: 1年（セキュリティ要件次第）
   - 無期限は**絶対禁止**

4. **Repository accessの制限**:
   - "Only select repositories"を選択
   - 必要なリポジトリのみを指定
   - "All repositories"は避ける

**トークンのローテーション**:
```bash
# 期限切れ30日前に新トークンを生成
# 1. 新トークン生成
# 2. Keychainに保存
security add-generic-password \
  -a "$USER" \
  -s "github-personal-access-token" \
  -w "NEW_TOKEN" \
  -U  # -U: 既存エントリを更新

# 3. 動作確認
gh auth status

# 4. 旧トークンを削除（GitHubウェブ上で）
```

---

## シークレット管理

### ✅ 推奨: macOS Keychain

**利点**:
- macOS標準の暗号化ストレージ
- FileVault有効時はディスク全体が暗号化
- アクセス制御リスト（ACL）対応

**保存方法**:
```bash
# トークンを保存
security add-generic-password \
  -a "$USER" \
  -s "github-personal-access-token" \
  -w "ghp_YOUR_TOKEN_HERE" \
  -T ""  # すべてのアプリケーションに許可

# 読み取り
security find-generic-password \
  -a "$USER" \
  -s "github-personal-access-token" \
  -w
```

**セキュリティ設定**:
```bash
# 特定アプリのみアクセス許可（推奨）
security add-generic-password \
  -a "$USER" \
  -s "github-personal-access-token" \
  -w "TOKEN" \
  -T /Applications/Claude.app \
  -T /usr/bin/security
```

### ❌ 禁止事項

#### 1. 平文ファイルへの保存

```bash
# ❌ 絶対禁止
echo "ghp_TOKEN" > ~/.github-token.txt

# ❌ 環境変数ファイルも危険
echo "GITHUB_TOKEN=ghp_TOKEN" >> .env

# ❌ コミット履歴に残る
git add .env
git commit -m "Add token"  # 危険！
```

**リスク**:
- ファイルシステムに平文で保存
- バックアップに含まれる可能性
- 誤ってコミットする危険性

#### 2. ハードコーディング

```python
# ❌ 絶対禁止
GITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# ✅ 正しい方法
import os
GITHUB_TOKEN = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
```

#### 3. Git履歴への保存

```bash
# ❌ 絶対禁止
git remote add origin https://ghp_TOKEN@github.com/user/repo.git

# ✅ 正しい方法
git remote add origin git@github.com:user/repo.git
```

### 🚨 トークン漏洩時の対応

**即座に実行すべきアクション**:

1. **トークンの無効化**（1分以内）:
   ```
   https://github.com/settings/tokens
   → 該当トークンの"Delete"をクリック
   ```

2. **Git履歴からの削除**:
   ```bash
   # BFG Repo-Cleanerを使用
   brew install bfg

   # トークンを含むファイルを削除
   bfg --delete-files token.txt

   # Git履歴を書き換え
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive

   # 強制プッシュ（慎重に）
   git push origin --force --all
   ```

3. **新トークンの生成**（Step 2参照）

4. **影響範囲の調査**:
   - GitHub Audit Logで不正アクセスを確認
   - リポジトリの変更履歴を確認
   - 必要に応じてリポジトリをprivateに変更

---

## 脆弱性報告

### 報告方法

**重要**: 脆弱性は公開Issueで報告**しないでください**

#### 推奨報告手段（優先順）

1. **GitHub Security Advisories**:
   ```
   https://github.com/AIUELAB/001-final-hourglass/security/advisories/new
   ```

2. **メール**:
   ```
   security@example.com（プロジェクト管理者のメール）
   ```

3. **暗号化通信**:
   - PGP公開鍵: [公開鍵URL]
   - Signal: [Signal ID]

#### 報告に含めるべき情報

```markdown
## 脆弱性レポート

### 概要
- 脆弱性の種類: [例: XSS, SQLi, RCE]
- 影響範囲: [例: 全ユーザー、管理者のみ]
- 深刻度: [Critical/High/Medium/Low]

### 再現手順
1. ステップ1
2. ステップ2
3. ...

### 影響
- 攻撃者が実行可能なアクション
- データ漏洩の可能性
- システムへの影響

### 推奨される対策
- 修正案（あれば）
- 一時的な緩和策

### 環境情報
- OS: macOS 14.0
- Python: 3.11.5
- その他依存関係のバージョン
```

### 報告後の流れ

| タイミング | アクション |
|----------|-----------|
| 24時間以内 | 受領確認の返信 |
| 7日以内 | 初期評価と優先度の決定 |
| 30日以内 | 修正版のリリース（Critical/Highの場合） |
| 90日以内 | 修正版のリリース（Medium/Lowの場合） |

---

## セキュリティチェックリスト

### コミット前のチェック

```bash
# ✅ シークレットのスキャン
git diff --cached | grep -E "(token|password|api_key|secret)"

# ✅ Gitleaksでの自動スキャン（推奨）
brew install gitleaks
gitleaks detect --source . -v

# ✅ 環境変数の確認
grep -r "GITHUB_TOKEN" .
# .gitignoreに .env が含まれているか確認
```

### 定期的なセキュリティ監査

#### 月次チェック

```bash
# 依存関係の脆弱性スキャン
pip-audit

# npm脆弱性スキャン（Node.js依存がある場合）
npm audit

# Banditでのコードスキャン
bandit -r src/
```

#### 四半期チェック

- [ ] GitHub Personal Access Tokenのローテーション
- [ ] SSH鍵の棚卸し（不要な鍵の削除）
- [ ] アクセス権限のレビュー
- [ ] 監査ログの確認

### GitHub設定のベストプラクティス

#### リポジトリ設定

```bash
# ブランチ保護の確認
gh api repos/AIUELAB/001-final-hourglass/branches/main/protection | jq

# 期待される設定:
# - required_status_checks: CI/CDパイプライン
# - enforce_admins: true
# - required_pull_request_reviews.required_approving_review_count: 1
# - allow_force_pushes: false
# - allow_deletions: false
```

#### Organization設定（該当する場合）

- [ ] 2FA強制有効化
- [ ] 外部コラボレーターの制限
- [ ] OAuth Appの定期レビュー
- [ ] Audit Logの監視

---

## 環境変数の管理

### ✅ 推奨方法

#### 開発環境

```bash
# .env.example を提供（値は空）
cat > .env.example << 'EOF'
GITHUB_PERSONAL_ACCESS_TOKEN=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
EOF

# .gitignoreに追加
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore
```

#### 本番環境

- **環境変数**: システムレベルで設定
- **Secret Manager**: AWS Secrets Manager, GCP Secret Manager等
- **Vault**: HashiCorp Vault等

### ❌ 避けるべき方法

```bash
# ❌ シェル履歴に残る
export GITHUB_TOKEN="ghp_TOKEN"

# ❌ プロセスリストに表示される
python script.py --token ghp_TOKEN

# ✅ 正しい方法
export GITHUB_TOKEN=$(security find-generic-password -s "github-personal-access-token" -w)
python script.py  # 環境変数から読み取る
```

---

## CI/CD パイプラインのセキュリティ

### GitHub Actions

#### Secretsの管理

```yaml
# .github/workflows/ci.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      # ✅ GitHub Secretsを使用
      - name: Run tests
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}  # 自動提供
          API_KEY: ${{ secrets.API_KEY }}  # 手動設定
        run: pytest tests/
```

#### セキュリティベストプラクティス

```yaml
# ✅ 最小権限の原則
permissions:
  contents: read
  issues: write
  pull-requests: write

# ✅ バージョン固定（セキュリティアップデート対応）
- uses: actions/checkout@v4.1.0  # ハッシュ固定も可

# ❌ 避けるべき
- uses: actions/checkout@main  # 予期しない変更のリスク
```

---

## インシデント対応

### 侵害の兆候

以下の兆候を検出した場合、即座に対応:

- 未承認のコミット/プッシュ
- 不明なブランチの作成
- Secretsの変更
- 不審なAPI呼び出し

### 対応手順

1. **即座の隔離** (5分以内):
   ```bash
   # トークンの無効化
   # リポジトリをprivateに変更（一時的）
   ```

2. **影響範囲の特定** (30分以内):
   ```bash
   # GitHub Audit Logの確認
   gh api /repos/AIUELAB/001-final-hourglass/events

   # Git履歴の確認
   git log --all --oneline --graph
   ```

3. **修正と復旧** (24時間以内):
   - 不正な変更のrevert
   - セキュリティパッチの適用
   - 新しいシークレットの生成

4. **事後分析** (7日以内):
   - 侵害原因の特定
   - 再発防止策の策定
   - ドキュメントの更新

---

## 参考資料

### 外部リソース

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

### プロジェクト内ドキュメント

- [GITHUB_MCP_SETUP.md](./GITHUB_MCP_SETUP.md) - セットアップガイド
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - トラブルシューティング
- [CONTRIBUTING.md](../CONTRIBUTING.md) - 貢献ガイドライン

---

## 更新履歴

- **2025-11-20**: 初版作成
  - 認証とアクセス管理のガイドライン
  - シークレット管理のベストプラクティス
  - 脆弱性報告手順
  - インシデント対応プロセス

---

## 連絡先

セキュリティに関する質問や報告:
- **Email**: security@example.com
- **GitHub**: [@gunzitakashi](https://github.com/gunzitakashi)
