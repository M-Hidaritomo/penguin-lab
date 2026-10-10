export type Member = {
  id: string; // 画像ファイル名と一致
  name: string;
  motif: string;
  role: string;
  tagline: string; // ひとこと
  career: string;
  image: string; // public からの相対パス（先頭スラッシュなし）
};

// 組織図順
export const members: readonly Member[] = [
  {
    id: 'konko',
    name: 'コンコ',
    motif: 'きつね',
    role: 'プロダクトマネージャー',
    tagline: '先を読む切れ者。「本当の困りごと」を聞き返す',
    career: '生活雑貨メーカーで商品企画を8年',
    image: 'members/konko.webp',
  },
  {
    id: 'poko',
    name: 'ポコ',
    motif: 'たぬき',
    role: 'テックリード',
    tagline: 'どっしり構えた懐の深い古株。動じない',
    career: 'エンジニア15年、シンプルな設計が信条',
    image: 'members/poko.webp',
  },
  {
    id: 'hime',
    name: 'ヒメ',
    motif: 'ウーパールーパー',
    role: 'デザイナー',
    tagline: 'にこにこ、でも色と余白には妥協しない',
    career: 'UI/UXデザイン6年、見やすさが専門',
    image: 'members/hime.webp',
  },
  {
    id: 'kerota',
    name: 'ケロタ',
    motif: 'かえる',
    role: 'フロントエンドエンジニア',
    tagline: '元気で手が速い',
    career: 'React / Next.js 5年',
    image: 'members/kerota.webp',
  },
  {
    id: 'moko',
    name: 'モコ',
    motif: 'ひつじ',
    role: 'バックエンドエンジニア',
    tagline: 'おっとりした慎重派。データが消えるのが怖い',
    career: 'DB設計・Supabase 5年',
    image: 'members/moko.webp',
  },
  {
    id: 'mike',
    name: 'ミケ',
    motif: 'ねこ',
    role: 'QA・レビュー担当',
    tagline: '気まぐれに見えて見逃さない',
    career: '元セキュリティ診断4年',
    image: 'members/mike.webp',
  },
  {
    id: 'penta',
    name: 'ペンタ',
    motif: 'ぺんぎん',
    role: 'SNS戦略担当',
    tagline: '会社の顔。穏やかで数字に強い',
    career: 'SNS運用代理店で企業アカウントを育成',
    image: 'members/penta.webp',
  },
  {
    id: 'piyo',
    name: 'ピヨ',
    motif: 'ひよこ',
    role: 'コンテンツ担当',
    tagline: '明るい新人。読者目線',
    career: '個人ブログ3年、分かりやすい文章が得意',
    image: 'members/piyo.webp',
  },
];
