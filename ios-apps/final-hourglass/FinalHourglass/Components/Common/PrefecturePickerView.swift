import SwiftUI

// MARK: - 都道府県選択画面
struct PrefecturePickerView: View {
    @Binding var selectedPrefecture: String
    @Binding var isPresented: Bool
    @State private var selectedRegion: Region?
    @State private var searchText = ""

    // 検索結果
    private var searchResults: [Prefecture] {
        if searchText.isEmpty {
            return []
        }
        return Prefecture.allCases.filter { prefecture in
            prefecture.name.contains(searchText)
        }
    }

    // 地域ごとの都道府県
    private func prefecturesForRegion(_ region: Region) -> [Prefecture] {
        return Prefecture.allCases.filter { $0.region == region }
    }

    var body: some View {
        NavigationView {
            ZStack {
                // 背景
                Color.black.edgesIgnoringSafeArea(.all)

                VStack(spacing: 0) {
                    // 検索バー
                    HStack {
                        Image(systemName: "magnifyingglass")
                            .foregroundColor(.gray)

                        TextField("都道府県を検索", text: $searchText)
                            .foregroundColor(.white)
                            .autocapitalization(.none)
                    }
                    .padding()
                    .background(Color.gray.opacity(0.2))
                    .cornerRadius(10)
                    .padding()

                    if !searchText.isEmpty {
                        // 検索結果
                        ScrollView {
                            VStack(spacing: 0) {
                                ForEach(searchResults, id: \.code) { prefecture in
                                    PrefectureRow(
                                        prefecture: prefecture,
                                        isSelected: selectedPrefecture == prefecture.code,
                                        action: {
                                            selectedPrefecture = prefecture.code
                                            isPresented = false
                                        }
                                    )
                                }
                            }
                        }
                    } else if selectedRegion == nil {
                        // 地域選択
                        ScrollView {
                            VStack(spacing: 12) {
                                ForEach(Region.allCases, id: \.self) { region in
                                    RegionButton(
                                        region: region,
                                        prefectureCount: prefecturesForRegion(region).count,
                                        action: {
                                            withAnimation(.easeInOut(duration: 0.3)) {
                                                selectedRegion = region
                                            }
                                        }
                                    )
                                }
                            }
                            .padding()
                        }
                    } else {
                        // 都道府県一覧
                        VStack(spacing: 0) {
                            // 地域ヘッダー
                            HStack {
                                Button(action: {
                                    withAnimation(.easeInOut(duration: 0.3)) {
                                        selectedRegion = nil
                                    }
                                }) {
                                    HStack(spacing: 5) {
                                        Image(systemName: "chevron.left")
                                        Text("戻る")
                                    }
                                    .foregroundColor(.gray)
                                }

                                Spacer()

                                Text(selectedRegion!.rawValue)
                                    .font(.headline)
                                    .foregroundColor(.white)

                                Spacer()

                                // バランスを取るための透明ボタン
                                Button("戻る") {}
                                    .opacity(0)
                                    .disabled(true)
                            }
                            .padding()
                            .background(Color.black.opacity(0.8))

                            ScrollView {
                                VStack(spacing: 0) {
                                    ForEach(prefecturesForRegion(selectedRegion!), id: \.code) { prefecture in
                                        PrefectureRow(
                                            prefecture: prefecture,
                                            isSelected: selectedPrefecture == prefecture.code,
                                            action: {
                                                selectedPrefecture = prefecture.code
                                                isPresented = false
                                            }
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
            .navigationTitle("都道府県を選択")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("閉じる") {
                        isPresented = false
                    }
                    .foregroundColor(.red)
                }
            }
        }
        .preferredColorScheme(.dark)
    }
}

// MARK: - 地域選択ボタン
struct RegionButton: View {
    let region: Region
    let prefectureCount: Int
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(region.rawValue)
                        .font(.headline)
                        .foregroundColor(.white)

                    Text("\(prefectureCount)都道府県")
                        .font(.caption)
                        .foregroundColor(.gray)
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .foregroundColor(.gray)
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color.white.opacity(0.05))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                    )
            )
        }
    }
}

// MARK: - 都道府県行
struct PrefectureRow: View {
    let prefecture: Prefecture
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                Text(prefecture.name)
                    .foregroundColor(isSelected ? .white : .gray)
                    .fontWeight(isSelected ? .medium : .regular)

                Spacer()

                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.green)
                }
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 16)
            .background(
                Rectangle()
                    .fill(isSelected ? Color.red.opacity(0.2) : Color.clear)
            )
        }

        Divider()
            .background(Color.gray.opacity(0.3))
    }
}
