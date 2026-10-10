// 実際の通信を防ぐ。呼ばれたら失敗させる（個別のテストは偽 fetch を明示的に渡す）。
globalThis.fetch = (() => {
  throw new Error('テスト中に fetch が呼ばれました（ネットワーク遮断）');
}) as typeof fetch;
