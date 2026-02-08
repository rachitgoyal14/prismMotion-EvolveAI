from pathlib import Path
import cairosvg

ROOT = Path(".")   # run this from the folder that contains anatomy/, cellular/, etc.
DPI = 300

svg_files = list(ROOT.rglob("*.svg"))
print(f"Found {len(svg_files)} SVG files")

for svg_path in svg_files:
    png_path = svg_path.with_suffix(".png")

    # Skip if PNG already exists
    if png_path.exists():
        print(f"↷ Skipped (exists): {png_path}")
        continue

    try:
        cairosvg.svg2png(
            url=str(svg_path),
            write_to=str(png_path),
            dpi=DPI
        )
        print(f"✓ {svg_path}")
    except Exception as e:
        print(f"✗ FAILED: {svg_path}")
        print(f"  → {e}")
