#!/usr/bin/env python3
"""
ダッシュボードデバッグスクリプト
Playwrightを使用してChromeのDevTools情報を自動取得

使用方法:
    python scripts/dashboard_debug.py                    # 基本デバッグ
    python scripts/dashboard_debug.py --full            # 全機能（パフォーマンス・メモリ含む）
    python scripts/dashboard_debug.py --lighthouse      # Lighthouse監査
    python scripts/dashboard_debug.py --watch           # 継続監視モード
    python scripts/dashboard_debug.py --url <URL>       # カスタムURL
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright


class DashboardDebugger:
    """ダッシュボードデバッグクラス"""

    def __init__(self, url: str = "http://localhost:8082/episode_database_dashboard_v6.html"):
        self.url = url
        self.output_dir = Path("logs/dashboard_debug")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # ログ収集用
        self.console_logs = []
        self.network_requests = []
        self.network_responses = []
        self.errors = []
        self.performance_entries = []

    async def capture_console(self, headless: bool = False, wait_time: int = 5000):
        """コンソールログ・ネットワーク・エラーをキャプチャ"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context()
            page = await context.new_page()

            # イベントリスナー設定
            page.on(
                "console",
                lambda msg: self.console_logs.append(
                    {
                        "type": msg.type,
                        "text": msg.text,
                        "location": str(msg.location) if msg.location else None,
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
            )

            page.on(
                "pageerror",
                lambda err: self.errors.append({"message": str(err), "timestamp": datetime.now().isoformat()}),
            )

            page.on(
                "request",
                lambda req: self.network_requests.append(
                    {
                        "url": req.url,
                        "method": req.method,
                        "resource_type": req.resource_type,
                        "headers": dict(req.headers) if req.headers else {},
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
            )

            page.on(
                "response",
                lambda res: self.network_responses.append(
                    {
                        "url": res.url,
                        "status": res.status,
                        "status_text": res.status_text,
                        "headers": dict(res.headers) if res.headers else {},
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
            )

            print(f"🌐 アクセス中: {self.url}")
            await page.goto(self.url, wait_until="networkidle")

            print(f"⏳ {wait_time/1000}秒待機中...")
            await page.wait_for_timeout(wait_time)

            # JavaScript状態取得
            js_state = await self._get_js_state(page)

            # DOM状態取得
            dom_state = await self._get_dom_state(page)

            # スクリーンショット
            screenshot_path = self.output_dir / f"screenshot_{self.timestamp}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"📸 スクリーンショット: {screenshot_path}")

            await browser.close()

        return {"js_state": js_state, "dom_state": dom_state, "screenshot": str(screenshot_path)}

    async def capture_performance(self):
        """パフォーマンスメトリクスを取得"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # CDP（Chrome DevTools Protocol）セッション開始
            client = await context.new_cdp_session(page)
            await client.send("Performance.enable")

            await page.goto(self.url, wait_until="networkidle")
            await page.wait_for_timeout(3000)

            # パフォーマンスメトリクス取得
            metrics = await client.send("Performance.getMetrics")

            # Web Vitals取得
            web_vitals = await page.evaluate("""() => {
                const perf = window.performance;
                const timing = perf.timing;
                const entries = perf.getEntriesByType('navigation')[0] || {};

                return {
                    // Core Web Vitals
                    TTFB: entries.responseStart - entries.requestStart,
                    FCP: perf.getEntriesByName('first-contentful-paint')[0]?.startTime || null,
                    LCP: null,  // 別途計測が必要
                    CLS: null,  // 別途計測が必要

                    // その他のメトリクス
                    domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                    loadComplete: timing.loadEventEnd - timing.navigationStart,
                    domInteractive: timing.domInteractive - timing.navigationStart,

                    // リソース統計
                    resourceCount: perf.getEntriesByType('resource').length,
                    totalTransferSize: perf.getEntriesByType('resource')
                        .reduce((sum, r) => sum + (r.transferSize || 0), 0)
                };
            }""")

            # リソースタイミング取得
            resource_timing = await page.evaluate("""() => {
                return performance.getEntriesByType('resource').map(r => ({
                    name: r.name,
                    type: r.initiatorType,
                    duration: r.duration,
                    transferSize: r.transferSize,
                    startTime: r.startTime
                })).sort((a, b) => b.duration - a.duration).slice(0, 20);
            }""")

            await browser.close()

        return {"metrics": metrics, "web_vitals": web_vitals, "slow_resources": resource_timing}

    async def capture_memory(self):
        """メモリ使用状況を取得"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            client = await context.new_cdp_session(page)

            await page.goto(self.url, wait_until="networkidle")
            await page.wait_for_timeout(3000)

            # ヒープスナップショット情報
            await client.send("HeapProfiler.enable")

            # JS ヒープ使用量
            js_heap = await page.evaluate("""() => {
                if (performance.memory) {
                    return {
                        usedJSHeapSize: performance.memory.usedJSHeapSize,
                        totalJSHeapSize: performance.memory.totalJSHeapSize,
                        jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
                    };
                }
                return null;
            }""")

            # DOM統計
            dom_stats = await page.evaluate("""() => {
                return {
                    nodeCount: document.getElementsByTagName('*').length,
                    scriptCount: document.scripts.length,
                    styleSheetCount: document.styleSheets.length,
                    imageCount: document.images.length
                };
            }""")

            await browser.close()

        return {"js_heap": js_heap, "dom_stats": dom_stats}

    async def run_lighthouse(self):
        """Lighthouse監査を実行（簡易版）"""
        print("🔍 Lighthouse監査を実行中...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto(self.url, wait_until="networkidle")
            await page.wait_for_timeout(5000)

            # アクセシビリティチェック
            accessibility = await page.evaluate("""() => {
                const issues = [];

                // 画像のalt属性チェック
                document.querySelectorAll('img').forEach(img => {
                    if (!img.alt) issues.push({type: 'accessibility', message: `画像にalt属性がありません: ${img.src.substring(0, 50)}`});
                });

                // フォームラベルチェック
                document.querySelectorAll('input, select, textarea').forEach(el => {
                    if (!el.labels?.length && !el.getAttribute('aria-label')) {
                        issues.push({type: 'accessibility', message: `フォーム要素にラベルがありません: ${el.id || el.name || el.type}`});
                    }
                });

                // コントラスト（簡易）
                // ボタンの存在確認
                const buttons = document.querySelectorAll('button, [role="button"]');

                return {
                    issues: issues,
                    stats: {
                        images: document.images.length,
                        links: document.links.length,
                        buttons: buttons.length,
                        forms: document.forms.length
                    }
                };
            }""")

            # SEOチェック
            seo = await page.evaluate("""() => {
                return {
                    title: document.title,
                    hasMetaDescription: !!document.querySelector('meta[name="description"]'),
                    hasViewport: !!document.querySelector('meta[name="viewport"]'),
                    h1Count: document.querySelectorAll('h1').length,
                    hasCanonical: !!document.querySelector('link[rel="canonical"]')
                };
            }""")

            # ベストプラクティス
            best_practices = await page.evaluate("""() => {
                const issues = [];

                // HTTPS確認
                if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
                    issues.push('HTTPSを使用していません');
                }

                // コンソールエラー確認（すでにキャプチャ済み）

                return {
                    protocol: location.protocol,
                    issues: issues
                };
            }""")

            await browser.close()

        return {"accessibility": accessibility, "seo": seo, "best_practices": best_practices}

    async def watch_mode(self, interval: int = 30):
        """継続監視モード"""
        print(f"👁️ 監視モード開始（{interval}秒間隔）")
        print("   Ctrl+C で終了")

        iteration = 0
        while True:
            iteration += 1
            print(f"\n--- 監視 #{iteration} ({datetime.now().strftime('%H:%M:%S')}) ---")

            self.console_logs = []
            self.errors = []
            self.network_responses = []

            await self.capture_console(headless=True, wait_time=2000)

            # サマリー表示
            error_count = len(self.errors)
            failed_requests = len([r for r in self.network_responses if r["status"] >= 400])

            status = "✅ 正常" if error_count == 0 and failed_requests == 0 else "⚠️ 問題あり"
            print(f"   {status} | エラー: {error_count} | 失敗リクエスト: {failed_requests}")

            if error_count > 0:
                for err in self.errors[:3]:
                    print(f"   ❌ {err['message'][:80]}")

            await asyncio.sleep(interval)

    async def _get_js_state(self, page):
        """JavaScript変数の状態を取得"""
        return await page.evaluate("""() => {
            const result = {
                allEpisodesCount: typeof allEpisodes !== 'undefined' ? allEpisodes.length : 'undefined',
                filteredEpisodesCount: typeof filteredEpisodes !== 'undefined' ? filteredEpisodes.length : 'undefined',
                currentPage: typeof currentPage !== 'undefined' ? currentPage : 'undefined',
                itemsPerPage: typeof itemsPerPage !== 'undefined' ? itemsPerPage : 'undefined',
            };

            if (typeof allEpisodes !== 'undefined' && allEpisodes.length > 0) {
                result.firstEpisode = {
                    episode_id: allEpisodes[0].episode_id,
                    person_id: allEpisodes[0].person_id,
                    person_name: allEpisodes[0].person_name,
                    age: allEpisodes[0].age,
                    slot: allEpisodes[0].slot,
                    fame_score: allEpisodes[0].fame_score,
                    episode_fame_score: allEpisodes[0].episode_fame_score,
                    composite_score: allEpisodes[0].composite_score
                };
            }

            return result;
        }""")

    async def _get_dom_state(self, page):
        """DOM要素の状態を取得"""
        return await page.evaluate("""() => {
            const tbody = document.getElementById('episode-tbody');
            const resultCount = document.getElementById('result-count');

            return {
                tableRowCount: tbody ? tbody.querySelectorAll('tr').length : 0,
                resultCountText: resultCount ? resultCount.textContent : null,
                tabsCount: document.querySelectorAll('.tab-button').length,
                activeTab: document.querySelector('.tab-button.active')?.textContent || null
            };
        }""")

    def generate_report(self, data: dict) -> str:
        """デバッグレポートを生成"""
        report_path = self.output_dir / f"debug_report_{self.timestamp}.json"

        full_report = {
            "timestamp": self.timestamp,
            "url": self.url,
            "console_logs": self.console_logs,
            "errors": self.errors,
            "network_requests": self.network_requests,
            "network_responses": self.network_responses,
            **data,
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(full_report, f, ensure_ascii=False, indent=2)

        return str(report_path)

    def print_summary(self):
        """サマリーを表示"""
        print("\n" + "=" * 60)
        print("📊 デバッグサマリー")
        print("=" * 60)

        # エラー
        print(f"\n🔴 エラー数: {len(self.errors)}")
        for err in self.errors[:5]:
            print(f"   - {err['message'][:100]}")

        # コンソールログ（重要なもの）
        important_logs = [
            log
            for log in self.console_logs
            if log["type"] in ["error", "warning"] or any(x in log["text"] for x in ["✅", "❌", "⚠️", "🎨", "📋"])
        ]
        print(f"\n📝 重要なログ数: {len(important_logs)}")
        for log in important_logs[:10]:
            print(f"   [{log['type']}] {log['text'][:80]}")

        # ネットワーク
        failed = [r for r in self.network_responses if r["status"] >= 400]
        print(f"\n🌐 ネットワーク: {len(self.network_requests)}リクエスト, {len(failed)}失敗")
        for res in failed[:5]:
            print(f"   [{res['status']}] {res['url'][:60]}")


async def main():
    parser = argparse.ArgumentParser(description="ダッシュボードデバッグツール")
    parser.add_argument(
        "--url", default="http://localhost:8082/episode_database_dashboard_v6.html", help="デバッグ対象のURL"
    )
    parser.add_argument("--full", action="store_true", help="全機能（パフォーマンス・メモリ含む）")
    parser.add_argument("--lighthouse", action="store_true", help="Lighthouse監査")
    parser.add_argument("--performance", action="store_true", help="パフォーマンス分析")
    parser.add_argument("--memory", action="store_true", help="メモリ分析")
    parser.add_argument("--watch", action="store_true", help="継続監視モード")
    parser.add_argument("--interval", type=int, default=30, help="監視間隔（秒）")
    parser.add_argument("--headless", action="store_true", help="ヘッドレスモード")
    args = parser.parse_args()

    debugger = DashboardDebugger(url=args.url)

    try:
        if args.watch:
            await debugger.watch_mode(interval=args.interval)
            return

        # 基本キャプチャ
        data = await debugger.capture_console(headless=args.headless)

        # オプション機能
        if args.full or args.performance:
            print("\n📈 パフォーマンス分析中...")
            data["performance"] = await debugger.capture_performance()
            print(f"   Web Vitals: {json.dumps(data['performance']['web_vitals'], indent=4)}")

        if args.full or args.memory:
            print("\n💾 メモリ分析中...")
            data["memory"] = await debugger.capture_memory()
            if data["memory"]["js_heap"]:
                heap = data["memory"]["js_heap"]
                print(
                    f"   JS Heap: {heap['usedJSHeapSize']/1024/1024:.1f}MB / {heap['totalJSHeapSize']/1024/1024:.1f}MB"
                )
            print(f"   DOM Stats: {data['memory']['dom_stats']}")

        if args.full or args.lighthouse:
            print("\n🔍 Lighthouse監査中...")
            data["lighthouse"] = await debugger.run_lighthouse()
            print(f"   SEO: {data['lighthouse']['seo']}")
            print(f"   アクセシビリティ問題: {len(data['lighthouse']['accessibility']['issues'])}件")

        # レポート生成
        report_path = debugger.generate_report(data)
        print(f"\n📄 レポート保存: {report_path}")

        # サマリー表示
        debugger.print_summary()

        # JS状態表示
        if data.get("js_state"):
            print("\n📋 JavaScript状態:")
            print(f"   allEpisodes: {data['js_state'].get('allEpisodesCount', 'N/A')}件")
            print(f"   filteredEpisodes: {data['js_state'].get('filteredEpisodesCount', 'N/A')}件")
            if data["js_state"].get("firstEpisode"):
                ep = data["js_state"]["firstEpisode"]
                print(f"   最初のエピソード: {ep.get('person_name')} (ID: {ep.get('episode_id')})")

    except KeyboardInterrupt:
        print("\n\n⏹️ 中断されました")
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
