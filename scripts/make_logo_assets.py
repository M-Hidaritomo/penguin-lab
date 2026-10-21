"""会社ロゴ（docs/design/logo/penguinlab-logo.png）から HP 用の画像を作る。ローカルで手動実行する（CI では動かさない）。

使い方:
    python scripts/make_logo_assets.py ../../docs/design/logo/penguinlab-logo.png public ../../docs/design/sns/2026-10-21-icon-logo.png

出力:
  public/logo.png        ヘッダー用。本体だけ（紙の余白を落とし、紙の地色を #F9F8F7 に置き換え）。高さ 240px（PC 表示 80px の 3 倍密度）
  public/favicon.svg     ペンギンの頭（冠羽とくちばし）を正方形にして PNG を data URI で埋め込んだ SVG
  <第3引数>              SNS アイコン用の正方形 PNG（円形に切っても欠けない余白つき）。HP には入れない
縮小のみで拡大はしない。
"""
import base64
import io
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

BG = (0xF9, 0xF8, 0xF7)
HEADER_H = 240
FAVICON_BOX = (585, 200, 955, 420)  # 元画像上の頭の部分（文字は含めない）
FAVICON_PX = 64
CUT_Y, BEAK_X = 396, (725, 815)
ICON_SIDE = 1000


def flatten(img: Image.Image, paper) -> Image.Image:
    """紙の色に近いほど BG に、離れるほど元の色に（やわらかく）置き換える。"""
    diff = ImageChops.difference(img, Image.new("RGB", img.size, paper))
    r, g, b = diff.split()
    d = ImageChops.lighter(ImageChops.lighter(r, g), b)
    w = d.point(lambda v: max(0, min(255, round((v - 6) * 255 / 18))))
    return Image.composite(img, Image.new("RGB", img.size, BG), w)


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    src, pub, icon = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    pub.mkdir(parents=True, exist_ok=True)
    img = Image.open(src).convert("RGB")
    paper = tuple(round(v) for v in ImageStat.Stat(img.crop((0, 0, 200, 200))).median)
    flat = flatten(img, paper)
    ink = ImageChops.difference(flat, Image.new("RGB", img.size, BG)).convert("L").point(lambda v: 255 if v > 24 else 0)
    x0, y0, x1, y1 = ink.getbbox()
    pad = 6
    body = flat.crop((x0 - pad, y0 - pad, x1 + pad, y1 + pad))
    print("ロゴ本体", body.size)

    h = HEADER_H
    logo = body.resize((round(body.width * h / body.height), h), Image.LANCZOS)
    logo.save(pub / "logo.png", optimize=True)
    print("logo.png", logo.size)

    head = flat.crop(FAVICON_BOX)
    # 頭の下に文字の上端（ぺ・ぎ）が少し入るので、くちばし以外の y>=CUT_Y は紙の色にする
    x_off, y_off = FAVICON_BOX[0], FAVICON_BOX[1]
    for yy in range(CUT_Y - y_off, head.height):
        for xx in range(head.width):
            if not (BEAK_X[0] <= xx + x_off <= BEAK_X[1]):
                head.putpixel((xx, yy), BG)
    side = max(head.size) + 40
    sq = Image.new("RGB", (side, side), BG)
    sq.paste(head, ((side - head.width) // 2, (side - head.height) // 2))
    fav = sq.resize((FAVICON_PX, FAVICON_PX), Image.LANCZOS)
    buf = io.BytesIO()
    fav.save(buf, "PNG", optimize=True)
    uri = base64.b64encode(buf.getvalue()).decode()
    (pub / "favicon.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {FAVICON_PX} {FAVICON_PX}">'
        f'<image width="{FAVICON_PX}" height="{FAVICON_PX}" href="data:image/png;base64,{uri}"/></svg>\n',
        encoding="utf-8")

    # SNS アイコン: 本体の四隅が円（直径 ICON_SIDE）に収まる大きさの正方形
    cx, cy = body.width / 2, body.height / 2
    half_diag = (cx ** 2 + cy ** 2) ** 0.5
    assert 2 * half_diag + 20 <= ICON_SIDE, "ロゴが円からはみ出します"
    canvas = Image.new("RGB", (ICON_SIDE, ICON_SIDE), BG)
    canvas.paste(body, ((ICON_SIDE - body.width) // 2, (ICON_SIDE - body.height) // 2))
    icon.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(icon, optimize=True)
    print("icon", canvas.size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
