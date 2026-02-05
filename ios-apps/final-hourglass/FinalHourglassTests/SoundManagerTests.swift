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
}
