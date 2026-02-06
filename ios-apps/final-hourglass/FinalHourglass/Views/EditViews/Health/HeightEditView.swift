import SwiftUI

struct HeightEditView: View {
    @EnvironmentObject var userModel: UserModel
    @Environment(\.dismiss) var dismiss
    @State private var tempHeight: Double = 0

    var body: some View {
        NavigationView {
            ZStack {
            // 背景
            Color.black.ignoresSafeArea()

            VStack(spacing: 40) {
                // 現在の身長表示
                VStack(spacing: 16) {
                    Text("現在の身長")
                        .font(.headline)
                        .foregroundColor(.white.opacity(0.6))

                    HStack(alignment: .bottom, spacing: 4) {
                        Text("\(tempHeight, specifier: "%.1f")")
                            .font(.system(size: 48, weight: .light))
                            .foregroundColor(.white)

                        Text("cm")
                            .font(.title2)
                            .foregroundColor(.white.opacity(0.6))
                            .padding(.bottom, 8)
                    }
                }
                .padding(.top, 40)

                // スライダー
                VStack(spacing: 20) {
                    Slider(value: $tempHeight, in: 100...220, step: 0.1)
                        .accentColor(Color.skyBlue)
                        .padding(.horizontal)
                        .onChange(of: tempHeight) { _ in
                            // スライダー操作時の選択音
                            SoundManager.shared.playSelectionSound()
                        }

                    HStack {
                        Text("100cm")
                            .font(.caption)
                            .foregroundColor(.white.opacity(0.5))
                        Spacer()
                        Text("220cm")
                            .font(.caption)
                            .foregroundColor(.white.opacity(0.5))
                    }
                    .padding(.horizontal)
                }
                .padding(.horizontal)

                Spacer()
            }
        }
        .navigationTitle("身長")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarLeading) {
                Button("戻る") {
                        // タップ音
                        SoundManager.shared.playTapSound(.cancel)
                        dismiss()
                }
                .foregroundColor(Color.mysticalPurple)
            }

            ToolbarItem(placement: .navigationBarTrailing) {
                Button("保存") {
                        // タップ音
                        SoundManager.shared.playTapSound(.confirm)
                        userModel.height = tempHeight
                    userModel.saveToUserDefaults()
                    dismiss()
                }
                .foregroundColor(Color.mysticalPurple)
                .font(.system(size: 17, weight: .semibold))
            }
        }
        .onAppear {
            tempHeight = userModel.height
        }
        }
    }
}
