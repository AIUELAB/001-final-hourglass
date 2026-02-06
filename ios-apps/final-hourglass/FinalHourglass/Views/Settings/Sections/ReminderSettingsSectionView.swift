// periphery:ignore:all - 将来使用予定のUIコンポーネント
import SwiftUI

struct ReminderSettingsSectionView: View {
    @EnvironmentObject var appStateManager: AppStateManager

    var body: some View {
        VStack(spacing: 0) {
            // リマインダー設定に変更
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    StainedGlassIcon(
                        systemName: "bell.fill",
                        backgroundColor: Color.mysticBlue.opacity(0.2),
                        borderColor: Color.mysticBlue.opacity(0.3),
                        glowColor: Color.mysticBlue
                    )

                    Text("リマインダー")
                        .foregroundColor(.white.opacity(0.85))
                        .font(.system(size: 17, weight: .regular))
                        .shadow(color: .black.opacity(0.5), radius: 1.5, x: 0, y: 1)

                    Spacer()

                    MysticalToggle(isOn: $appStateManager.reminderEnabled)
                        .onChange(of: appStateManager.reminderEnabled) { newValue in
                            if newValue {
                                appStateManager.requestNotificationPermission { granted in
                                    if granted {
                                        appStateManager.scheduleReminder()
                                    } else {
                                        appStateManager.reminderEnabled = false
                                    }
                                }
                            } else {
                                appStateManager.cancelReminder()
                            }
                        }
                }
                .padding(.horizontal, 16)
                .padding(.top, 12)

                // リマインダーが有効な場合、時刻選択を表示
                if appStateManager.reminderEnabled {
                    HStack {
                        Text("時刻")
                            .foregroundColor(.white.opacity(0.65))
                            .font(.system(size: 15))
                            .padding(.leading, 56) // アイコン分のインデント

                        Spacer()

                        DatePicker("",
                                   selection: $appStateManager.reminderTime,
                                   displayedComponents: .hourAndMinute)
                            .labelsHidden()
                            .colorScheme(.dark)
                            .accentColor(Color.mysticalPurple)
                            .onChange(of: appStateManager.reminderTime) { _ in
                                appStateManager.scheduleReminder()
                            }
                    }
                    .padding(.horizontal, 16)
                    .padding(.bottom, 12)
                    .transition(.opacity.combined(with: .move(edge: .top)))
                }
            }
            .animation(.easeInOut(duration: 0.3), value: appStateManager.reminderEnabled)
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
}
