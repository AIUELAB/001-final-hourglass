import MessageUI
import SwiftUI
import UIKit

// MARK: - FeedbackCategory

/// フィードバックのカテゴリ
enum FeedbackCategory: String, CaseIterable, Identifiable {
    case bugReport = "bug_report"
    case featureRequest = "feature_request"
    case usability = "usability"
    case other = "other"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .bugReport: return "バグ報告"
        case .featureRequest: return "機能要望"
        case .usability: return "使いにくい"
        case .other: return "その他"
        }
    }

    var icon: String {
        switch self {
        case .bugReport: return "ladybug"
        case .featureRequest: return "lightbulb"
        case .usability: return "hand.tap"
        case .other: return "ellipsis.circle"
        }
    }
}

// MARK: - FeedbackFormView

/// アプリ内フィードバック送信フォーム
struct FeedbackFormView: View {
    @Environment(\.dismiss) private var dismiss

    @State private var selectedCategory: FeedbackCategory = .other
    @State private var feedbackText: String = ""
    @State private var showingMailComposer = false
    @State private var showingMailAlert = false

    /// フィードバック送信先メールアドレス
    private let supportEmail = "support@lifelimit.app"

    var body: some View {
        NavigationView {
            Form {
                // カテゴリ選択
                Section(header: Text("カテゴリ")) {
                    ForEach(FeedbackCategory.allCases) { category in
                        Button {
                            selectedCategory = category
                        } label: {
                            HStack {
                                Image(systemName: category.icon)
                                    .foregroundColor(.accentColor)
                                    .frame(width: 24)
                                Text(category.displayName)
                                    .foregroundColor(.primary)
                                Spacer()
                                if selectedCategory == category {
                                    Image(systemName: "checkmark")
                                        .foregroundColor(.accentColor)
                                }
                            }
                        }
                    }
                }

                // 自由記述
                Section(header: Text("詳細")) {
                    if #available(iOS 16.0, *) {
                        TextField("ご意見・ご要望をお聞かせください", text: $feedbackText, axis: .vertical)
                            .lineLimit(5...10)
                    } else {
                        TextEditor(text: $feedbackText)
                            .frame(minHeight: 120)
                    }
                }

                // デバイス情報（自動付加の説明）
                Section(footer: Text("送信時にデバイス情報（iOSバージョン、アプリバージョン、デバイスモデル）が自動的に付加されます。")) {
                    EmptyView()
                }
            }
            .navigationTitle("フィードバック")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("キャンセル") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("送信") {
                        sendFeedback()
                    }
                    .disabled(feedbackText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
            .sheet(isPresented: $showingMailComposer) {
                FeedbackMailComposerView(
                    recipients: [supportEmail],
                    subject: feedbackMailSubject,
                    messageBody: feedbackMailBody
                )
            }
            .alert("メールを送信できません", isPresented: $showingMailAlert) {
                Button("OK", role: .cancel) { }
            } message: {
                Text("メールアプリが設定されていません。\n\n\(supportEmail)\n\nこちらのアドレスに直接お問い合わせください。")
            }
        }
    }

    // MARK: - Computed Properties

    private var feedbackMailSubject: String {
        "[最期の砂時計] フィードバック - \(selectedCategory.displayName)"
    }

    private var feedbackMailBody: String {
        """
        カテゴリ: \(selectedCategory.displayName)

        \(feedbackText)

        -----
        アプリバージョン: \(appVersion)
        デバイス: \(deviceModel)
        iOS: \(UIDevice.current.systemVersion)
        """
    }

    private var appVersion: String {
        let version = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "Unknown"
        let build = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "Unknown"
        return "\(version) (\(build))"
    }

    private var deviceModel: String {
        var systemInfo = utsname()
        uname(&systemInfo)
        let identifier = withUnsafePointer(to: &systemInfo.machine) {
            $0.withMemoryRebound(to: CChar.self, capacity: 1) {
                String(validatingUTF8: $0)
            }
        }
        return identifier ?? UIDevice.current.model
    }

    // MARK: - Actions

    private func sendFeedback() {
        if MFMailComposeViewController.canSendMail() {
            showingMailComposer = true
        } else {
            // mailto: URLScheme フォールバック
            var mailtoAllowed = CharacterSet.urlQueryAllowed
            mailtoAllowed.remove(charactersIn: "&=")
            let subject = feedbackMailSubject.addingPercentEncoding(withAllowedCharacters: mailtoAllowed) ?? ""
            let body = feedbackMailBody.addingPercentEncoding(withAllowedCharacters: mailtoAllowed) ?? ""
            let mailtoString = "mailto:\(supportEmail)?subject=\(subject)&body=\(body)"

            if let mailtoURL = URL(string: mailtoString),
               UIApplication.shared.canOpenURL(mailtoURL) {
                UIApplication.shared.open(mailtoURL)
                dismiss()
            } else {
                showingMailAlert = true
            }
        }
    }
}

// MARK: - FeedbackMailComposerView

/// MFMailComposeViewControllerのSwiftUIラッパー（フィードバック専用）
struct FeedbackMailComposerView: UIViewControllerRepresentable {
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
        let parent: FeedbackMailComposerView

        init(_ parent: FeedbackMailComposerView) {
            self.parent = parent
        }

        func mailComposeController(
            _ controller: MFMailComposeViewController,
            didFinishWith result: MFMailComposeResult,
            error: Error?
        ) {
            parent.dismiss()
        }
    }
}
