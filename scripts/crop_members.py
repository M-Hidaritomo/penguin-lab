"""社員イラストの切り出し。ローカルで手動実行する（CI では動かさない）。

使い方:
    python -m pip install -r scripts/requirements.txt
    python scripts/crop_members.py <元画像のパス> public/members

元画像は 1536x1024、3列x3行・名前ラベルなし。並びは左上から右へ、上の行から:
    konko, poko, hime / kerota, moko, mike / penta, piyo, holo

処理:
  1. 紙の色（最頻色）との差が大きい画素を「描かれた部分」とし、行・列の投影から 9 人の範囲を求める
  2. 各キャラの足元を基準に 400x400 の窓を決める（拡大縮小なし。8人とも足元の高さがそろう）
  3. 窓とそのキャラの持ち場（隣との境目の中央まで）の重なり部分だけを貼る
  4. 外周から連結した「紙の色に近い画素」を、完全な #F9F8F7 に置き換える（キャラ内部の白は塗らない）
  5. lossless WebP で保存し、検証する
"""
import sys
from pathlib import Path

from PIL import Image, ImageChops

EXPECTED_SIZE = (1536, 1024)
BG = (0xF9, 0xF8, 0xF7)  # HP の背景色
SIZE = 400
FOOT_MARGIN = 30  # 足元から窓の下端まで
INK_THRESHOLD = 16  # 紙の色から各チャンネル16以上離れていたら「描かれた部分」
FLATTEN_TOL = 6
MIN_GAP = 12  # これより狭い隙間は同じキャラとして結合
IDS = [
    ["konko", "poko", "hime"],
    ["kerota", "moko", "mike"],
    ["penta", "piyo", "holo"],
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
    キャラクター内部の白（毛など）は、外周から連結していなければ塗りつぶされない。"""
    img = img.copy()
    px = img.load()
    w, h = img.size

    def near(c):
        return all(abs(c[i] - ref[i]) <= tol for i in range(3))

    seen = bytearray(w * h)
    stack = []
    for x in range(w):
        stack += [(x, 0), (x, h - 1)]
    for y in range(h):
        stack += [(0, y), (w - 1, y)]
    while stack:
        x, y = stack.pop()
        if not (0 <= x < w and 0 <= y < h) or seen[y * w + x]:
            continue
        seen[y * w + x] = 1
        if not near(px[x, y]):
            continue
        px[x, y] = BG
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return img


def locate(sheet: Image.Image, ref):
    """9人それぞれの (x0, x1, y0, y1)（描かれた部分の外接矩形）と、持ち場（セル）を返す。"""
    w, h = sheet.size
    mask = ink_mask(sheet, ref)
    row_runs = runs(list(mask.resize((1, h), Image.BOX).getdata()), MIN_GAP)
    if len(row_runs) != 3:
        raise SystemExit(f"行が3つに分かれませんでした: {row_runs}")
    # 行の持ち場：隣の行との隙間の中央
    cuts_y = [0] + [(row_runs[i][1] + row_runs[i + 1][0]) // 2 for i in range(2)] + [h]
    found = {}
    for r, (ry0, ry1) in enumerate(row_runs):
        band = mask.crop((0, ry0, w, ry1 + 1))
        col_runs = runs(list(band.resize((w, 1), Image.BOX).getdata()), MIN_GAP)
        if len(col_runs) != 3:
            raise SystemExit(f"{r + 1}行目が3人に分かれませんでした: {col_runs}")
        cuts_x = [0] + [(col_runs[i][1] + col_runs[i + 1][0]) // 2 for i in range(2)] + [w]
        for c, (cx0, cx1) in enumerate(col_runs):
            bb = band.crop((cx0, 0, cx1 + 1, band.height)).getbbox()
            found[IDS[r][c]] = {
                "bbox": (cx0, ry0 + bb[1], cx1 + 1, ry0 + bb[3]),
                "cell": (cuts_x[c], cuts_y[r], cuts_x[c + 1], cuts_y[r + 1]),
            }
    return found


def make_card(sheet: Image.Image, ref, info) -> Image.Image:
    x0, y0, x1, y1 = info["bbox"]
    cx0, cy0, cx1, cy1 = info["cell"]
    wx0 = (x0 + x1) // 2 - SIZE // 2
    wy1 = y1 + FOOT_MARGIN
    wy0 = wy1 - SIZE
    ox0, oy0 = max(wx0, cx0), max(wy0, cy0)
    ox1, oy1 = min(wx0 + SIZE, cx1), min(wy1, cy1)
    canvas = Image.new("RGB", (SIZE, SIZE), ref)  # セル外は紙の色（あとで BG に置き換わる）
    canvas.paste(sheet.crop((ox0, oy0, ox1, oy1)), (ox0 - wx0, oy0 - wy0))
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
    print("OK: 9枚そろいました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
