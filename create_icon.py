import os
from PIL import Image, ImageDraw

os.makedirs("assets", exist_ok=True)
icon_path = "assets/app_icon.ico"

# Créer une image 256x256
img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Fond sombre doux
draw.ellipse((10, 10, 246, 246), fill=(14, 18, 27, 255), outline=(56, 189, 248, 180), width=6)

# Halo cyan
draw.ellipse((45, 45, 211, 211), fill=(30, 41, 59, 255))

# Noyau central Antigravity Cyan
draw.ellipse((85, 85, 171, 171), fill=(56, 189, 248, 255))

# Sauvegarder sous formats multiples pour .ico
img.save(icon_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print(f"Icône générée avec succès dans {icon_path}")
