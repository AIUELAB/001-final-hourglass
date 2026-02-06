// periphery:ignore:all - 開発モード管理（デバッグ用途）
//
//  DeveloperModeManager.swift
//  FinalHourglass
//
//  開発モードの管理
//

import SwiftUI

// MARK: - UserDefaults Extension
extension UserDefaults {
    // 開発モードの永続化
    var isDeveloperMode: Bool {
        get { bool(forKey: "isDeveloperMode") }
        set { set(newValue, forKey: "isDeveloperMode") }
    }
}

// MARK: - Developer Mode Manager
class DeveloperModeManager: ObservableObject {
    // MARK: - Constants
    private let developerPassword = "dev2024"

    // MARK: - Published Properties
    @Published var isDeveloperMode: Bool {
        didSet {
            UserDefaults.standard.isDeveloperMode = isDeveloperMode
        }
    }

    @Published var showPasswordPrompt = false
    @Published var passwordInput = ""
    @Published var wrongPasswordAlert = false

    // MARK: - Initialization
    init() {
        self.isDeveloperMode = UserDefaults.standard.isDeveloperMode
    }

    // MARK: - Public Methods
    func toggleDeveloperMode() {
        if isDeveloperMode {
            // 開発モードをOFFにする
            isDeveloperMode = false
            logModeChange(enabled: false)
        } else {
            // パスワード入力を要求
            showPasswordPrompt = true
            passwordInput = ""
        }
    }

    func validatePassword() {
        if passwordInput == developerPassword {
            isDeveloperMode = true
            showPasswordPrompt = false
            passwordInput = "" // パスワードをクリア
            logModeChange(enabled: true)
        } else {
            wrongPasswordAlert = true
            passwordInput = "" // パスワードをクリア
        }
    }

    // MARK: - Private Methods
    private func logModeChange(enabled: Bool) {
        #if DEBUG
        print("🔧 Developer Mode: \(enabled ? "Enabled" : "Disabled")")
        #endif
    }
}

// MARK: - View Modifier
struct DeveloperModeModifier: ViewModifier {
    @EnvironmentObject var devManager: DeveloperModeManager

    func body(content: Content) -> some View {
        content
            .overlay(alignment: .topTrailing) {
                if devManager.isDeveloperMode {
                    VStack(spacing: 0) {
                        Text("DEV")
                            .font(.caption2)
                            .fontWeight(.bold)
                            .foregroundColor(.white)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Color.red)
                            .cornerRadius(4)
                    }
                    .padding(8)
                }
            }
    }
}

// MARK: - View Extension
extension View {
    func developerModeIndicator() -> some View {
        modifier(DeveloperModeModifier())
    }
}
