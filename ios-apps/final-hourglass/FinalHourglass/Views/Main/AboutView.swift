import MessageUI
import StoreKit
import SwiftUI

// MARK: - iOS 15/16 互換性対応
/// NavigationStack (iOS 16+) と NavigationView (iOS 15) の互換性ラッパー
private struct NavigationStackCompatible<Content: View>: View {
    let content: () -> Content

    init(@ViewBuilder content: @escaping () -> Content) {
        self.content = content
    }

    var body: some View {
        if #available(iOS 16.0, *) {
            NavigationStack {
                content()
            }
        } else {
            NavigationView {
                content()
            }
            .navigationViewStyle(.stack)
        }
    }
}

struct AboutView: View {
    @State private var showingMailComposer = false
    @State private var showingMailAlert = false

    private var appVersion: String {
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "Unknown"
    }
    @State private var showingUpdateHistory = false
    @State private var showingFAQ = false
    @State private var showingTerms = false
    @State private var showingPrivacy = false
    @State private var showingLicense = false
    @State private var showingDeveloper = false
    @State private var showingAcknowledgments = false

    var body: some View {
        ZStack {
            // 背景を先に配置
            MysticalSpaceBackground()
                .ignoresSafeArea()

            List {
                // アプリ情報ヘッダー
                VStack(spacing: 15) {
                    // アプリアイコン（神秘的なデザイン）
                    ZStack {
                        // ステンドグラスの枠
                        Circle()
                            .fill(
                                LinearGradient(
                                    colors: [Color.mysticalPurple.opacity(0.3), Color.mysticBlue.opacity(0.2)],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                            .frame(width: 100, height: 100)
                            .overlay(
                                Circle()
                                    .stroke(Color.mysticalPurple.opacity(0.5), lineWidth: 1)
                            )
                            .shadow(color: Color.mysticalPurple.opacity(0.5), radius: 20)

                        Image(systemName: "hourglass")
                            .font(.system(size: 50))
                            .foregroundStyle(
                                LinearGradient(
                                    colors: [Color.mysticalPurple, Color.mysticBlue],
                                    startPoint: .top,
                                    endPoint: .bottom
                                )
                            )
                    }

                    VStack(spacing: 8) {
                        Text("最期の砂時計")
                            .font(.system(size: 24, weight: .light, design: .serif))
                            .foregroundColor(.white)

                        Text("バージョン \(appVersion)")
                            .font(.caption)
                            .foregroundColor(Color.mysticalPurple.opacity(0.8))
                    }
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 30)
                .listRowBackground(Color.clear)
                .listRowInsets(EdgeInsets())

                // アプリ情報セクション
                Section(header:
                            Text("アプリ情報")
                    .foregroundColor(Color.mysticalPurple.opacity(0.8))
                    .font(.system(size: 13, weight: .regular))
                    .textCase(.uppercase)
                    .shadow(color: Color.mysticalPurple.opacity(0.4), radius: 4)
                ) {
                    VStack(spacing: 0) {
                        AboutActionButton(
                            icon: AnyView(
                                Image(systemName: "clock.arrow.circlepath")
                                    .foregroundColor(.white.opacity(0.9))
                                    .font(.system(size: 16))
                            ),
                            title: "更新履歴",
                            backgroundColor: Color.mysticBlue.opacity(0.2),
                            borderColor: Color.mysticBlue.opacity(0.3),
                            glowColor: Color.mysticBlue,
                            action: { showingUpdateHistory = true }
                        )
                    }
                    .background(
                        RoundedRectangle(cornerRadius: 14)
                            .fill(Color(white: 0.11, opacity: 0.4))
                            .overlay(
                                RoundedRectangle(cornerRadius: 14)
                                    .stroke(Color.mysticalPurple.opacity(0.1), lineWidth: 1)
                            )
                    )
                    .listRowBackground(Color.clear)
                    .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 16, trailing: 20))
                }

                // サポートセクション
                Section(header:
                            Text("サポート")
                    .foregroundColor(Color.mysticalPurple.opacity(0.8))
                    .font(.system(size: 13, weight: .regular))
                    .textCase(.uppercase)
                    .shadow(color: Color.mysticalPurple.opacity(0.4), radius: 4)
                ) {
                    VStack(spacing: 0) {
                        // お問い合わせ
                        AboutActionButton(
                            icon: AnyView(
                                Image(systemName: "envelope.fill")
                                    .foregroundColor(.white.opacity(0.9))
                                    .font(.system(size: 16))
                            ),
                            title: "お問い合わせ",
                            backgroundColor: Color(red: 0.3, green: 0.8, blue: 1.0).opacity(0.2),
                            borderColor: Color(red: 0.3, green: 0.8, blue: 1.0).opacity(0.3),
                            glowColor: Color(red: 0.3, green: 0.8, blue: 1.0),
                            action: { sendEmail() }
                        )

                        AboutItemDivider()

                        // よくある質問
                        AboutActionButton(
                            icon: AnyView(
                                Image(systemName: "questionmark.circle.fill")
                                    .foregroundColor(.white.opacity(0.9))
                                    .font(.system(size: 16))
                            ),
                            title: "よくある質問",
                            backgroundColor: Color.mysticalPurple.opacity(0.2),
                            borderColor: Color.mysticalPurple.opacity(0.3),
                            glowColor: Color.mysticalPurple,
                            action: { showingFAQ = true }
                        )

                        AboutItemDivider()

                        // アプリを評価
                        AboutActionButton(
                            icon: AnyView(
                                Image(systemName: "star.fill")
                                    .foregroundColor(.white.opacity(0.9))
                                    .font(.system(size: 16))
                            ),
                            title: "アプリを評価",
                            backgroundColor: Color.gold.opacity(0.2),
                            borderColor: Color.gold.opacity(0.3),
                            glowColor: Color.gold,
                            action: { requestReview() }
                        )
                    }
                    .background(
                        RoundedRectangle(cornerRadius: 14)
                            .fill(Color(white: 0.11, opacity: 0.4))
                            .overlay(
                                RoundedRectangle(cornerRadius: 14)
                                    .stroke(Color.mysticalPurple.opacity(0.1), lineWidth: 1)
                            )
                    )
                    .listRowBackground(Color.clear)
                    .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 16, trailing: 20))
                }

                // 法的情報セクション
                Section(header:
                            Text("法的情報")
                    .foregroundColor(Color.mysticalPurple.opacity(0.8))
                    .font(.system(size: 13, weight: .regular))
                    .textCase(.uppercase)
                    .shadow(color: Color.mysticalPurple.opacity(0.4), radius: 4)
                ) {
                    VStack(spacing: 0) {
                        AboutActionButton(
                            icon: AnyView(
                                Image(systemName: "doc.text.fill")
                                    .foregroundColor(.white.opacity(0.9))
                                    .font(.system(size: 16))
                            ),
                            title: "利用規約",
                            backgroundColor: Color.gray.opacity(0.2),
                            borderColor: Color.gray.opacity(0.3),
                            glowColor: Color.gray,
                            action: { showingTerms = true }
                        )

                        AboutItemDivider()

                        AboutActionButton(
                            icon: AnyView(
                                Image(systemName: "lock.shield.fill")
                                    .foregroundColor(.white.opacity(0.9))
                                    .font(.system(size: 16))
                            ),
                            title: "プライバシーポリシー",
                            backgroundColor: Color.gray.opacity(0.2),
                            borderColor: Color.gray.opacity(0.3),
                            glowColor: Color.gray,
                            action: { showingPrivacy = true }
                        )

                        AboutItemDivider()

                        AboutActionButton(
                            icon: AnyView(
                                Image(systemName: "doc.plaintext.fill")
                                    .foregroundColor(.white.opacity(0.9))
                                    .font(.system(size: 16))
                            ),
                            title: "ライセンス",
                            backgroundColor: Color.gray.opacity(0.2),
                            borderColor: Color.gray.opacity(0.3),
                            glowColor: Color.gray,
                            action: { showingLicense = true }
                        )
                    }
                    .background(
                        RoundedRectangle(cornerRadius: 14)
                            .fill(Color(white: 0.11, opacity: 0.4))
                            .overlay(
                                RoundedRectangle(cornerRadius: 14)
                                    .stroke(Color.mysticalPurple.opacity(0.1), lineWidth: 1)
                            )
                    )
                    .listRowBackground(Color.clear)
                    .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 16, trailing: 20))
                }

                // その他セクション
                Section(header:
                            Text("その他")
                    .foregroundColor(Color.mysticalPurple.opacity(0.8))
                    .font(.system(size: 13, weight: .regular))
                    .textCase(.uppercase)
                    .shadow(color: Color.mysticalPurple.opacity(0.4), radius: 4)
                ) {
                    VStack(spacing: 0) {
                        AboutActionButton(
                            icon: AnyView(
                                Image(systemName: "person.fill")
                                    .foregroundColor(.white.opacity(0.9))
                                    .font(.system(size: 16))
                            ),
                            title: "開発者について",
                            backgroundColor: Color.deepPink.opacity(0.2),
                            borderColor: Color.deepPink.opacity(0.3),
                            glowColor: Color.deepPink,
                            action: { showingDeveloper = true }
                        )

                        AboutItemDivider()

                        AboutActionButton(
                            icon: AnyView(
                                Image(systemName: "heart.fill")
                                    .foregroundColor(.white.opacity(0.9))
                                    .font(.system(size: 16))
                            ),
                            title: "謝辞",
                            backgroundColor: Color.limeGreen.opacity(0.2),
                            borderColor: Color.limeGreen.opacity(0.3),
                            glowColor: Color.limeGreen,
                            action: { showingAcknowledgments = true }
                        )
                    }
                    .background(
                        RoundedRectangle(cornerRadius: 14)
                            .fill(Color(white: 0.11, opacity: 0.4))
                            .overlay(
                                RoundedRectangle(cornerRadius: 14)
                                    .stroke(Color.mysticalPurple.opacity(0.1), lineWidth: 1)
                            )
                    )
                    .listRowBackground(Color.clear)
                    .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 16, trailing: 20))
                }

                // フッター
                VStack(spacing: 8) {
                    Text("© 2025 AIUELAB")
                        .foregroundColor(Color.mysticalPurple.opacity(0.4))
                    Text("Made with ❤️ in Tokyo")
                        .foregroundColor(Color.mysticalPurple.opacity(0.3))
                }
                .font(.caption)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 20)
                .listRowBackground(Color.clear)
            }
            .listStyle(PlainListStyle())
            .environment(\.defaultMinListRowHeight, 44)
            .onAppear {
                // UITableViewの外観をカスタマイズ
                UITableView.appearance().backgroundColor = .clear
                UITableView.appearance().separatorStyle = .none
                UITableViewCell.appearance().backgroundColor = .clear
                UITableView.appearance().separatorColor = .clear
            }
            .navigationTitle("About")
            .navigationBarTitleDisplayMode(.inline)
        }
        // シート表示（NavigationStackCompatibleで親のNavigationViewから分離）
        .sheet(isPresented: $showingUpdateHistory) {
            NavigationStackCompatible {
                UpdateHistoryView()
                    .toolbar {
                        ToolbarItem(placement: .topBarTrailing) {
                            Button("閉じる") {
                                showingUpdateHistory = false
                            }
                        }
                    }
            }
        }
        .sheet(isPresented: $showingFAQ) {
            NavigationStackCompatible {
                FAQView()
                    .toolbar {
                        ToolbarItem(placement: .topBarTrailing) {
                            Button("閉じる") {
                                showingFAQ = false
                            }
                        }
                    }
            }
        }
        .sheet(isPresented: $showingTerms) {
            NavigationStackCompatible {
                TermsView()
                    .toolbar {
                        ToolbarItem(placement: .topBarTrailing) {
                            Button("閉じる") {
                                showingTerms = false
                            }
                        }
                    }
            }
        }
        .sheet(isPresented: $showingPrivacy) {
            NavigationStackCompatible {
                PrivacyView()
                    .toolbar {
                        ToolbarItem(placement: .topBarTrailing) {
                            Button("閉じる") {
                                showingPrivacy = false
                            }
                        }
                    }
            }
        }
        .sheet(isPresented: $showingLicense) {
            NavigationStackCompatible {
                LicenseView()
                    .toolbar {
                        ToolbarItem(placement: .topBarTrailing) {
                            Button("閉じる") {
                                showingLicense = false
                            }
                        }
                    }
            }
        }
        .sheet(isPresented: $showingDeveloper) {
            NavigationStackCompatible {
                DeveloperView()
                    .toolbar {
                        ToolbarItem(placement: .topBarTrailing) {
                            Button("閉じる") {
                                showingDeveloper = false
                            }
                        }
                    }
            }
        }
        .sheet(isPresented: $showingAcknowledgments) {
            NavigationStackCompatible {
                AcknowledgmentsView()
                    .toolbar {
                        ToolbarItem(placement: .topBarTrailing) {
                            Button("閉じる") {
                                showingAcknowledgments = false
                            }
                        }
                    }
            }
        }
        .sheet(isPresented: $showingMailComposer) {
            MailComposerView(
                recipients: ["support@lifelimit.app"],
                subject: "最期の砂時計 - お問い合わせ",
                messageBody: """


                   -----
                   アプリバージョン: \(appVersion)
                   デバイス: \(UIDevice.current.model)
                   OS: iOS \(UIDevice.current.systemVersion)
                   """
            )
        }
        .alert("メールを送信できません", isPresented: $showingMailAlert) {
            Button("OK", role: .cancel) { }
        } message: {
            Text("メールアプリが設定されていません。\n\nsupport@lifelimit.app\n\nこちらのアドレスに直接お問い合わせください。")
        }
    }

    private func sendEmail() {
        if MFMailComposeViewController.canSendMail() {
            showingMailComposer = true
        } else {
            showingMailAlert = true
        }
    }

    private func requestReview() {
        if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene {
            if #available(iOS 18.0, *) {
                AppStore.requestReview(in: windowScene)
            } else {
                SKStoreReviewController.requestReview(in: windowScene)
            }
        }
    }
}

// MARK: - About用のカスタムボタン（アクション版のみ使用）
struct AboutActionButton: View {
    let icon: AnyView
    let title: String
    let backgroundColor: Color
    let borderColor: Color
    let glowColor: Color
    let action: () -> Void

    @State private var isPressed = false
    @State private var shimmerOffset: CGFloat = -1

    var body: some View {
        HStack {
            ZStack {
                RoundedRectangle(cornerRadius: 6)
                    .fill(backgroundColor)
                    .frame(width: 28, height: 28)
                    .overlay(
                        RoundedRectangle(cornerRadius: 6)
                            .stroke(borderColor, lineWidth: 1)
                    )
                    .shadow(color: glowColor.opacity(0.5), radius: 8)

                icon

                // 光沢効果
                SettingsIconShimmer(shimmerOffset: $shimmerOffset)
            }

            Text(title)
                .foregroundColor(.white.opacity(0.85))
                .font(.system(size: 17, weight: .regular))
                .shadow(color: .black.opacity(0.5), radius: 1.5, x: 0, y: 1)

            Spacer()

            Image(systemName: "chevron.right")
                .foregroundColor(.secondary)
                .font(.system(size: 16))
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(
            isPressed ? Color.white.opacity(0.05) : Color.clear
        )
        .scaleEffect(isPressed ? 0.98 : 1.0)
        .contentShape(Rectangle())
        .onTapGesture {
            withAnimation(.easeInOut(duration: 0.1)) {
                isPressed = true
            }

            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                isPressed = false
                action()
            }
        }
    }
}

// MARK: - セクション間の区切り線
struct AboutItemDivider: View {
    var body: some View {
        Divider()
            .background(Color.mysticalPurple.opacity(0.1))
            .padding(.leading, 56)
    }
}

// MARK: - サブビュー（すべて同じまま）

// UpdateHistoryView
struct UpdateHistoryView: View {
    private let entries = VersionHistoryLoader.load()

    var body: some View {
        ZStack {
            MysticalSpaceBackground()
                .ignoresSafeArea()

            if entries.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: "doc.text")
                        .font(.system(size: 40))
                        .foregroundColor(Color.mysticalPurple.opacity(0.5))
                    Text("更新履歴を読み込めませんでした")
                        .foregroundColor(.white.opacity(0.7))
                }
            }

            List {
                ForEach(entries) { entry in
                    Section(header: Text("バージョン \(entry.version)")
                        .foregroundColor(Color.mysticalPurple.opacity(0.8))
                    ) {
                        VStack(alignment: .leading, spacing: 10) {
                            Text(entry.releaseDate)
                                .font(.caption)
                                .foregroundColor(Color.mysticalPurple.opacity(0.6))

                            VStack(alignment: .leading, spacing: 8) {
                                ForEach(entry.changes, id: \.self) { change in
                                    Text("• \(change)")
                                }
                            }
                            .foregroundColor(.white.opacity(0.85))
                        }
                        .padding(.vertical, 5)
                        .listRowBackground(
                            RoundedRectangle(cornerRadius: 14)
                                .fill(Color(white: 0.11, opacity: 0.4))
                        )
                    }
                }
            }
            .listStyle(PlainListStyle())
        }
        .navigationTitle("更新履歴")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// FAQView
struct FAQView: View {
    var body: some View {
        ZStack {
            MysticalSpaceBackground()
                .ignoresSafeArea()

            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    FAQItem(
                        question: "人生のタイムリミットはどのように計算されますか？",
                        answer: "統計データと個人の健康情報を基に、AI が予測寿命を算出します。"
                    )

                    FAQItem(
                        question: "エピソードはどのように選ばれますか？",
                        answer: "あなたの現在の年齢に合わせて、同じ年齢の時の著名人（歴史上の偉人から現代のスポーツ選手、起業家まで）のエピソードを表示します。"
                    )

                    FAQItem(
                        question: "データは安全ですか？",
                        answer: "すべてのデータはデバイス内に保存され、外部に送信されることはありません。"
                    )
                }
                .padding()
            }
        }
        .navigationTitle("よくある質問")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct FAQItem: View {
    let question: String
    let answer: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(question)
                .font(.headline)
                .foregroundColor(.white)

            Text(answer)
                .font(.body)
                .foregroundColor(.white.opacity(0.7))
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(Color(white: 0.11, opacity: 0.4))
                .overlay(
                    RoundedRectangle(cornerRadius: 14)
                        .stroke(Color.mysticalPurple.opacity(0.1), lineWidth: 1)
                )
        )
    }
}

// TermsView
struct TermsView: View {
    var body: some View {
        ZStack {
            MysticalSpaceBackground()
                .ignoresSafeArea()

            ScrollView {
                Text("""
               利用規約

               最終更新日: 2024年3月1日

               1. サービスの利用
               本アプリケーションをダウンロードまたは使用することにより、これらの利用規約に同意したものとみなされます。

               2. 個人情報の取り扱い
               当社は、お客様の個人情報を適切に保護し、プライバシーポリシーに従って取り扱います。

               3. 免責事項
               本アプリケーションが提供する寿命予測は、統計的な推定に基づくものであり、実際の寿命を保証するものではありません。

               4. 知的財産権
               本アプリケーションに含まれるすべてのコンテンツは、当社または第三者の知的財産権によって保護されています。
               """)
                .foregroundColor(.white.opacity(0.85))
                .padding()
            }
        }
        .navigationTitle("利用規約")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// PrivacyView
struct PrivacyView: View {
    var body: some View {
        ZStack {
            MysticalSpaceBackground()
                .ignoresSafeArea()

            ScrollView {
                Text("""
               プライバシーポリシー

               最終更新日: 2024年3月1日

               1. 収集する情報
               - 生年月日
               - 性別
               - 健康に関する基本情報

               2. 情報の利用目的
               収集した情報は、寿命予測の精度向上のためにのみ使用されます。

               3. 情報の保存
               すべての個人情報は、お客様のデバイス内にのみ保存され、外部サーバーに送信されることはありません。

               4. 第三者への提供
               当社は、お客様の個人情報を第三者に販売、貸与、または提供することはありません。
               """)
                .foregroundColor(.white.opacity(0.85))
                .padding()
            }
        }
        .navigationTitle("プライバシーポリシー")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// LicenseView
struct LicenseView: View {
    var body: some View {
        ZStack {
            MysticalSpaceBackground()
                .ignoresSafeArea()

            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    Text("オープンソースライセンス")
                        .font(.headline)
                        .foregroundColor(.white)

                    LicenseItem(
                        name: "SwiftUI",
                        license: "Apple Inc. All rights reserved."
                    )

                    LicenseItem(
                        name: "Supabase",
                        license: "Apache License 2.0"
                    )
                }
                .padding()
            }
        }
        .navigationTitle("ライセンス")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct LicenseItem: View {
    let name: String
    let license: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(name)
                .font(.subheadline)
                .fontWeight(.semibold)
                .foregroundColor(.white)

            Text(license)
                .font(.caption)
                .foregroundColor(.white.opacity(0.6))
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(Color(white: 0.11, opacity: 0.4))
        )
    }
}

// DeveloperView
struct DeveloperView: View {
    var body: some View {
        ZStack {
            MysticalSpaceBackground()
                .ignoresSafeArea()

            VStack(spacing: 30) {
                // デベロッパーロゴ
                ZStack {
                    Circle()
                        .fill(
                            LinearGradient(
                                colors: [Color.mysticalPurple.opacity(0.3), Color.mysticBlue.opacity(0.2)],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .frame(width: 120, height: 120)
                        .overlay(
                            Circle()
                                .stroke(Color.mysticalPurple.opacity(0.5), lineWidth: 1)
                        )
                        .shadow(color: Color.mysticalPurple.opacity(0.5), radius: 20)

                    Text("AIU")
                        .font(.system(size: 40, weight: .thin, design: .serif))
                        .foregroundColor(.white)
                }

                VStack(spacing: 10) {
                    Text("AIUELAB")
                        .font(.system(size: 28, weight: .light, design: .serif))
                        .foregroundColor(.white)

                    Text("Crafting Digital Experiences")
                        .font(.subheadline)
                        .foregroundColor(Color.mysticalPurple.opacity(0.8))
                }

                VStack(spacing: 20) {
                    Link(destination: URL(string: "https://aiuelabo.com")!) {
                        HStack {
                            Image(systemName: "globe")
                            Text("Website")
                        }
                        .foregroundColor(.white)
                        .padding(.horizontal, 30)
                        .padding(.vertical, 12)
                        .background(
                            Capsule()
                                .fill(Color.mysticalPurple.opacity(0.3))
                                .overlay(
                                    Capsule()
                                        .stroke(Color.mysticalPurple.opacity(0.5), lineWidth: 1)
                                )
                        )
                    }

                    Link(destination: URL(string: "https://twitter.com/aiuelabo")!) {
                        HStack {
                            Image(systemName: "link")
                            Text("Follow us")
                        }
                        .foregroundColor(.white)
                        .padding(.horizontal, 30)
                        .padding(.vertical, 12)
                        .background(
                            Capsule()
                                .fill(Color.mysticBlue.opacity(0.3))
                                .overlay(
                                    Capsule()
                                        .stroke(Color.mysticBlue.opacity(0.5), lineWidth: 1)
                                )
                        )
                    }
                }

                Spacer()
            }
            .padding(.top, 50)
        }
        .navigationTitle("開発者について")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// AcknowledgmentsView
struct AcknowledgmentsView: View {
    var body: some View {
        ZStack {
            MysticalSpaceBackground()
                .ignoresSafeArea()

            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    Text("このアプリケーションの開発にあたり、以下の方々に深く感謝いたします。")
                        .foregroundColor(.white.opacity(0.85))
                        .padding(.bottom, 10)

                    AcknowledgmentItem(
                        title: "デザインインスピレーション",
                        description: "美しい宇宙と神秘的なビジュアルデザインのアイデアを与えてくれた全てのアーティストたち"
                    )

                    AcknowledgmentItem(
                        title: "技術サポート",
                        description: "SwiftUI と Firebase の素晴らしいドキュメントとコミュニティ"
                    )

                    AcknowledgmentItem(
                        title: "ユーザーフィードバック",
                        description: "アプリをより良くするための貴重な意見を提供してくれた全てのユーザーの皆様"
                    )

                    AcknowledgmentItem(
                        title: "特別な感謝",
                        description: "人生の有限性について深い洞察を与えてくれた哲学者、思想家の皆様"
                    )
                }
                .padding()
            }
        }
        .navigationTitle("謝辞")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct AcknowledgmentItem: View {
    let title: String
    let description: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.headline)
                .foregroundColor(.white)

            Text(description)
                .font(.body)
                .foregroundColor(.white.opacity(0.7))
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(Color(white: 0.11, opacity: 0.4))
                .overlay(
                    RoundedRectangle(cornerRadius: 14)
                        .stroke(Color.mysticalPurple.opacity(0.1), lineWidth: 1)
                )
        )
    }
}

// AboutView.swiftの最後に追加

struct MailComposerView: UIViewControllerRepresentable {
    let recipients: [String]
    let subject: String
    let messageBody: String

    @Environment(\.dismiss) private var dismiss

    func makeUIViewController(context: Context) -> MFMailComposeViewController {
        let mailComposer = MFMailComposeViewController()
        mailComposer.mailComposeDelegate = context.coordinator
        mailComposer.setToRecipients(recipients)
        mailComposer.setSubject(subject)
        mailComposer.setMessageBody(messageBody, isHTML: false)
        return mailComposer
    }

    func updateUIViewController(_ uiViewController: MFMailComposeViewController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    class Coordinator: NSObject, MFMailComposeViewControllerDelegate {
        let parent: MailComposerView

        init(_ parent: MailComposerView) {
            self.parent = parent
        }

        func mailComposeController(_ controller: MFMailComposeViewController, didFinishWith result: MFMailComposeResult, error: Error?) {
            parent.dismiss()
        }
    }
}
