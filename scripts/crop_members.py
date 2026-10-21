"""社員イラストの切り出し。ローカルで手動実行する（CI では動かさない）。

使い方:
    python -m pip install -r scripts/requirements.txt
    python scripts/crop_members.py <元画像のパス> public/members

元画像は 1536x1024、名前ラベルなし。4・3・3 の10人（2・3行目は半歩ずらし）。並びは左から右へ、上の行から:
    konko, poko, hime, koko / moko, mike, piyo / penta, holo, kumaji

処理:
  1. 紙の色（最頻色）との差が大きい画素を「描かれた部分」とし、連結成分（行同士が縦に重なるため）から 10 人の範囲を求める
  2. 各キャラの足元を基準に 400x400 の窓を決める（拡大縮小なし。10人とも足元の高さがそろう）
  3. 窓のうち、そのキャラ自身の範囲（連結成分）だけを貼る。隣のキャラは紙の色にする
  4. 外周から連結した「紙の色に近い画素」を、完全な #F9F8F7 に置き換える（キャラ内部の白は塗らない）
  5. lossless WebP で保存し、検証する
"""
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

EXPECTED_SIZE = (1536, 1024)
BG = (0xF9, 0xF8, 0xF7)  # HP の背景色
SIZE = 400
FOOT_MARGIN = 30  # 足元から窓の下端まで
INK_THRESHOLD = 16  # 紙の色から各チャンネル16以上離れていたら「描かれた部分」
FLATTEN_TOL = 6
MIN_GAP = 12  # これより狭い隙間は同じキャラとして結合
IDS = [
    ["konko", "poko", "hime", "koko"],
    ["moko", "mike", "piyo"],
    ["penta", "holo", "kumaji"],
]
MAX_BYTES = 200 * 1024


def paper_color(img: Image.Image):
    counts = img.getcolors(maxcolors=img.width * img.height)
    return max(counts)[1]


def ink_mask(img: Image.Image, ref, threshold: int = INK_THRESHOLD) -> Image.Image:
    diff = ImageChops.difference(img, Image.new("RGB", img.size, ref))
    r, g, b = diff.split()
    d = ImageChops.lighter(ImageChops.lighter(r, g), b)
    return d.point(lambda v: 255 if v >= threshold else 0)


def runs(proj, min_gap: int = 1):
    """投影（0 / 非0）から連続区間を求める。min_gap 未満の隙間は結合する。"""
    out = []
    start = None
    for i, v in enumerate(proj):
        if v > 0:
            if start is None:
                start = i
            last = i
        elif start is not None and i - last >= min_gap:
            out.append((start, last))
            start = None
    if start is not None:
        out.append((start, last))
    return out


def flatten_background(img: Image.Image, ref, tol: int = FLATTEN_TOL) -> Image.Image:
    """外周から連結した「ref に近い色」だけを完全な BG に置き換える。
    キャラクター内部の白（毛など）は塗らない。輪郭の細い切れ目から毛の白がつながって
    しまうので、まず輪郭を太らせた壁（barrier）を越えない範囲で外側を求め、
    そのあと輪郭ぎわ（3画素）まで広げる。"""
    img = img.copy()
    px = img.load()
    w, h = img.size
    barrier = ink_mask(img, ref).filter(ImageFilter.MaxFilter(7)).load()

    def near(c):
        return all(abs(c[i] - ref[i]) <= tol for i in range(3))

    outside = bytearray(w * h)
    stack = []
    for x in range(w):
        stack += [(x, 0), (x, h - 1)]
    for y in range(h):
        stack += [(0, y), (w - 1, y)]
    while stack:
        x, y = stack.pop()
        if not (0 <= x < w and 0 <= y < h) or outside[y * w + x]:
            continue
        if barrier[x, y] or not near(px[x, y]):
            continue
        outside[y * w + x] = 1
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    frontier = [(i % w, i // w) for i in range(w * h) if outside[i]]
    for _ in range(3):  # 輪郭ぎわまで広げる
        nxt = []
        for x, y in frontier:
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < w and 0 <= ny < h and not outside[ny * w + nx] and near(px[nx, ny]):
                    outside[ny * w + nx] = 1
                    nxt.append((nx, ny))
        frontier = nxt
    for i in range(w * h):
        if outside[i]:
            px[i % w, i // w] = BG
    return img


def components(mask: Image.Image, scale: int = 4, bridge: int = 3):
    """描かれた部分を縮小・膨張して連結成分に分ける（行同士が縦に重なる並びでも分けられる）。
    戻り値は (縮小座標のラベル配列, 幅, 高さ, 成分数)。"""
    w, h = mask.size
    sw, sh = w // scale, h // scale
    small = mask.resize((sw, sh), Image.BOX).point(lambda v: 255 if v > 0 else 0)
    small = small.filter(ImageFilter.MaxFilter(bridge))
    px = small.load()
    labels = [[0] * sw for _ in range(sh)]
    n = 0
    for y0 in range(sh):
        for x0 in range(sw):
            if px[x0, y0] and not labels[y0][x0]:
                n += 1
                stack = [(x0, y0)]
                while stack:
                    x, y = stack.pop()
                    if not (0 <= x < sw and 0 <= y < sh) or labels[y][x] or not px[x, y]:
                        continue
                    labels[y][x] = n
                    stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return labels, sw, sh, n


def fill_holes(m: Image.Image) -> Image.Image:
    """外周から到達できない 0 の画素（穴）を 255 にする。"""
    w, h = m.size
    px = m.load()
    seen = bytearray(w * h)
    stack = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    while stack:
        x, y = stack.pop()
        if not (0 <= x < w and 0 <= y < h) or seen[y * w + x] or px[x, y]:
            continue
        seen[y * w + x] = 1
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    out = Image.new("L", (w, h), 255)
    op = out.load()
    for y in range(h):
        for x in range(w):
            if seen[y * w + x]:
                op[x, y] = 0
    return out


def locate(sheet: Image.Image, ref):
    """10人それぞれの外接矩形（bbox）と、そのキャラだけを残すマスク（own）を返す。
    行は縦に重なることがあるため、連結成分で人を分け、重心の高さで行に振り分ける。"""
    w, h = sheet.size
    scale = 4
    mask = ink_mask(sheet, ref)
    labels, sw, sh, n = components(mask, scale)
    expected = sum(len(r) for r in IDS)
    if n != expected:
        raise SystemExit(f"キャラクターが{expected}人に分かれませんでした: {n}個")
    cy = {}
    for y in range(sh):
        for x in range(sw):
            l = labels[y][x]
            if l:
                cy.setdefault(l, []).append((x, y))
    info = {}
    for l, pts in cy.items():
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        info[l] = {"cx": sum(xs) / len(xs), "cy": sum(ys) / len(ys)}
    ordered = sorted(info, key=lambda l: info[l]["cy"])
    found = {}
    start = 0
    for r, ids in enumerate(IDS):
        row = sorted(ordered[start:start + len(ids)], key=lambda l: info[l]["cx"])
        start += len(ids)
        for member_id, l in zip(ids, row):
            lm = Image.new("L", (sw, sh), 0)
            lp = lm.load()
            for x, y in cy[l]:
                lp[x, y] = 255
            lm = fill_holes(lm)  # 毛の白など、内側の「紙に近い色」の穴も自分の範囲に含める
            own = lm.resize((w, h), Image.NEAREST)  # この成分（膨張込み）の範囲
            own_ink = ImageChops.multiply(own, mask)
            bb = own_ink.getbbox()
            found[member_id] = {"bbox": bb, "own": own}
    return found


def make_card(sheet: Image.Image, ref, info) -> Image.Image:
    x0, y0, x1, y1 = info["bbox"]
    wx0 = (x0 + x1) // 2 - SIZE // 2
    wy1 = y1 + FOOT_MARGIN
    wy0 = wy1 - SIZE
    box = (wx0, wy0, wx0 + SIZE, wy1)
    paper = Image.new("RGB", sheet.size, ref)
    own_only = Image.composite(sheet, paper, info["own"])  # 隣のキャラは紙の色にする
    canvas = Image.new("RGB", (SIZE, SIZE), ref)
    ox0, oy0 = max(wx0, 0), max(wy0, 0)
    ox1, oy1 = min(wx0 + SIZE, sheet.width), min(wy1, sheet.height)
    canvas.paste(own_only.crop((ox0, oy0, ox1, oy1)), (ox0 - wx0, oy0 - wy0))
    return flatten_background(canvas, ref)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    src, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    sheet = Image.open(src).convert("RGB")
    if sheet.size != EXPECTED_SIZE:
        print(f"画像サイズが {EXPECTED_SIZE} ではありません: {sheet.size}")
        return 1
    ref = paper_color(sheet)
    out_dir.mkdir(parents=True, exist_ok=True)
    found = locate(sheet, ref)
    problems = []

    for member_id, info in found.items():
        path = out_dir / f"{member_id}.webp"
        make_card(sheet, ref, info).save(path, "WEBP", lossless=True, method=6)

    for ids in IDS:
        for member_id in ids:
            path = out_dir / f"{member_id}.webp"
            if not path.exists():
                problems.append(f"{member_id}: ファイルがありません")
                continue
            img = Image.open(path).convert("RGB")
            if img.size != (SIZE, SIZE):
                problems.append(f"{member_id}: サイズが {img.size}")
            if path.stat().st_size > MAX_BYTES:
                problems.append(f"{member_id}: {path.stat().st_size} バイト（200KB超）")
            corners = [img.getpixel(p) for p in [(0, 0), (SIZE - 1, 0), (0, SIZE - 1), (SIZE - 1, SIZE - 1)]]
            if any(c != BG for c in corners):
                problems.append(f"{member_id}: 四隅が背景色と一致しません {corners}")
            if ink_mask(img.crop((0, 0, SIZE, 10)), BG, 24).getbbox() is not None:
                problems.append(f"{member_id}: 上端が切れています")
            x0, y0, x1, y1 = found[member_id]["bbox"]
            print(f"{member_id}: {img.size} {path.stat().st_size // 1024}KB 元の大きさ {x1 - x0}x{y1 - y0}")

    if problems:
        print("検証に失敗:")
        for p in problems:
            print(" -", p)
        return 1
    print("OK: 10枚そろいました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
