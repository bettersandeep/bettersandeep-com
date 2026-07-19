"""Turn a reference image into pixel art for the site avatar and favicon set.

Usage:
    python3 utils/pixelize.py <reference-image> [grid_width] [dark_fraction]
    python3 utils/pixelize.py pika.jpg 60 0.08

Requires Pillow (pip install pillow). Run from the repo root; writes to static/images/.

How it works:

1. Sampling. The reference is divided into grid_width x N cells (N keeps the
   aspect ratio). For each cell we count how many source pixels are "dark"
   (luminance < 100). If that fraction >= dark_fraction the cell becomes
   outline (B). Lower dark_fraction = thicker, more connected outlines;
   raise it if the result looks too heavy, lower it if outlines break up.

2. Palette snapping. Non-outline cells take their mean colour and snap to the
   nearest class in CLASSES (yellow / white / red / pink, matched against
   colours sampled from the reference). Output uses the site's brand colours,
   not the reference colours.

3. Background removal by flood fill. In many references the background is the
   same colour as the subject (our Pikachu poster: yellow on yellow), so you
   cannot separate them by colour. Instead we flood-fill from every border
   cell across all non-outline cells; whatever the flood reaches is background
   and gets dropped. The black outline is the fence. This is why dark_fraction
   matters: one broken outline cell lets the flood eat the face (symptom: the
   output is mostly empty or the subject loses its fill colours).

4. Circle-crop safety. The theme crops the avatar to a circle, so padding
   grows until every cell (checked at its corners) fits inside the inscribed
   circle. Ear tips near canvas corners are the usual offenders.

5. Outputs. avatar.png (512px on the dark badge), PNG favicons at
   16/32/180/192/512 (LANCZOS-downscaled from a transparent master), a
   rect-per-cell favicon.svg (crisp at any size), and a black-silhouette
   safari-pinned-tab.svg.
"""
import sys
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parent.parent
IMGDIR = REPO / "static" / "images"

SRC = sys.argv[1]
GRID_W = int(sys.argv[2]) if len(sys.argv) > 2 else 60
DARK_FRAC = float(sys.argv[3]) if len(sys.argv) > 3 else 0.08

BG = (66, 66, 66, 255)  # #424242 avatar badge, matches theme dark bg tones
# class -> (reference RGB it is matched against, brand RGB it is drawn with)
CLASSES = {
    "Y": ((245, 224, 77), (255, 213, 41, 255)),
    "W": ((250, 250, 250), (255, 255, 255, 255)),
    "R": ((225, 75, 55), (232, 68, 58, 255)),
    "P": ((238, 158, 178), (242, 160, 176, 255)),
}
B_OUT = (26, 26, 26, 255)

src = Image.open(SRC).convert("RGB")
W, H = src.size
grid_h = round(H / W * GRID_W)
px = src.load()

# 1 + 2: sample cells into outline or palette classes
grid = [[None] * GRID_W for _ in range(grid_h)]
for gy in range(grid_h):
    for gx in range(GRID_W):
        x0, x1 = W * gx // GRID_W, W * (gx + 1) // GRID_W
        y0, y1 = H * gy // grid_h, H * (gy + 1) // grid_h
        n = dark = 0
        rs = gs = bs = 0
        for y in range(y0, y1):
            for x in range(x0, x1):
                r, g, b = px[x, y]
                n += 1
                if 0.299 * r + 0.587 * g + 0.114 * b < 100:
                    dark += 1
                else:
                    rs += r; gs += g; bs += b
        if dark / n >= DARK_FRAC:
            grid[gy][gx] = "B"
        else:
            m = n - dark
            mean = (rs / m, gs / m, bs / m)
            grid[gy][gx] = min(CLASSES, key=lambda c: sum(
                (a - b) ** 2 for a, b in zip(mean, CLASSES[c][0])))

# 3: flood-fill background from the borders; outline cells fence it in
q = deque((x, y) for y in range(grid_h) for x in range(GRID_W)
          if (x in (0, GRID_W - 1) or y in (0, grid_h - 1)) and grid[y][x] != "B")
seen = set(q)
while q:
    x, y = q.popleft()
    grid[y][x] = None
    for nx, ny in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
        if 0 <= nx < GRID_W and 0 <= ny < grid_h and (nx, ny) not in seen and grid[ny][nx] != "B":
            seen.add((nx, ny))
            q.append((nx, ny))

cells = [(x, y, ch) for y in range(grid_h) for x in range(GRID_W) if (ch := grid[y][x])]
xs = [x for x, _, _ in cells]
ys = [y for _, y, _ in cells]
minx, miny = min(xs), min(ys)
w, h = max(xs) - minx + 1, max(ys) - miny + 1

# 4: grow padding until every cell corner fits inside the circular crop
for pad in range(3, 15):
    side = max(w, h) + 2 * pad
    ox = (side - w) / 2 - minx
    oy = (side - h) / 2 - miny
    c = side / 2
    if all(((x + ox + dx - c) ** 2 + (y + oy + dy - c) ** 2) <= (c - 0.5) ** 2
           for x, y, _ in cells for dx in (0.02, 0.98) for dy in (0.02, 0.98)):
        break

def draw(cell_px, pad_cells, bg):
    """Render the grid centered on a square canvas, integer pixel offsets (no seams)."""
    side_cells = max(w, h) + 2 * pad_cells
    size = side_cells * cell_px
    img = Image.new("RGBA", (size, size), bg)
    d = ImageDraw.Draw(img)
    ox_ = round((size - w * cell_px) / 2) - minx * cell_px
    oy_ = round((size - h * cell_px) / 2) - miny * cell_px
    for x, y, ch in cells:
        p, q2 = x * cell_px + ox_, y * cell_px + oy_
        d.rectangle([p, q2, p + cell_px - 1, q2 + cell_px - 1],
                    fill=B_OUT if ch == "B" else CLASSES[ch][1])
    return img

# 5: outputs
badge = draw(512 // side, pad, BG)
final = Image.new("RGBA", (512, 512), BG)
final.paste(badge, ((512 - badge.width) // 2, (512 - badge.height) // 2))
final.save(IMGDIR / "avatar.png")

master = draw(8, 0, (0, 0, 0, 0))
for s, name in [(16, "favicon-16x16.png"), (32, "favicon-32x32.png"),
                (180, "apple-touch-icon.png"), (192, "android-chrome-192x192.png"),
                (512, "android-chrome-512x512.png")]:
    master.resize((s, s), Image.LANCZOS).save(IMGDIR / name)

def svg(colorfn, fname):
    sside = max(w, h)
    sx, sy = (sside - w) / 2 - minx, (sside - h) / 2 - miny
    rects = "".join(
        f'<rect x="{x + sx:g}" y="{y + sy:g}" width="1" height="1" fill="{colorfn(ch)}"/>'
        for x, y, ch in cells)
    Path(fname).write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {sside} {sside}" '
        f'shape-rendering="crispEdges">{rects}</svg>')

svg(lambda ch: "#%02x%02x%02x" % ((B_OUT if ch == "B" else CLASSES[ch][1])[:3]),
    IMGDIR / "favicon.svg")
svg(lambda ch: "#000000", IMGDIR / "safari-pinned-tab.svg")

print(f"grid {GRID_W}x{grid_h}, content {w}x{h}, pad {pad} -> avatar + favicons in {IMGDIR}")
