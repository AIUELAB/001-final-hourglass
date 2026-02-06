import Foundation

// MARK: - 地域
enum Region: String, CaseIterable {
    case hokkaido
    case tohoku
    case kanto
    case chubu
    case kinki
    case chugoku
    case shikoku
    case kyushu
}

// MARK: - 都道府県
enum Prefecture: String, CaseIterable {
    case hokkaido
    case aomori
    case iwate
    case miyagi
    case akita
    case yamagata
    case fukushima
    case ibaraki
    case tochigi
    case gunma
    case saitama
    case chiba
    case tokyo
    case kanagawa
    case niigata
    case toyama
    case ishikawa
    case fukui
    case yamanashi
    case nagano
    case gifu
    case shizuoka
    case aichi
    case mie
    case shiga
    case kyoto
    case osaka
    case hyogo
    case nara
    case wakayama
    case tottori
    case shimane
    case okayama
    case hiroshima
    case yamaguchi
    case tokushima
    case kagawa
    case ehime
    case kochi
    case fukuoka
    case saga
    case nagasaki
    case kumamoto
    case oita
    case miyazaki
    case kagoshima
    case okinawa

    var name: String {
        switch self {
        case .hokkaido: return "北海道"
        case .aomori: return "青森県"
        case .iwate: return "岩手県"
        case .miyagi: return "宮城県"
        case .akita: return "秋田県"
        case .yamagata: return "山形県"
        case .fukushima: return "福島県"
        case .ibaraki: return "茨城県"
        case .tochigi: return "栃木県"
        case .gunma: return "群馬県"
        case .saitama: return "埼玉県"
        case .chiba: return "千葉県"
        case .tokyo: return "東京都"
        case .kanagawa: return "神奈川県"
        case .niigata: return "新潟県"
        case .toyama: return "富山県"
        case .ishikawa: return "石川県"
        case .fukui: return "福井県"
        case .yamanashi: return "山梨県"
        case .nagano: return "長野県"
        case .gifu: return "岐阜県"
        case .shizuoka: return "静岡県"
        case .aichi: return "愛知県"
        case .mie: return "三重県"
        case .shiga: return "滋賀県"
        case .kyoto: return "京都府"
        case .osaka: return "大阪府"
        case .hyogo: return "兵庫県"
        case .nara: return "奈良県"
        case .wakayama: return "和歌山県"
        case .tottori: return "鳥取県"
        case .shimane: return "島根県"
        case .okayama: return "岡山県"
        case .hiroshima: return "広島県"
        case .yamaguchi: return "山口県"
        case .tokushima: return "徳島県"
        case .kagawa: return "香川県"
        case .ehime: return "愛媛県"
        case .kochi: return "高知県"
        case .fukuoka: return "福岡県"
        case .saga: return "佐賀県"
        case .nagasaki: return "長崎県"
        case .kumamoto: return "熊本県"
        case .oita: return "大分県"
        case .miyazaki: return "宮崎県"
        case .kagoshima: return "鹿児島県"
        case .okinawa: return "沖縄県"
        }
    }

    var region: Region {
        switch self {
        case .hokkaido:
            return .hokkaido
        case .aomori, .iwate, .miyagi, .akita, .yamagata, .fukushima:
            return .tohoku
        case .ibaraki, .tochigi, .gunma, .saitama, .chiba, .tokyo, .kanagawa:
            return .kanto
        case .niigata, .toyama, .ishikawa, .fukui, .yamanashi, .nagano, .gifu, .shizuoka, .aichi:
            return .chubu
        case .mie, .shiga, .kyoto, .osaka, .hyogo, .nara, .wakayama:
            return .kinki
        case .tottori, .shimane, .okayama, .hiroshima, .yamaguchi:
            return .chugoku
        case .tokushima, .kagawa, .ehime, .kochi:
            return .shikoku
        case .fukuoka, .saga, .nagasaki, .kumamoto, .oita, .miyazaki, .kagoshima, .okinawa:
            return .kyushu
        }
    }

    var code: String {
        switch self {
        case .hokkaido: return "01"
        case .aomori: return "02"
        case .iwate: return "03"
        case .miyagi: return "04"
        case .akita: return "05"
        case .yamagata: return "06"
        case .fukushima: return "07"
        case .ibaraki: return "08"
        case .tochigi: return "09"
        case .gunma: return "10"
        case .saitama: return "11"
        case .chiba: return "12"
        case .tokyo: return "13"
        case .kanagawa: return "14"
        case .niigata: return "15"
        case .toyama: return "16"
        case .ishikawa: return "17"
        case .fukui: return "18"
        case .yamanashi: return "19"
        case .nagano: return "20"
        case .gifu: return "21"
        case .shizuoka: return "22"
        case .aichi: return "23"
        case .mie: return "24"
        case .shiga: return "25"
        case .kyoto: return "26"
        case .osaka: return "27"
        case .hyogo: return "28"
        case .nara: return "29"
        case .wakayama: return "30"
        case .tottori: return "31"
        case .shimane: return "32"
        case .okayama: return "33"
        case .hiroshima: return "34"
        case .yamaguchi: return "35"
        case .tokushima: return "36"
        case .kagawa: return "37"
        case .ehime: return "38"
        case .kochi: return "39"
        case .fukuoka: return "40"
        case .saga: return "41"
        case .nagasaki: return "42"
        case .kumamoto: return "43"
        case .oita: return "44"
        case .miyazaki: return "45"
        case .kagoshima: return "46"
        case .okinawa: return "47"
        }
    }

    // コードから都道府県を取得
    static func fromCode(_ code: String) -> Prefecture? {
        return Prefecture.allCases.first { $0.code == code }
    }

    // rawValueから都道府県を取得
    static func fromRawValue(_ rawValue: String) -> Prefecture? {
        return Prefecture(rawValue: rawValue)
    }

    // periphery:ignore - Future use for prefecture selection
    // 全都道府県リスト（PrefecturePickerViewとの互換性のため）
    static var allPrefectures: [Prefecture] {
        return Prefecture.allCases
    }
}
