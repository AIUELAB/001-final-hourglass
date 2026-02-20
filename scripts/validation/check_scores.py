#!/usr/bin/env python3
"""7軸スコアの状態を詳細確認"""

import asyncio
from playwright.async_api import async_playwright


async def check_scores():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto("http://localhost:8082/episode_database_dashboard_v6.html", wait_until="networkidle")
        await page.wait_for_timeout(5000)

        # 7軸スコアの詳細を取得
        scores_data = await page.evaluate("""() => {
            if (typeof allEpisodes === 'undefined' || allEpisodes.length === 0) {
                return { error: 'allEpisodes is empty or undefined' };
            }

            // 最初の10件のスコアデータを取得
            const samples = allEpisodes.slice(0, 10).map((ep, i) => ({
                index: i,
                person_name: ep.person_name,
                composite_score: ep.composite_score,
                memorability_score: ep.memorability_score,
                empathy_score: ep.empathy_score,
                surprise_score: ep.surprise_score,
                generation_quality_score: ep.generation_quality_score,
                educational_value: ep.educational_value,
                story_quality: ep.story_quality,
                factual_density: ep.factual_density
            }));

            // スコアがnullのエピソード数をカウント
            const nullCounts = {
                composite_score: allEpisodes.filter(ep => ep.composite_score === null).length,
                memorability_score: allEpisodes.filter(ep => ep.memorability_score === null).length,
                empathy_score: allEpisodes.filter(ep => ep.empathy_score === null).length,
                surprise_score: allEpisodes.filter(ep => ep.surprise_score === null).length,
                generation_quality_score: allEpisodes.filter(ep => ep.generation_quality_score === null).length,
                educational_value: allEpisodes.filter(ep => ep.educational_value === null).length,
                story_quality: allEpisodes.filter(ep => ep.story_quality === null).length,
                factual_density: allEpisodes.filter(ep => ep.factual_density === null).length
            };

            return {
                total: allEpisodes.length,
                samples: samples,
                nullCounts: nullCounts
            };
        }""")

        await browser.close()

        print("=" * 70)
        print("📊 7軸スコア詳細確認")
        print("=" * 70)

        if "error" in scores_data:
            print(f"❌ エラー: {scores_data['error']}")
            return

        print(f"\n📈 総エピソード数: {scores_data['total']}")

        print("\n📋 最初の10件のスコア:")
        for sample in scores_data["samples"]:
            print(f"\n  [{sample['index'] + 1}] {sample['person_name']}")
            print(f"      総合: {sample['composite_score']}")
            print(
                f"      記憶: {sample['memorability_score']} | 共感: {sample['empathy_score']} | 意外: {sample['surprise_score']}"
            )
            print(
                f"      品質: {sample['generation_quality_score']} | 教育: {sample['educational_value']} | 物語: {sample['story_quality']} | 事実: {sample['factual_density']}"
            )

        print("\n📊 nullのスコア数:")
        for key, count in scores_data["nullCounts"].items():
            pct = (count / scores_data["total"]) * 100
            status = "✅" if count == 0 else "⚠️" if pct < 50 else "❌"
            print(f"  {status} {key}: {count}/{scores_data['total']} ({pct:.1f}%)")


if __name__ == "__main__":
    asyncio.run(check_scores())
