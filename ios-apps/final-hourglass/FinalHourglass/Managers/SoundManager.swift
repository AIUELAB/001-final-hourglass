import AVFoundation
import Foundation
import UIKit

// タップ音の種類
enum TapSoundType: Hashable {
    case soft      // 通常のタップ
    case confirm   // 確認・決定
    case cancel    // キャンセル
    case success   // 成功
    case warning   // 警告
}

class SoundManager: ObservableObject {
    static let shared = SoundManager()

    private var bgmPlayer: AVAudioPlayer?
    private var soundEffectPlayer: AVAudioPlayer?
    private var fadeTimer: Timer?
    private var currentBGMFilename: String?
    @Published var isBGMPlaying = false
    @Published var bgmVolume: Float = UserDefaults.standard.object(forKey: "bgmVolume") as? Float ?? 0.3 // デフォルト音量（30%）
    @Published var hapticEnabled: Bool = UserDefaults.standard.object(forKey: "hapticEnabled") as? Bool ?? true {
        didSet {
            UserDefaults.standard.set(hapticEnabled, forKey: "hapticEnabled")
        }
    }

    private init() {
        setupAudioSession()
    }

    private func setupAudioSession() {
        do {
            try AVAudioSession.sharedInstance().setCategory(.ambient, mode: .default)
            try AVAudioSession.sharedInstance().setActive(true)
        } catch {
            #if DEBUG
            print("オーディオセッションの設定に失敗: \(error)")
            #endif
            // Release でもリトライ（1回のみ）
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                do {
                    try AVAudioSession.sharedInstance().setCategory(.ambient, mode: .default)
                    try AVAudioSession.sharedInstance().setActive(true)
                } catch {
                    #if DEBUG
                    print("オーディオセッションのリトライも失敗: \(error)")
                    #endif
                }
            }
        }
    }

    // すべてのフェード処理をキャンセル
    private func cancelFadeTimers() {
        fadeTimer?.invalidate()
        fadeTimer = nil
    }

    /// フェード中のBGM再生要求を処理し、新規再生が必要かどうかを返す
    /// - Returns: `true` なら新規再生に進む、`false` なら呼び出し元で `return` する
    private func handleFadingState(for fullFilename: String) -> Bool {
        guard fadeTimer != nil else { return true }

        // 同じBGMのフェード中 → キャンセルして再生継続
        if currentBGMFilename == fullFilename {
            cancelFadeTimers()
            if let player = bgmPlayer, player.isPlaying {
                player.volume = bgmVolume
                isBGMPlaying = true
                #if DEBUG
                print("BGMフェードアウトキャンセル、再生継続: \(fullFilename)")
                #endif
                return false
            }
            currentBGMFilename = nil
        } else {
            // 別BGMへ切り替え → フェードキャンセル＆旧プレイヤー停止
            cancelFadeTimers()
            stopCurrentBGM()
        }
        return true
    }

    /// BGMをループ再生する
    /// - Parameters:
    ///   - filename: ファイル名（拡張子なし、デフォルト: "open-sound"）
    ///   - ext: 拡張子（デフォルト: "m4a"）
    func playBackgroundMusic(filename: String = "open-sound", withExtension ext: String = "m4a") {
        let fullFilename = "\(filename).\(ext)"

        // 同じBGMが既に再生中ならスキップ（タブ切り替え時の途切れ防止）
        if currentBGMFilename == fullFilename && bgmPlayer?.isPlaying == true && fadeTimer == nil {
            #if DEBUG
            print("BGM再生スキップ（同一ファイル再生中）: \(fullFilename)")
            #endif
            return
        }

        // フェード中の状態をハンドリング（同一BGM復帰 or 別BGM切り替え）
        if !handleFadingState(for: fullFilename) { return }

        guard let url = Bundle.main.url(forResource: filename, withExtension: ext) else {
            #if DEBUG
            print("音楽ファイルが見つかりません: \(filename).\(ext)")
            #endif
            return
        }

        do {
            bgmPlayer = try AVAudioPlayer(contentsOf: url)
            bgmPlayer?.numberOfLoops = -1 // 無限ループ
            bgmPlayer?.volume = bgmVolume
            bgmPlayer?.prepareToPlay()
            bgmPlayer?.play()
            isBGMPlaying = true
            currentBGMFilename = "\(filename).\(ext)"
            #if DEBUG
            print("BGM再生開始: \(filename).\(ext)")
            #endif
        } catch {
            #if DEBUG
            print("BGM再生エラー: \(error)")
            #endif
            bgmPlayer = nil
            isBGMPlaying = false
            currentBGMFilename = nil
        }
    }

    /// 現在再生中のBGMを停止し、フェードタイマーも解除する
    func stopBackgroundMusic() {
        cancelFadeTimers()  // タイマーをキャンセル
        bgmPlayer?.stop()
        bgmPlayer = nil
        isBGMPlaying = false
        currentBGMFilename = nil
        #if DEBUG
        print("BGM停止")
        #endif
    }

    /// BGMと効果音をすべて即座に停止する
    func stopAllSounds() {
        // タイマーを即座にキャンセル
        cancelFadeTimers()

        // BGMを即座に停止
        if bgmPlayer != nil {
            bgmPlayer?.stop()
            bgmPlayer = nil
            isBGMPlaying = false
            currentBGMFilename = nil
            #if DEBUG
            print("BGM即座停止")
            #endif
        }

        // 効果音を即座に停止
        if soundEffectPlayer != nil {
            soundEffectPlayer?.stop()
            soundEffectPlayer = nil
            #if DEBUG
            print("効果音即座停止")
            #endif
        }
    }

    /// BGM音量を設定する（0.0〜1.0にクランプ）
    /// - Parameter volume: 設定する音量
    func setBGMVolume(_ volume: Float) {
        bgmVolume = max(0.0, min(1.0, volume))
        bgmPlayer?.volume = bgmVolume
    }

    /// BGMをフェードインで再生開始する
    /// - Parameters:
    ///   - duration: フェード時間（秒、デフォルト: 2.0）
    ///   - filename: ファイル名（拡張子なし、デフォルト: "open-sound"）
    ///   - ext: 拡張子（デフォルト: "m4a"）
    func fadeInBackgroundMusic(duration: TimeInterval = 2.0, filename: String = "open-sound", withExtension ext: String = "m4a") {
        // 同じBGMが既に再生中ならスキップ（実際の再生状態とフェード状態を確認）
        if currentBGMFilename == "\(filename).\(ext)" && bgmPlayer?.isPlaying == true && fadeTimer == nil {
            #if DEBUG
            print("BGMフェードインスキップ（同一ファイル再生中）: \(filename).\(ext)")
            #endif
            return
        }

        cancelFadeTimers()  // 既存のフェードをキャンセル
        stopCurrentBGM()

        guard prepareBGMPlayer(filename: filename, withExtension: ext) else { return }

        #if DEBUG
        print("BGMフェードイン開始: \(filename).\(ext)")
        #endif

        // フェードインアニメーション
        var currentStep = 0
        let totalSteps = 20
        let volumeIncrement = bgmVolume / Float(totalSteps)

        fadeTimer = Timer.scheduledTimer(withTimeInterval: duration / Double(totalSteps), repeats: true) { [weak self] timer in
            currentStep += 1
            self?.bgmPlayer?.volume = volumeIncrement * Float(currentStep)

            if currentStep >= totalSteps {
                timer.invalidate()
                self?.fadeTimer = nil
                #if DEBUG
                print("BGMフェードイン完了")
                #endif
            }
        }
    }

    private func stopCurrentBGM() {
        bgmPlayer?.stop()
        bgmPlayer = nil
        isBGMPlaying = false
        currentBGMFilename = nil
    }

    private func prepareBGMPlayer(filename: String, withExtension ext: String) -> Bool {
        guard let url = Bundle.main.url(forResource: filename, withExtension: ext) else {
            #if DEBUG
            print("音楽ファイルが見つかりません: \(filename).\(ext)")
            #endif
            return false
        }

        do {
            bgmPlayer = try AVAudioPlayer(contentsOf: url)
            bgmPlayer?.numberOfLoops = -1
            bgmPlayer?.volume = 0
            bgmPlayer?.prepareToPlay()
            bgmPlayer?.play()
            isBGMPlaying = true
            currentBGMFilename = "\(filename).\(ext)"
            return true
        } catch {
            #if DEBUG
            print("BGM再生エラー: \(error)")
            #endif
            bgmPlayer = nil
            isBGMPlaying = false
            currentBGMFilename = nil
            return false
        }
    }

    /// 現在のBGMをフェードアウトで停止する
    /// - Parameters:
    ///   - duration: フェード時間（秒、デフォルト: 2.0）
    ///   - completion: フェード完了時のコールバック
    func fadeOutBackgroundMusic(duration: TimeInterval = 2.0, completion: (() -> Void)? = nil) {
        // bgmPlayerがnilの場合は即座に完了
        guard bgmPlayer != nil else {
            completion?()
            return
        }

        cancelFadeTimers()  // 既存のフェードをキャンセル

        let currentVolume = bgmPlayer?.volume ?? bgmVolume
        var currentStep = 0
        let totalSteps = 20
        let volumeDecrement = currentVolume / Float(totalSteps)

        fadeTimer = Timer.scheduledTimer(withTimeInterval: duration / Double(totalSteps), repeats: true) { [weak self] timer in
            currentStep += 1
            let newVolume = currentVolume - (volumeDecrement * Float(currentStep))
            self?.bgmPlayer?.volume = max(0, newVolume)

            if currentStep >= totalSteps {
                timer.invalidate()
                self?.fadeTimer = nil
                self?.stopBackgroundMusic()
                completion?()
            }
        }
    }

    /// 効果音を再生（単発）
    /// - Parameters:
    ///   - filename: ファイル名（拡張子なし）
    ///   - ext: 拡張子（デフォルト: m4a）
    ///   - volume: 基準音量（デフォルト: 0.5）
    ///   - syncWithBGMVolume: trueの場合、BGM音量設定と同期（volume * bgmVolume）
    func playSoundEffect(filename: String, withExtension ext: String = "m4a", volume: Float = 0.5, syncWithBGMVolume: Bool = false) {
        guard let url = Bundle.main.url(forResource: filename, withExtension: ext) else {
            #if DEBUG
            print("効果音ファイルが見つかりません: \(filename).\(ext)")
            #endif
            return
        }

        do {
            soundEffectPlayer = try AVAudioPlayer(contentsOf: url)
            soundEffectPlayer?.numberOfLoops = 0 // 単発再生

            // BGM音量同期対応
            let effectiveVolume = syncWithBGMVolume ? (volume * bgmVolume) : volume
            soundEffectPlayer?.volume = max(0.0, min(1.0, effectiveVolume))

            soundEffectPlayer?.prepareToPlay()
            soundEffectPlayer?.play()
            #if DEBUG
            print("効果音再生: \(filename).\(ext), volume=\(effectiveVolume)")
            #endif
        } catch {
            #if DEBUG
            print("効果音再生エラー: \(error)")
            #endif
            soundEffectPlayer = nil
        }
    }

    // タップフィードバック設定
    private struct TapFeedbackConfig {
        let notificationStyle: UINotificationFeedbackGenerator.FeedbackType?
        let impactStyle: UIImpactFeedbackGenerator.FeedbackStyle
        let soundID: SystemSoundID
    }

    // 各TapSoundTypeに対応するフィードバック設定
    private let tapFeedbackConfigs: [TapSoundType: TapFeedbackConfig] = [
        .soft: TapFeedbackConfig(notificationStyle: nil, impactStyle: .light, soundID: 1104),      // Modern tick sound
        .confirm: TapFeedbackConfig(notificationStyle: nil, impactStyle: .medium, soundID: 1113), // Begin recording sound
        .cancel: TapFeedbackConfig(notificationStyle: nil, impactStyle: .light, soundID: 1105),   // Exit/Back sound
        .success: TapFeedbackConfig(notificationStyle: .success, impactStyle: .medium, soundID: 1114), // Task completed sound
        .warning: TapFeedbackConfig(notificationStyle: .warning, impactStyle: .heavy, soundID: 1106)   // Alert sound
    ]

    /// タップ音とハプティックフィードバックを再生する
    /// - Parameter type: タップ音の種類
    func playTapSound(_ type: TapSoundType) {
        guard let config = tapFeedbackConfigs[type] else { return }

        // ハプティックフィードバックを先に実行（遅延なしで即座に反応）
        if hapticEnabled {
            // Notification feedbackがある場合はそちらを優先
            if let notificationStyle = config.notificationStyle {
                let notificationFeedback = UINotificationFeedbackGenerator()
                notificationFeedback.prepare()
                notificationFeedback.notificationOccurred(notificationStyle)
            } else {
                // Impact feedbackを使用
                let impactFeedback = UIImpactFeedbackGenerator(style: config.impactStyle)
                impactFeedback.prepare()
                impactFeedback.impactOccurred()
            }
        }

        // システムサウンドを再生（音量設定に関係なく再生される）
        AudioServicesPlaySystemSound(config.soundID)
    }

    /// 選択フィードバック（ピッカー操作など）を再生する
    func playSelectionSound() {
        if hapticEnabled {
            let selectionFeedback = UISelectionFeedbackGenerator()
            selectionFeedback.prepare()
            selectionFeedback.selectionChanged()
        }
        AudioServicesPlaySystemSound(1104) // Tick sound
    }

    // MARK: - Test Helpers

    // swiftlint:disable identifier_name
    #if DEBUG
    func testHelperSimulateFading(currentBGMFilename: String?) {
        self.currentBGMFilename = currentBGMFilename
        cancelFadeTimers()
        fadeTimer = Timer.scheduledTimer(withTimeInterval: 999, repeats: false) { _ in }
    }

    // swiftlint:disable function_body_length
    func testHelperSimulateFadingWhilePlaying(currentBGMFilename: String?) {
        self.currentBGMFilename = currentBGMFilename
        cancelFadeTimers()
        fadeTimer = Timer.scheduledTimer(withTimeInterval: 999, repeats: false) { _ in }

        // 最小限の無音WAVデータでbgmPlayerを作成し再生状態にする
        let sampleRate: UInt32 = 8000
        let numSamples: UInt32 = 8000
        let bitsPerSample: UInt16 = 16
        let numChannels: UInt16 = 1
        let dataSize = numSamples * UInt32(bitsPerSample / 8) * UInt32(numChannels)
        var wavData = Data()
        // RIFF header
        wavData.append(contentsOf: [0x52, 0x49, 0x46, 0x46]) // "RIFF"
        var chunkSize = 36 + dataSize
        wavData.append(Data(bytes: &chunkSize, count: 4))
        wavData.append(contentsOf: [0x57, 0x41, 0x56, 0x45]) // "WAVE"
        // fmt sub-chunk
        wavData.append(contentsOf: [0x66, 0x6D, 0x74, 0x20]) // "fmt "
        var subchunk1Size: UInt32 = 16
        wavData.append(Data(bytes: &subchunk1Size, count: 4))
        var audioFormat: UInt16 = 1 // PCM
        wavData.append(Data(bytes: &audioFormat, count: 2))
        var channels = numChannels
        wavData.append(Data(bytes: &channels, count: 2))
        var rate = sampleRate
        wavData.append(Data(bytes: &rate, count: 4))
        var byteRate = sampleRate * UInt32(numChannels) * UInt32(bitsPerSample / 8)
        wavData.append(Data(bytes: &byteRate, count: 4))
        var blockAlign = numChannels * (bitsPerSample / 8)
        wavData.append(Data(bytes: &blockAlign, count: 2))
        var bps = bitsPerSample
        wavData.append(Data(bytes: &bps, count: 2))
        // data sub-chunk
        wavData.append(contentsOf: [0x64, 0x61, 0x74, 0x61]) // "data"
        var dSize = dataSize
        wavData.append(Data(bytes: &dSize, count: 4))
        wavData.append(Data(count: Int(dataSize))) // 無音データ

        do {
            bgmPlayer = try AVAudioPlayer(data: wavData)
            bgmPlayer?.numberOfLoops = -1
            bgmPlayer?.volume = bgmVolume
            bgmPlayer?.prepareToPlay()
            bgmPlayer?.play()
            isBGMPlaying = true
        } catch {
            print("テスト用音声プレイヤー作成失敗: \(error)")
        }
    }
    // swiftlint:enable function_body_length

    func testHelperClearFadeState() {
        cancelFadeTimers()
        stopCurrentBGM()
    }

    var testHelperCurrentBGMFilename: String? { currentBGMFilename }
    var testHelperIsFading: Bool { fadeTimer != nil }
    #endif
    // swiftlint:enable identifier_name
}
