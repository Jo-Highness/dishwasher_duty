# Dishwasher Duty – ユーザーガイド（日本語）

Dishwasher Duty は**誰が食洗機を片付けたか**を記録し、統計をとります。

## 1. 仕組み
食洗機のセンサー（例: Home Connect「Operation state」）を監視します。**運転中 → 終了** に変わると、
クレーム可能なサイクルが開きます。片付けた人は自分のボタンを押す（またはサービスを呼ぶ）と
クレジット **1.0** を得ます。複数人で片付けた場合は 1.0 を公平に分けます。

## 2. インストール
- **HACS:** ⋮ →（カスタムリポジトリ）→ 本リポジトリを **Integration** として追加 → ダウンロード →
  HA を再起動。
- **手動:** `custom_components/dishwasher_duty/` を `<config>/custom_components/` にコピーして再起動。
- その後（設定 → デバイスとサービス → 統合を追加 →「Dishwasher Duty」）。

## 3. 設定
- **ソースセンサー:** 食洗機の動作状態センサー。
- **「運転中」「終了」の値**（2 番目のステップ）: センサーが提供する状態の一覧から選ぶか、独自の値を
  入力します。Home Connect は `run` と `finished`（既定値）を使います。大文字・小文字は区別しません。
  不明な場合は（開発者ツール → 状態）で確認してください。
- **対象の人物:** 片付ける `person` エンティティ。
- **共同の片付け**（既定で有効）+ **コクレーム時間枠**（90 秒）。

## 4. 日々の使い方
- 片付けたら自分の**ボタン**を押す: `button.dishwasher_duty_claim_<名前>`。
- 共同で片付けた？ 各自が時間枠内にボタンを押すと 1.0 が分配されます。
- 誤って押した？ 時間枠が開いている間に `dishwasher_duty.cancel_claim` を使用。

## 5. エンティティ
- `binary_sensor.dishwasher_duty_claimable` – クレーム可能な間「on」。
- `sensor.dishwasher_duty_total_cycles` – 終了サイクル数。
- `sensor.dishwasher_duty_<名前>` – 人物ごとのクレジット（属性: 日/週/月/年）。

## 6. 統計の取得
```yaml
action: dishwasher_duty.get_statistics
data:
  start: "2026-01-01 00:00:00"
  end: "2026-12-31 23:59:59"
response_variable: stats
```
合計サイクル数、未クレームのサイクル数、人物ごと（参加回数＋クレジット）、時系列リストを返します。

## 7. 注意
- `unavailable`/`unknown`（機器の再起動など）は無視されます。*run → unavailable → finished* は 1 サイクル
  として数え、運転なしの *unavailable → finished* は数えません。
- 開いているサイクルがない場合、`dishwasher_duty.cancel_claim` はエラーを返します。
- 複数回押しても問題ありません（人物／サイクルごとに1回の貢献）。
- `dishwasher_duty.reset_statistics` は履歴を削除します（全体または個人）— 慎重に使用してください。
