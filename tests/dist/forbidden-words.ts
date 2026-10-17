// 紹介しないサービス名・モデル名。語そのものをソースに書かないため base64 で持つ。
const encoded = ['YXBwLVJGUA==', 'U29ubmV0', 'T3B1cw=='];

export const forbiddenWords: string[] = encoded.map((s) => Buffer.from(s, 'base64').toString('utf8'));

// キャラクターの口調（成果物に出さない）
export const toneWords = ['〜じゃ', 'ケロ！', 'メェ', 'にゃ', 'ぴよ！'];
