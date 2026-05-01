# valorant-scraper

[thespike.gg](https://www.thespike.gg) から VALORANT の試合データを取得するスクレイパーです。

## 取得できるデータ

| データ種別 | 内容 |
|-----------|------|
| マップスコア | 各マップのチーム名・ラウンド数・勝敗 |
| 選手統計 | Rating / ACS / K・D・A / +/- / KD / KAST / ADR / HS% / FBSR / FB / FD（全マップ＋マップ別） |
| 対面データ | 選手同士のキル数（マップ別・全マップ合算） |
| パフォーマンス | 2K / 3K / 4K / 5K、クラッチ状況（1v1〜1v5）（マップ別・全マップ合算） |
| ラウンドエコノミー | チーム単位・ラウンド別の使用金額 |

取得結果は `output/{match_id}.json` に保存されます。

---

## セットアップ

### 必要環境

- Python 3.11 以上

### インストール

```bash
pip install -r requirements.txt
playwright install chromium
```

> `playwright install chromium` を忘れると初回起動時にエラーになります。

---

## 使い方

### 1. URL で1試合取得

```bash
python main.py --url "https://www.thespike.gg/jp/match/detonation-focusme-varrel/143054"
```

### 2. 試合 ID を直接指定

```bash
# 1試合
python main.py --match-ids 143054

# 複数試合（スペース区切り）
python main.py --match-ids 143054 143055 143056
```

### 3. イベント単位で一括取得

```bash
# 終了済み試合のみ（デフォルト）
python main.py --event-id 4043

# 未開催試合も含める
python main.py --event-id 4043 --all
```

### オプション一覧

| オプション | 説明 |
|-----------|------|
| `--url` | 試合ページの URL（1試合） |
| `--match-ids` | 試合 ID（複数スペース区切り可） |
| `--event-id` | イベント ID（グループ＋プレーオフの全試合を取得） |
| `--all` | `--event-id` と併用。未開催試合も対象にする |
| `--force` | 既存ファイルを上書き（デフォルトはスキップ） |

---

## イベント ID の調べ方

対象イベントの URL 末尾の数字がイベント ID です。

```
https://www.thespike.gg/jp/event/valorant-champions-tour-2026-pacific-stage-1/4043
                                                                                ^^^^
                                                                            event_id = 4043
```

### 主なイベント ID（例）

| イベント | event_id |
|---------|---------|
| VCT 2026 Pacific Stage 1 | `4043` |

---

## 出力ファイルの構造

`output/{match_id}.json` に以下の形式で保存されます。

```json
{
  "match_id": "143054",
  "url": "https://www.thespike.gg/jp/match/detonation-focusme-varrel/143054",
  "team1": "DetonatioN FocusMe",
  "team1_score": 2,
  "team2": "VARREL",
  "team2_score": 1,
  "date": "2026-04-25T11:27:00+00:00",
  "tournament": "VALORANT Champions Tour 2026 - Pacific Stage 1",
  "maps": [
    {
      "map_name": "Lotus",
      "team1_name": "VARREL",
      "team1_rounds": 11,
      "team2_name": "DetonatioN FocusMe",
      "team2_rounds": 13,
      "winner": "DetonatioN FocusMe"
    }
  ],
  "player_stats": [
    {
      "player_id": 8173,
      "player_name": "Meiy",
      "team_name": "DetonatioN FocusMe",
      "map": "all",
      "rating": 1.35,
      "acs": 289.0,
      "kills": 68,
      "deaths": 50,
      "assists": 10,
      "plus_minus": 18,
      "kd": 1.36,
      "kast": 72.46,
      "adr": 172.2,
      "hs_pct": 22.0,
      "fbsr": 72.73,
      "fb": 16,
      "fd": 6,
      "econ_rating": 73.0,
      "total_spent": 0
    }
  ],
  "head_to_head": [
    {
      "map_name": "all",
      "attacker_name": "Meiy",
      "victim_name": "C1nder",
      "kills": 12
    }
  ],
  "performances": [
    {
      "player_name": "Meiy",
      "team_name": "DetonatioN FocusMe",
      "map": "all",
      "k2": 14,
      "k3": 3,
      "k4": 3,
      "k5": 1,
      "clutch_1v1_won": 0,
      "clutch_1v1_lost": 0,
      "clutch_1v2_won": 1,
      "clutch_1v2_lost": 0
    }
  ],
  "round_economy": [
    {
      "map_name": "Lotus",
      "team_name": "DetonatioN FocusMe",
      "rounds": {
        "1": 3750,
        "2": 2100,
        "3": 21200
      }
    }
  ]
}
```

---

## プロジェクト構成

```
valorant-search/
├── scraper/
│   ├── api_client.py      # API リクエスト・データパース
│   ├── models.py          # データモデル（dataclass）
│   ├── storage.py         # JSON 保存・スキップ判定
│   ├── discover.py        # API エンドポイント探索（キャッシュ付き）
│   └── logger.py          # ログ設定
├── output/                # 取得データ（.gitignore 対象）
├── logs/                  # ログファイル（.gitignore 対象）
├── cache/                 # API キャッシュ（.gitignore 対象）
├── main.py                # CLI エントリポイント
└── requirements.txt
```

---

## 動作の仕組み

1. `GET https://api.thespike.gg/match/{match_id}` でチーム・選手情報を取得
2. `GET https://api.thespike.gg/match/{match_id}/stats` で全統計を取得
3. 2つのレスポンスをパースして JSON に保存

`--event-id` 使用時は先に `GET https://api.thespike.gg/events/{event_id}` で試合 ID 一覧を取得し、終了済み試合を順番に処理します。試合間には 3 秒のインターバルを設けています。

---

## 注意事項

- 取得対象は公開されている試合データのみです（ログイン不要）
- 試合データが存在しない場合（404）はスキップされます
- 既存ファイルは `--force` を付けない限り上書きされません
