"""Icon generator for JARVIS."""
from pathlib import Path
from PIL import Image, ImageDraw


def create_jarvis_icon(size: int = 256, output_path: str = None) -> Image.Image:
    """JARVIS logosunu programatik olarak oluştur."""
    img = Image.new("RGBA", (size, size), (1, 10, 10, 255))
    draw = ImageDraw.Draw(img)
    
    # Cyan renkleri
    cyan_bright = (0, 232, 208, 255)
    cyan_mid = (0, 184, 168, 200)
    cyan_dim = (0, 100, 100, 100)
    
    center = size // 2
    radius = size // 3
    
    # Ana hexagon (J harfi stilinde)
    points = []
    for i in range(6):
        angle = (i * 60 - 90) * 3.14159 / 180
        x = center + radius * 0.8 * __import__('math').cos(angle)
        y = center + radius * 0.8 * __import__('math').sin(angle)
        points.append((x, y))
    
    # Hexagon çiz
    draw.polygon(points, outline=cyan_bright, width=3)
    
    # İç daire
    inner_r = radius * 0.5
    draw.ellipse(
        [center - inner_r, center - inner_r, center + inner_r, center + inner_r],
        outline=cyan_mid,
        width=2
    )
    
    # Orta nokta
    dot_r = radius * 0.15
    draw.ellipse(
        [center - dot_r, center - dot_r, center + dot_r, center + dot_r],
        fill=cyan_bright
    )
    
    # Köşe noktaları
    for px, py in points:
        dot_r = 4
        draw.ellipse([px - dot_r, py - dot_r, px + dot_r, py + dot_r], fill=cyan_bright)
    
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, "PNG")
    
    return img


if __name__ == "__main__":
    # Icon dosyalarını oluştur
    icon_dir = Path(__file__).parent
    
    # 256x256 (window icon)
    create_jarvis_icon(256, icon_dir / "jarvis.png")
    print(f"✓ Created: {icon_dir / 'jarvis.png'}")
    
    # 64x64 (tray icon)
    create_jarvis_icon(64, icon_dir / "jarvis_tray.png")
    print(f"✓ Created: {icon_dir / 'jarvis_tray.png'}")
