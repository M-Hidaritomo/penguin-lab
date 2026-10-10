"""社員イラストの切り出し。ローカルで手動実行する（CI では動かさない）。

使い方:
    python -m pip install -r scripts/requirements.txt
    python scripts/crop_members.py <members-sheet.png のパス> public/members
"""
import sys
from pathlib import Path

from PIL import Image

EXPECTED_SIZE = (1490, 1055)
BG = (0xF9, 0xF8, 0xF7)
THRESHOLD = 209  # 背景(249)から40以上暗い画素を輪郭として扱う
SIZE = 400
FOOT_MARGIN = 18
ROWS = [(0, 480), (520, 925)]
IDS = [
    ["piyo", "penta", "mike", "moko"],
    ["kerota", "hime", "poko", "konko"],
]
MAX_BYTES = 200 * 1024


def ink_bbox(cell: Image.Image):
    mask = cell.convert("L").point(lambda v: 255 if v < THRESHOLD else 0)
    return mask.getbbox()


def flatten_background(img: Image.Image, tol: int = 6) -> Image.Image:
    """四隅（外周）から連結した「背景に近い色」だけを完全な BG に置き換える。
    キャラクター内部の白（毛など）は輪郭線で囲まれているので塗りつぶされない。"""
    img = img.copy()
    px = img.load()
    w, h = img.size

    def near(c):
        return all(abs(c[i] - BG[i]) <= tol for i in range(3))

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


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    src, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    sheet = Image.open(src).convert("RGB")
    if sheet.size != EXPECTED_SIZE:
        print(f"画像サイズが {EXPECTED_SIZE} ではありません: {sheet.size}")
        return 1
    w = sheet.width
    out_dir.mkdir(parents=True, exist_ok=True)
    problems = []

    for r, (y0, y1) in enumerate(ROWS):
        for c, member_id in enumerate(IDS[r]):
            x0, x1 = round(c * w / 4), round((c + 1) * w / 4)
            cell = sheet.crop((x0, y0, x1, y1))
            bbox = ink_bbox(cell)
            if bbox is None:
                problems.append(f"{member_id}: 輪郭が見つかりません")
                continue
            # 窓（セル座標）。横は bbox の中心、縦は足元の18px下を下端にする
            cx = (bbox[0] + bbox[2]) // 2
            wx0 = cx - SIZE // 2
            wy1 = bbox[3] + FOOT_MARGIN
            wy0 = wy1 - SIZE
            # 窓とセルの重なり部分だけを貼る
            ox0, oy0 = max(wx0, 0), max(wy0, 0)
            ox1, oy1 = min(wx0 + SIZE, cell.width), min(wy1, cell.height)
            canvas = Image.new("RGB", (SIZE, SIZE), BG)
            canvas.paste(cell.crop((ox0, oy0, ox1, oy1)), (ox0 - wx0, oy0 - wy0))
            canvas = flatten_background(canvas)
            path = out_dir / f"{member_id}.webp"
            canvas.save(path, "WEBP", lossless=True, method=6)

    # 検証
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
            if img.getpixel((0, 0)) != BG or img.getpixel((SIZE - 1, SIZE - 1)) != BG:
                problems.append(f"{member_id}: 四隅が背景色と一致しません")
            top = img.crop((0, 0, SIZE, 10))
            if ink_bbox(top) is not None:
                problems.append(f"{member_id}: 上端が切れています")
            print(f"{member_id}: {img.size} {path.stat().st_size // 1024}KB")

    if problems:
        print("検証に失敗:")
        for p in problems:
            print(" -", p)
        return 1
    print("OK: 8枚そろいました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
