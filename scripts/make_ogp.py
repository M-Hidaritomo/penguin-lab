"""OGP 画像（public/ogp.png, 1200x630）を作る。ローカルで手動実行する（CI では動かさない）。

使い方:
    python scripts/make_ogp.py <元画像のパス> public/ogp.png

構図は docs/design/website-design.md 6章。左に文字、右にペンタ。
ペンタは crop_members.py と同じ処理で元画像から切り出す（拡大しない）。
HTML を一時フォルダに作り、ヘッドレスの Chrome / Edge でスクリーンショットを撮る。
新しいパッケージは不要（Pillow と、入っているブラウザだけ）。
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import crop_members as cm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "node_modules/@fontsource/zen-maru-gothic/files"
BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]
W, H = 1200, 630
MAX_BYTES = 300 * 1024

HTML = """<!doctype html><meta charset="utf-8"><style>
@font-face{font-family:Z;font-weight:700;src:url('%(f)s/zen-maru-gothic-japanese-700-normal.woff2')}
@font-face{font-family:ZL;font-weight:700;src:url('%(f)s/zen-maru-gothic-latin-700-normal.woff2')}
html,body{margin:0;width:1200px;height:630px;background:#f9f8f7;color:#4a3728;font-family:ZL,Z,sans-serif;font-weight:700;overflow:hidden}
.t1{position:absolute;left:80px;top:112px;font-size:96px;line-height:120px;letter-spacing:.02em}
.rule{position:absolute;left:80px;top:226px;width:160px;height:4px;background:#3f5a78;border-radius:2px}
.t2{position:absolute;left:80px;top:258px;font-size:56px;line-height:72px}
.t3{position:absolute;left:80px;top:344px;font-size:32px;line-height:44px;color:#6e5a4c}
.paws{position:absolute;left:84px;top:500px;display:flex;gap:34px;color:#ddd3c4}
img{position:absolute;right:%(r)dpx;bottom:%(b)dpx}
</style>
<div class="t1">ぺんぎんラボ</div><div class="rule"></div>
<div class="t2">日常の面倒をなくす</div>
<div class="t3">小さなWebアプリをつくる小さなチーム</div>
<div class="paws">%(paws)s</div>
<img src="%(img)s">
"""
PAW = ('<svg width="30" height="30" viewBox="0 0 24 24"><g fill="currentColor"><ellipse cx="12" cy="16" rx="5.5" ry="4.5"/>'
       '<circle cx="4.5" cy="10.5" r="2.4"/><circle cx="9" cy="5.5" r="2.4"/><circle cx="15" cy="5.5" r="2.4"/>'
       '<circle cx="19.5" cy="10.5" r="2.4"/></g></svg>')


def crop_penta(sheet: Image.Image) -> Image.Image:
    ref = cm.paper_color(sheet)
    info = cm.locate(sheet, ref)["penta"]
    card = cm.make_card(sheet, ref, info)
    x0, y0, x1, y1 = info["bbox"]
    # 400 角のカードから、キャラの範囲だけ（拡大なし）を取り出す
    left = (cm.SIZE - (x1 - x0)) // 2
    top = cm.SIZE - cm.FOOT_MARGIN - (y1 - y0)
    return card.crop((left - 8, top - 8, left + (x1 - x0) + 8, top + (y1 - y0) + 8))


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    sheet = Image.open(sys.argv[1]).convert("RGB")
    penta = crop_penta(sheet)
    browser = next((b for b in BROWSERS if Path(b).exists()), None)
    if not browser:
        print("Chrome / Edge が見つかりません")
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        penta.save(tmp / "penta.png")
        html = HTML % {"f": (FONTS.as_uri()), "img": "penta.png", "r": 140, "b": 64, "paws": PAW * 3}
        (tmp / "ogp.html").write_text(html, encoding="utf-8")
        out = Path(sys.argv[2]).resolve()
        subprocess.run([browser, "--headless", "--disable-gpu", "--hide-scrollbars",
                        f"--window-size={W},{H}", f"--screenshot={out}", (tmp / "ogp.html").as_uri()],
                       check=True, capture_output=True)
    img = Image.open(sys.argv[2])
    size = Path(sys.argv[2]).stat().st_size
    print(f"ペンタ {penta.size}（元の大きさのまま） ogp {img.size} {size // 1024}KB")
    if img.size != (W, H) or size > MAX_BYTES:
        print("検証に失敗")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
