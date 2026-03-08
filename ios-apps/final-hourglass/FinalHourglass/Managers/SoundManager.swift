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
            bgmPlayer?.stop()
            bgmPlayer = nil
            isBGMPlaying = false
            currentBGMFilename = nil
        }
        return true
    }

    // BGM再生開始
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

    // BGM停止
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

    // 全ての音声を即座に停止
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

    // 音量調整
    func setBGMVolume(_ volume: Float) {
        bgmVolume = max(0.0, min(1.0, volume))
        bgmPlayer?.volume = bgmVolume
    }

    // フェードイン
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
        guard bgmPlayer != nil else { return }
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

    // フェードアウト
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

    // タップ音とハプティックフィードバック
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

    // 選択音（ピッカーなど用）
    func playSelectionSound() {
        if hapticEnabled {
            let selectionFeedback = UISelectionFeedbackGenerator()
            selectionFeedback.prepare()
            selectionFeedback.selectionChanged()
        }
        AudioServicesPlaySystemSound(1104) // Tick sound
    }
}
