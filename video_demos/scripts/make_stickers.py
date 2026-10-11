"""オーバーレイ用ステッカー PNG（ハート・吹き出し）を作る。"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from render_cats import heart  # noqa: E402

FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"

d = Path(sys.argv[1])
d.mkdir(parents=True, exist_ok=True)

img = Image.new("RGBA", (240, 220), (0, 0, 0, 0))
dr = ImageDraw.Draw(img)
heart(dr, 120, 112, 118, (255, 255, 255, 255))
heart(dr, 120, 112, 100, (240, 80, 120, 255))
dr.ellipse([70, 60, 100, 90], fill=(255, 255, 255, 170))
img.resize((120, 110), Image.LANCZOS).save(d / "heart.png")

b = Image.new("RGBA", (420, 230), (0, 0, 0, 0))
dr = ImageDraw.Draw(b)
dr.rounded_rectangle([10, 10, 410, 170], radius=70, fill="white", outline=(240, 110, 140), width=10)
dr.polygon([(90, 160), (150, 160), (70, 222)], fill="white", outline=(240, 110, 140))
dr.line([(90, 165), (70, 222), (150, 165)], fill=(240, 110, 140), width=10)
dr.rectangle([95, 150, 145, 168], fill="white")
f = ImageFont.truetype(FONT, 76)
dr.text((210, 92), "だいすき", font=f, fill=(220, 70, 110), anchor="mm")
b.resize((210, 115), Image.LANCZOS).save(d / "bubble.png")
print("stickers ok")
