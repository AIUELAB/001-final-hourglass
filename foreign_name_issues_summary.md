# Foreign Name Display Issues - Summary Report

## Statistics

- Total Records: 5558
- Records with Alphabet: 198
- Total Issues Found: 266

### Issue Breakdown

- Pure Alphabet Names: 41
- Mixed Format (with parentheses): 119
- Incorrect Katakana: 10
- Japanese with English Display: 96
- Duplicate Persons: 380 groups (840 total IDs)

## Key Findings

### Duplicate Persons Requiring Merge

- **G-Dragon**: 3 IDs ['P000010', 'P030070', 'P030070']
  - Displays: G-DRAGON, G-Dragon, G-Dragon
- **RM**: 3 IDs ['P000023', 'P030068', 'P030068']
  - Displays: RM (BTS), RM (BTS), RM (BTS)
- **IU**: 3 IDs ['P000149', 'P030071', 'P030071']
  - Displays: アイユー, アイユー, アイユー
- **Atal Bihari Vajpayee**: 2 IDs ['P000165', 'P000165']
  - Displays: アタル・ビハーリー・ヴァージペーイー, アタル・ビハーリー・ヴァージペーイー
- **Adam Smith**: 3 IDs ['P000166', 'P015983', 'P015983']
  - Displays: アダム・スミス, アダム・スミス, アダム・スミス
- **Amanda Gorman**: 3 IDs ['P000175', 'P030131', 'P030131']
  - Displays: アマンダ・ゴーマン, アマンダ・ゴーマン, アマンダ・ゴーマン
- **Anthony Albanese**: 3 IDs ['P000221', 'P030041', 'P030041']
  - Displays: アンソニー・アルバニージー, アンソニー・アルバニージー, アンソニー・アルバニージー
- **Andrew Ng**: 3 IDs ['P000233', 'P015830', 'P015830']
  - Displays: アンドリュー・ング, アンドリュー・ン, アンドリュー・ン
- **Andrea Ghez**: 3 IDs ['P000235', 'P015728', 'P015728']
  - Displays: アンドレア・ゲズ, アンドレア・ゲズ, アンドレア・ゲズ
- **Immanuel Kant**: 3 IDs ['P000271', 'P015984', 'P015984']
  - Displays: イマニュエル・カント, イマヌエル・カント, イマヌエル・カント

### K-pop Artists Using Katakana (Should Use Alphabet)

- P000022: サイ → PSY
- P000550: サイ → PSY
- P015900: サイ → PSY
- P015900: サイ → PSY
- P015890: セブンティーン → SEVENTEEN
- P015890: セブンティーン → SEVENTEEN
- P015896: アイヴ → IVE
- P015896: アイヴ → IVE
- P015897: ル・セラフィム → LE SSERAFIM
- P015897: ル・セラフィム → LE SSERAFIM

### Japanese Artists Using English Display (96 cases)

- P000001: Ado → Use Japanese: Ado
- P000003: Ayase (YOASOBI) → Use Japanese: Ayase
- P000005: DAIGO → Use Japanese: DAIGO
- P000006: DJ LOVE (SEKAI NO OWARI) → Use Japanese: DJ LOVE
- P000007: Eve → Use Japanese: Eve
- P000008: Fukase (SEKAI NO OWARI) → Use Japanese: Fukase
- P000011: GACKT → Use Japanese: GACKT
- P000012: HEATH (X JAPAN) → Use Japanese: HEATH
- P000013: HIKAKIN → Use Japanese: HIKAKIN
- P000014: HISASHI (GLAY) → Use Japanese: HISASHI

## Recommendations

1. **Merge Duplicate Persons**: Consolidate duplicate IDs for same persons
2. **K-pop Convention**: Use original alphabet names for all K-pop artists
3. **Japanese Artists**: Use person_name_ja when available
4. **Western Artists**: Convert to established katakana forms
5. **Implement Wikipedia Authority**: Use Wikipedia Japan page titles as canonical source
