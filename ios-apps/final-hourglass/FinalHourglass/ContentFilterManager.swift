// periphery:ignore:all - 将来使用予定
import Foundation
import SwiftUI

/// コンテンツフィルターの種類
enum ContentFilter: String, CaseIterable {
    case all
    case light
    case shadow

    var displayName: String {
        switch self {
        case .all:
            return "すべて表示"
        case .light:
            return "光のエピソード"
        case .shadow:
            return "影のエピソード"
        }
    }

    var icon: String {
        switch self {
        case .all:
            return "⚡"
        case .light:
            return "☀️"
        case .shadow:
            return "🌙"
        }
    }

    var description: String {
        switch self {
        case .all:
            return "偉人も独裁者も、すべての人間から学ぶ"
        case .light:
            return "偉人、英雄、聖人の美しい物語"
        case .shadow:
            return "独裁者、犯罪者から学ぶ歴史の教訓"
        }
    }
}

/// コンテンツフィルター管理クラス
class ContentFilterManager: ObservableObject {
    @Published var currentFilter: ContentFilter = .light
    @Published var hasSeenWarning: Bool = false
    @Published var userAge: Int?

    private let userDefaults = UserDefaults.standard
    private let filterKey = "contentFilter"
    private let warningKey = "hasSeenContentWarning"
    private let ageKey = "userAge"

    init() {
        loadSettings()
    }

    /// 設定の読み込み
    private func loadSettings() {
        if let filterString = userDefaults.string(forKey: filterKey),
           let filter = ContentFilter(rawValue: filterString) {
            currentFilter = filter
        }

        hasSeenWarning = userDefaults.bool(forKey: warningKey)

        if userDefaults.object(forKey: ageKey) != nil {
            userAge = userDefaults.integer(forKey: ageKey)
        }
    }

    /// フィルター変更
    func changeFilter(to filter: ContentFilter) {
        // 影のコンテンツへの変更時は警告を表示
        if filter == .shadow && !hasSeenWarning {
            // 警告表示後にフィルター変更
            return
        }

        currentFilter = filter
        userDefaults.set(filter.rawValue, forKey: filterKey)
    }

    /// 警告を確認済みにする
    func confirmWarning() {
        hasSeenWarning = true
        userDefaults.set(true, forKey: warningKey)
    }

    /// 年齢設定
    func setUserAge(_ age: Int) {
        userAge = age
        userDefaults.set(age, forKey: ageKey)
    }

    /// 年齢による制限チェック
    func canAccessShadowContent() -> Bool {
        guard let age = userAge else { return false }
        return age >= 17
    }

    // エピソード関連の機能は削除済み
    // 将来的に再実装が必要な場合はこのスペースを使用
}

/// コンテンツ警告ビュー
struct ContentWarningView: View {
    @ObservedObject var filterManager: ContentFilterManager
    @Binding var isPresented: Bool
    @State private var userAge: String = ""

    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 50))
                .foregroundColor(.orange)

            Text("重要な確認")
                .font(.title)
                .fontWeight(.bold)

            Text("このコンテンツには歴史上の独裁者、犯罪者、暴君などの教育的エピソードが含まれています。")
                .multilineTextAlignment(.center)
                .padding(.horizontal)

            Text("17歳以上の方のみ閲覧可能です")
                .font(.headline)
                .foregroundColor(.red)

            VStack(alignment: .leading, spacing: 10) {
                Text("含まれる内容:")
                    .fontWeight(.semibold)

                ForEach([
                    "• 独裁者の心理と転落",
                    "• 犯罪者の動機と結末",
                    "• 暴君の支配と破滅",
                    "• カルト指導者の手法"
                ], id: \.self) { item in
                    Text(item)
                        .font(.caption)
                }
            }
            .padding()
            .background(Color.gray.opacity(0.1))
            .cornerRadius(10)

            Text("教育的価値")
                .font(.headline)

            Text("これらのエピソードは、歴史の過ちを繰り返さないための教訓として提供されています。")
                .font(.caption)
                .multilineTextAlignment(.center)

            // 年齢入力
            HStack {
                Text("あなたの年齢:")
                TextField("年齢", text: $userAge)
                    .keyboardType(.numberPad)
                    .textFieldStyle(RoundedBorderTextFieldStyle())
                    .frame(width: 60)
            }

            HStack(spacing: 20) {
                Button(action: {
                    isPresented = false
                }) {
                    Text("キャンセル")
                        .padding(.horizontal, 30)
                        .padding(.vertical, 10)
                        .background(Color.gray.opacity(0.2))
                        .cornerRadius(10)
                }

                Button(action: {
                    if let age = Int(userAge), age >= 17 {
                        filterManager.setUserAge(age)
                        filterManager.confirmWarning()
                        filterManager.changeFilter(to: .shadow)
                        isPresented = false
                    }
                }) {
                    Text("理解しました")
                        .padding(.horizontal, 30)
                        .padding(.vertical, 10)
                        .background(Int(userAge) ?? 0 >= 17 ? Color.red : Color.gray)
                        .foregroundColor(.white)
                        .cornerRadius(10)
                }
                .disabled(Int(userAge) ?? 0 < 17)
            }
        }
        .padding()
        .frame(maxWidth: 400)
        .background(Color.white)
        .cornerRadius(20)
        .shadow(radius: 10)
    }
}

/// フィルター選択ビュー
struct ContentFilterSelector: View {
    @ObservedObject var filterManager: ContentFilterManager
    @State private var showingWarning = false

    var body: some View {
        VStack(spacing: 15) {
            Text("コンテンツフィルター")
                .font(.headline)

            ForEach(ContentFilter.allCases, id: \.self) { filter in
                Button(action: {
                    selectFilter(filter)
                }) {
                    HStack {
                        Text(filter.icon)
                            .font(.title2)

                        VStack(alignment: .leading) {
                            Text(filter.displayName)
                                .fontWeight(.semibold)
                            Text(filter.description)
                                .font(.caption)
                                .foregroundColor(.gray)
                        }

                        Spacer()

                        if filterManager.currentFilter == filter {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundColor(.blue)
                        }
                    }
                    .padding()
                    .background(
                        filterManager.currentFilter == filter ?
                        Color.blue.opacity(0.1) : Color.gray.opacity(0.05)
                    )
                    .cornerRadius(10)
                }
                .buttonStyle(PlainButtonStyle())
            }

            if filterManager.currentFilter == .shadow {
                Text("17歳以上限定コンテンツを表示中")
                    .font(.caption)
                    .foregroundColor(.red)
                    .padding(.top, 5)
            }
        }
        .padding()
        .sheet(isPresented: $showingWarning) {
            ContentWarningView(filterManager: filterManager, isPresented: $showingWarning)
        }
    }

    private func selectFilter(_ filter: ContentFilter) {
        if filter == .shadow && !filterManager.hasSeenWarning {
            showingWarning = true
        } else if filter == .shadow && !filterManager.canAccessShadowContent() {
            showingWarning = true
        } else {
            filterManager.changeFilter(to: filter)
        }
    }
}
