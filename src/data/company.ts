export const mission = {
  title: '日常の面倒をなくす',
  body: '人が毎日「めんどうだな」と感じていることを、小さなWebアプリで解決します。',
};

export type Principle = { no: number; title: string; body: string };

export const principles: readonly Principle[] = [
  { no: 1, title: '面倒を見つける', body: '機能の前に「誰のどんな面倒か」を言葉にします。' },
  { no: 2, title: '小さく出す', body: '完璧より公開。まず出して、反応から学びます。' },
  { no: 3, title: 'お金をかけない', body: '無料枠の中で工夫します。' },
  { no: 4, title: '正直に発信する', body: '誇張しません。うまくいかなかったことも学びとして共有します。' },
];
