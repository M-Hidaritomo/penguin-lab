# ぺんぎんラボ 公式サイト

ぺんぎんラボの会社紹介ページ（1ページ構成）のソースです。Astro で静的に生成し、GitHub Pages で公開します。

## ローカルで動かす

```
npm ci
npm run dev        # http://localhost:4321
```

## テスト・ビルド

```
npm test           # 単体・コンポーネントテスト（ネットワークには接続しません）
npm run build      # dist/ に出力
npm run test:dist  # ビルド後の成果物の検査（事前に build が必要）
npm run check      # build と上記すべてを順に実行
```

GitHub Pages のサブパスで確認する場合：`BASE_PATH=/<リポジトリ名> npm run build && npm run preview`

## 設定とデータ

| ファイル | 内容 |
|---|---|
| `src/config.ts` | サイト名・説明・X と note の URL |
| `src/data/members.ts` | 社員紹介 |
| `src/data/products.ts` | つくっているもの（空のとき「開発中」カードを表示） |
| `src/data/company.ts` | ミッション・行動指針 |

note の URL を `src/config.ts` の `noteUrl` に入れると、ビルド時に RSS から新着5件を取得して「開発ノート」に表示します。取得に失敗した場合は前回の取得結果を表示し、ビルドは止まりません（`NOTE_FEED_OFFLINE=1` で取得せずに確認できます）。

## 公開

`main` への push と、毎日 JST 6:00 に GitHub Actions がビルドして GitHub Pages へ公開します（`.github/workflows/deploy.yml`）。

## 社員イラストの再生成

```
python -m pip install -r scripts/requirements.txt
python scripts/crop_members.py <元画像のパス> public/members
```
