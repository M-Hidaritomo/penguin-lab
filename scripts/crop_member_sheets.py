"""キャラクターシート（docs/design/characters/<id>-sheet.png）の「まえ」全身を
public/members/<id>.webp（400x400）に切り出す。ローカルで手動実行する（CI では動かさない）。

使い方:
    python scripts/crop_member_sheets.py ../../docs/design/characters public/members

処理（crop_members.py の部品を使う）:
  1. シート左上の「まえ」の範囲（SEARCH の範囲）で、紙の色との差が大きい画素の連結成分を求め、最大のものを本体とする
     （ハート・きらきら・名前札・手書き文字は別の成分なので落ちる）
  2. 本体の範囲（穴埋め・少し膨張）だけを残し、足元を基準に 400x400 の窓へ貼る（拡大縮小なし）
  3. 外周の紙（地色は #F9F8F7 より黄色い）を #F9F8F7 に置き換える
"""
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageStat

sys.path.insert(0, str(Path(__file__).parent))
import crop_members as cm  # noqa: E402

IDS = ["penta", "konko", "poko", "hime", "koko", "moko", "mike", "piyo", "holo", "kumaji"]
SEARCH = (0, 80, 345, 385)  # 1段目いちばん左「まえ」の範囲（見出し帯は y<80、隣の「よこ」は x>345）  札や記号は別の成分になり、最大の成分だけを残す
THRESHOLD = 14
SCALE = 1.4  # 「拡大しない」方針の例外: 新版シートは1体が約200pxと小さいため、全員同じ率で LANCZOS 拡大（オーナー判断 2026-10-21）
FOOT_MARGIN = 42  # 拡大後の足元から下端まで。一番背の高いキャラ（約230px→322px）の上に約36pxの余白が残る
GROW = 5  # 毛先のやわらかい輪郭を残すための膨張（画素）


def paper_of(sheet: Image.Image):
    """紙の地色。枠の外側の帯（下端の余白）の中央値。"""
    band = sheet.crop((0, sheet.height - 20, sheet.width, sheet.height))
    return tuple(ImageStat.Stat(band).median)


def body_mask(region: Image.Image, ref) -> Image.Image:
    mask = cm.ink_mask(region, ref, THRESHOLD)
    labels, sw, sh, n = cm.components(mask, scale=2, bridge=3)
    sizes = {}
    for row in labels:
        for l in row:
            if l:
                sizes[l] = sizes.get(l, 0) + 1
    big = max(sizes, key=sizes.get)
    lm = Image.new("L", (sw, sh), 0)
    lp = lm.load()
    for y in range(sh):
        for x in range(sw):
            if labels[y][x] == big:
                lp[x, y] = 255
    lm = cm.fill_holes(lm).resize(region.size, Image.NEAREST)
    x0, y0, x1, y1 = lm.getbbox()
    if min(x0, y0, region.width - x1, region.height - y1) < 3:
        raise SystemExit(f"本体が検索範囲の端に接しています {lm.getbbox()}（SEARCH を見直してください）")
    return lm.filter(ImageFilter.MaxFilter(GROW * 2 + 1))


def make(sheet: Image.Image):
    ref = paper_of(sheet)
    region = sheet.crop(SEARCH)
    own = body_mask(region, ref)
    region = sheet.crop(SEARCH)
    ink = cm.ink_mask(region, ref, THRESHOLD)
    x0, y0, x1, y1 = ImageChops.multiply(own.filter(ImageFilter.MinFilter(GROW * 2 + 1)), ink).getbbox()
    win = round(cm.SIZE / SCALE)
    wx0 = (x0 + x1) // 2 - win // 2
    wy1 = y1 + round(FOOT_MARGIN / SCALE)
    wy0 = wy1 - win
    canvas = Image.new("RGB", (win, win), ref)
    own_only = Image.composite(region, Image.new("RGB", region.size, ref), own)
    canvas.paste(own_only, (-wx0, -wy0))  # 窓の外は貼られず、はみ出しは切れる
    # 紙の地色は黄色みがあるので、外周の紙を BG にしたうえで輪郭ぎわもなじませる
    out = cm.flatten_background(canvas, ref, tol=10)
    out = out.resize((cm.SIZE, cm.SIZE), Image.LANCZOS)
    return out, (x1 - x0, y1 - y0)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    src, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    problems = []
    for mid in IDS:
        sheet = Image.open(src / f"{mid}-sheet.png").convert("RGB")
        if abs(sheet.width - 1536) > 2 or abs(sheet.height - 1024) > 2:
            problems.append(f"{mid}: サイズが {sheet.size}")
            continue
        img, (w, h) = make(sheet)
        path = out_dir / f"{mid}.webp"
        img.save(path, "WEBP", lossless=True, method=6)
        corners = [img.getpixel(p) for p in [(0, 0), (399, 0), (0, 399), (399, 399)]]
        if any(c != cm.BG for c in corners):
            problems.append(f"{mid}: 四隅が背景色と一致しません {corners}")
        if path.stat().st_size > cm.MAX_BYTES:
            problems.append(f"{mid}: {path.stat().st_size} バイト（200KB超）")
        if cm.ink_mask(img.crop((0, 0, 400, 10)), cm.BG, 24).getbbox() is not None:
            problems.append(f"{mid}: 上端が切れています")
        print(f"{mid}: {path.stat().st_size // 1024}KB 元の大きさ {w}x{h}")
    for p in problems:
        print(" -", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
