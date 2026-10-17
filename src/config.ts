export const siteConfig = {
  siteName: 'ぺんぎんラボ',
  description: '毎日の「めんどうだな」を、小さなWebアプリで解決する小さなチームです。',
  xUrl: 'https://x.com/penguinlab_ofcl', // 空ならフッターは「X（準備中）」
  noteUrl: 'https://note.com/penguinlab_ofcl', // 空なら開発ノートは「準備中」で RSS 取得もしない
  noteRssUrl: '', // 通常は空。空なら `${noteUrl}/rss` を使う。形式が違った場合だけ入れる
} as const;
