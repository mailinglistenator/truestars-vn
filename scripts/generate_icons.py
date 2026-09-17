#!/usr/bin/env python3
"""
Generate crisp PNG icons for TrueStars VN Chrome Extension.
Sizes: 16x16, 48x48, 128x128.
"""

import os
import math
from PIL import Image, ImageDraw

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "extension", "icons")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def draw_star(draw, center, radius, points=5, color=(251, 191, 36, 255)):
    cx, cy = center
    inner_radius = radius * 0.42
    star_points = []
    
    for i in range(points * 2):
        r = radius if i % 2 == 0 else inner_radius
        angle = i * math.pi / points - math.pi / 2
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        star_points.append((x, y))
        
    draw.polygon(star_points, fill=color)

def generate_icon(size):
    # Render at 4x resolution for smooth antialiasing
    scale = 4
    canvas_size = size * scale
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Shield / Badge Background (Dark Navy #0f172a with subtle border)
    margin = 4 * scale
    
    # Draw rounded circle / shield
    draw.ellipse(
        [margin, margin, canvas_size - margin, canvas_size - margin],
        fill=(15, 23, 42, 255),
        outline=(59, 130, 246, 255),
        width=int(2.5 * scale)
    )
    
    # Draw golden star in center
    star_radius = (canvas_size / 2) * 0.52
    draw_star(draw, (canvas_size / 2, canvas_size / 2), star_radius, color=(251, 191, 36, 255))
    
    # Downsample with high-quality Lanczos filter
    final_img = img.resize((size, size), Image.Resampling.LANCZOS)
    out_path = os.path.join(OUTPUT_DIR, f"icon-{size}.png")
    final_img.save(out_path, "PNG")
    print(f"Generated {out_path} ({size}x{size} px)")

if __name__ == "__main__":
    for s in [16, 48, 128]:
        generate_icon(s)
