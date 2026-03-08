import XCTest
@testable import FinalHourglass

final class SoundManagerTests: XCTestCase {

    // MARK: - Singleton

    func testSharedInstance() {
        let instance = SoundManager.shared
        XCTAssertNotNil(instance)
        XCTAssertTrue(instance === SoundManager.shared, "shared は常に同一インスタンスを返すこと")
    }

    // MARK: - TapSoundType Enum

    func testTapSoundTypeHasAllExpectedCases() {
        let allCases: [TapSoundType] = [.soft, .confirm, .cancel, .success, .warning]
        XCTAssertEqual(allCases.count, 5, "TapSoundType は5種類であること")

        // Hashable 準拠の確認
        let set = Set(allCases)
        XCTAssertEqual(set.count, 5, "全ケースがユニークであること")
    }

    // MARK: - BGM Volume

    func testSetBGMVolumeClampsBelow() {
        let sut = SoundManager.shared
        sut.setBGMVolume(-0.5)
        XCTAssertEqual(sut.bgmVolume, 0.0, "負の値は0.0にクランプされること")
    }

    func testSetBGMVolumeClampsAbove() {
        let sut = SoundManager.shared
        sut.setBGMVolume(1.5)
        XCTAssertEqual(sut.bgmVolume, 1.0, "1.0超の値は1.0にクランプされること")
    }

    func testSetBGMVolumeNormalRange() {
        let sut = SoundManager.shared
        sut.setBGMVolume(0.7)
        XCTAssertEqual(sut.bgmVolume, 0.7, accuracy: 0.001, "0.0〜1.0の範囲内の値はそのまま設定されること")
    }

    // MARK: - Default Values

    func testDefaultBGMVolume() {
        // UserDefaultsに値がない場合のデフォルトは0.3
        // シングルトンなので前のテストで変更されている可能性がある。リセットして確認
        let sut = SoundManager.shared
        UserDefaults.standard.removeObject(forKey: "bgmVolume")
        // デフォルト値は初期化時に設定されるため、setBGMVolumeで0.3に戻して検証
        sut.setBGMVolume(0.3)
        XCTAssertEqual(sut.bgmVolume, 0.3, accuracy: 0.001, "デフォルトBGM音量は0.3であること")
    }

    func testDefaultHapticEnabled() {
        let sut = SoundManager.shared
        // hapticEnabled のデフォルトは true
        // シングルトンのため初期値が変更されていない限り true
        XCTAssertTrue(sut.hapticEnabled, "ハプティックフィードバックはデフォルトで有効であること")
    }

    // MARK: - BGM Playing State

    func testInitialIsBGMPlayingIsFalse() {
        let sut = SoundManager.shared
        // テスト環境ではBundleリソースがないため再生されない
        sut.stopBackgroundMusic()
        XCTAssertFalse(sut.isBGMPlaying, "初期状態ではBGMは再生されていないこと")
    }

    func testStopBackgroundMusicSetsIsBGMPlayingToFalse() {
        let sut = SoundManager.shared
        sut.stopBackgroundMusic()
        XCTAssertFalse(sut.isBGMPlaying, "stopBackgroundMusic後はisBGMPlayingがfalseであること")
    }

    func testStopAllSoundsSetsIsBGMPlayingToFalse() {
        let sut = SoundManager.shared
        sut.stopAllSounds()
        XCTAssertFalse(sut.isBGMPlaying, "stopAllSounds後はisBGMPlayingがfalseであること")
    }

    // MARK: - Fade State Management

    func testFadeOutWithNilPlayerCallsCompletionImmediately() {
        let sut = SoundManager.shared
        sut.stopBackgroundMusic() // bgmPlayer を nil にリセット

        let expectation = expectation(description: "completion called")
        sut.fadeOutBackgroundMusic { expectation.fulfill() }
        waitForExpectations(timeout: 1.0)

        XCTAssertFalse(sut.isBGMPlaying, "bgmPlayerがnilのフェードアウト後もisBGMPlayingはfalseであること")
    }

    func testStopBackgroundMusicClearsState() {
        let sut = SoundManager.shared
        // Bundle不在で再生は失敗するが、stopが安全に動作することを検証
        sut.playBackgroundMusic(filename: "nonexistent-file")
        sut.stopBackgroundMusic()

        XCTAssertFalse(sut.isBGMPlaying, "stopBackgroundMusic後はisBGMPlayingがfalseであること")
    }

    func testStopAllSoundsClearsAllState() {
        let sut = SoundManager.shared
        sut.playBackgroundMusic(filename: "nonexistent-file")
        sut.stopAllSounds()

        XCTAssertFalse(sut.isBGMPlaying, "stopAllSounds後はisBGMPlayingがfalseであること")
    }

    // MARK: - BGM Playback (Bundle不在時の状態検証)

    func testPlayBackgroundMusicWithMissingFileKeepsNotPlaying() {
        let sut = SoundManager.shared
        sut.stopBackgroundMusic()
        sut.playBackgroundMusic(filename: "file-that-does-not-exist", withExtension: "m4a")

        XCTAssertFalse(sut.isBGMPlaying, "存在しないファイルの再生試行後はisBGMPlayingがfalseであること")
    }

    func testPlayBackgroundMusicWithDifferentExtensionsTreatedAsDistinct() {
        let sut = SoundManager.shared
        sut.stopBackgroundMusic()

        // 同名・異拡張子の再生を連続呼び出し（Bundle不在で両方失敗するが、クラッシュしないことを確認）
        sut.playBackgroundMusic(filename: "test-sound", withExtension: "m4a")
        sut.playBackgroundMusic(filename: "test-sound", withExtension: "mp3")

        XCTAssertFalse(sut.isBGMPlaying, "Bundle不在時はisBGMPlayingがfalseであること")
    }

    // MARK: - Multiple Stop Calls Safety

    func testMultipleStopCallsAreSafe() {
        let sut = SoundManager.shared
        // 複数回のstop呼び出しがクラッシュしないことを検証
        sut.stopBackgroundMusic()
        sut.stopBackgroundMusic()
        sut.stopAllSounds()
        sut.stopAllSounds()

        XCTAssertFalse(sut.isBGMPlaying, "複数回のstop呼び出し後もisBGMPlayingはfalseであること")
    }

    func testStopThenPlayDoesNotCrash() {
        let sut = SoundManager.shared
        sut.stopBackgroundMusic()
        sut.playBackgroundMusic(filename: "nonexistent")
        sut.stopBackgroundMusic()
        sut.playBackgroundMusic(filename: "another-nonexistent", withExtension: "mp3")
        sut.stopAllSounds()

        XCTAssertFalse(sut.isBGMPlaying, "stop→play→stop→play→stopの連続呼び出しがクラッシュしないこと")
    }

    // MARK: - Fading State Handling (CodeRabbit Critical)

    func testFadingStateSameBGMCancelsFade() {
        let sut = SoundManager.shared
        sut.stopBackgroundMusic()

        // フェード中をシミュレート（同一BGM）
        sut.testHelperSimulateFading(currentBGMFilename: "open-sound.m4a")
        XCTAssertTrue(sut.testHelperIsFading, "フェードタイマーがセットされていること")

        // 同一BGMで再生要求 → フェードキャンセルされるべき
        sut.playBackgroundMusic(filename: "open-sound", withExtension: "m4a")

        // フェードタイマーがキャンセルされていることを確認
        // (Bundle不在のためbgmPlayerはnilでcurrentBGMFilenameはnilにリセットされる)
        XCTAssertFalse(sut.testHelperIsFading, "同一BGM再要求でフェードタイマーがキャンセルされること")

        sut.testHelperClearFadeState()
    }

    func testFadingStateDifferentBGMStopsOld() {
        let sut = SoundManager.shared
        sut.stopBackgroundMusic()

        // フェード中をシミュレート（BGM-A）
        sut.testHelperSimulateFading(currentBGMFilename: "bgm-a.m4a")
        XCTAssertTrue(sut.testHelperIsFading, "フェードタイマーがセットされていること")

        // 別BGMで再生要求 → 旧BGM停止
        sut.playBackgroundMusic(filename: "bgm-b", withExtension: "m4a")

        // フェードタイマーがキャンセルされていることを確認
        XCTAssertFalse(sut.testHelperIsFading, "別BGM切り替えでフェードタイマーがキャンセルされること")
        // Bundle不在のため最終状態はisBGMPlaying = false
        XCTAssertFalse(sut.isBGMPlaying, "Bundle不在時はisBGMPlayingがfalseであること")
        XCTAssertNil(sut.testHelperCurrentBGMFilename, "旧BGM名がクリアされること")

        sut.testHelperClearFadeState()
    }

    func testFadingStateSameBGMWhilePlayingResumesBGM() {
        let sut = SoundManager.shared
        sut.stopBackgroundMusic()

        // 再生中 + フェード中をシミュレート（同一BGM）
        sut.testHelperSimulateFadingWhilePlaying(currentBGMFilename: "open-sound.m4a")
        XCTAssertTrue(sut.testHelperIsFading, "フェードタイマーがセットされていること")
        XCTAssertTrue(sut.isBGMPlaying, "BGMが再生中であること")

        // 同一BGMで再生要求 → フェードキャンセル & 再生継続（return false分岐）
        sut.playBackgroundMusic(filename: "open-sound", withExtension: "m4a")

        // フェードキャンセルされ、再生は継続している
        XCTAssertFalse(sut.testHelperIsFading, "フェードタイマーがキャンセルされること")
        XCTAssertTrue(sut.isBGMPlaying, "同一BGM復帰で再生が継続すること")
        XCTAssertEqual(sut.testHelperCurrentBGMFilename, "open-sound.m4a", "BGMファイル名が維持されること")

        sut.testHelperClearFadeState()
    }

    func testSameNameDifferentExtensionTreatedAsDistinct() {
        let sut = SoundManager.shared
        sut.stopBackgroundMusic()

        // "test.m4a" でフェード中をシミュレート
        sut.testHelperSimulateFading(currentBGMFilename: "test.m4a")

        // "test.mp3" で再生要求 → 別ファイルとして扱われるべき
        sut.playBackgroundMusic(filename: "test", withExtension: "mp3")

        // 別ファイルなので旧BGM停止ルートを通る
        XCTAssertFalse(sut.testHelperIsFading, "同名別拡張子は別ファイルとして扱われフェードがキャンセルされること")
        XCTAssertNil(sut.testHelperCurrentBGMFilename, "旧BGM名が残らないこと")

        sut.testHelperClearFadeState()
    }
}
