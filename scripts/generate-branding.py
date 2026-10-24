"""Extract the two approved icons; no generated or redrawn artwork.

The dark icon's visible outer contour supplies a transparency mask for both
copies of the same rounded tile. Interior RGB pixels are copied unchanged.
Square padding preserves the layout's slightly rectangular icon proportions.
"""
from pathlib import Path
from math import sqrt
import hashlib
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/branding/approved-layout.png'
PUBLIC = ROOT / 'public'
BOXES = {'light': (20, 165, 716, 898), 'dark': (735, 165, 1430, 898)}


def extract(layout):
    dark = layout.crop(BOXES['dark']).convert('RGB')
    edges = []
    for y in range(dark.height):
        xs = [x for x in range(dark.width)
              if dark.getpixel((x, y))[0] < 120 and
              dark.getpixel((x, y))[2] - dark.getpixel((x, y))[0] > 15]
        if xs:
            edges.append((y, min(xs), max(xs)))
    # Trace the outer tile, never the face, stars or church. Supersampling
    # antialiases only this transparency boundary, not the original painting.
    contour = [(x, y) for y, x, _ in edges] + [(x + 1, y) for y, _, x in reversed(edges)]
    mask = Image.new('L', (dark.width * 4, dark.height * 4))
    ImageDraw.Draw(mask).polygon([(x * 4, y * 4) for x, y in contour], fill=255)
    mask = mask.resize(dark.size, Image.Resampling.LANCZOS)
    result = {}
    for theme, box in BOXES.items():
        icon = layout.crop(box).convert('RGBA')
        icon.putalpha(mask.resize(icon.size, Image.Resampling.LANCZOS))
        side = max(icon.size)
        square = Image.new('RGBA', (side, side))
        square.paste(icon, ((side - icon.width) // 2, 0))
        square.save(ROOT / f'docs/branding/source-{theme}.png', optimize=True)
        result[theme] = square
    return result


def main():
    layout = ImageOps.exif_transpose(Image.open(SOURCE))
    if layout.size != (1448, 1086):
        raise ValueError('Expected the approved 1448×1086 two-icon layout')
    icons = extract(layout)
    for theme, artwork in icons.items():
        resize = lambda n: artwork.resize((n, n), Image.Resampling.LANCZOS)
        for size in (96, 192):
            resize(size).save(PUBLIC / f'logo-{theme}-{size}.webp', lossless=True, method=6)
        suffix = '' if theme == 'light' else '-dark'
        resize(64).save(PUBLIC / f'favicon{suffix}-64.png', optimize=True)
        # Small dedicated favicon: reduce colour noise while keeping the veil,
        # profile, gold halo and church. This never replaces the main artwork.
        tiny = resize(16)
        backdrop = Image.new('RGBA', tiny.size, '#fffefa' if theme == 'light' else '#072a52')
        backdrop.alpha_composite(tiny)
        small = backdrop.convert('RGBA')
        for y in range(16):
            for x in range(16):
                r,g,b,_ = small.getpixel((x,y))
                if b > r + 7 and b > g + 3:
                    colour = '#0a3762'
                elif r > b + 14 and r > g + 6:
                    colour = '#d89b32'
                else:
                    colour = '#fffaf0'
                small.putpixel((x,y), Image.new('RGBA',(1,1),colour).getpixel((0,0)))
        small.putalpha(tiny.getchannel('A'))
        small.save(PUBLIC / f'favicon{suffix}-16.png', optimize=True)
        frames = [resize(n) for n in (16, 32, 48, 64)]
        frames[0] = small.convert('RGBA')
        frames[-1].save(PUBLIC / f'favicon{suffix}.ico', sizes=[(16,16),(32,32),(48,48),(64,64)],
                        append_images=frames[:-1])
    light = icons['light']
    for size, name in ((180, 'apple-touch-icon.png'), (192, 'icon-192.png'), (512, 'icon-512.png')):
        # Installation icons are opaque, stable and deliberately independent
        # of the current application theme; OS icon switching is not promised.
        canvas = Image.new('RGBA', (size, size), '#fffefa')
        canvas.alpha_composite(light.resize((size,size), Image.Resampling.LANCZOS))
        canvas.convert('RGB').save(PUBLIC / name, optimize=True)
    size = 512
    inner = int(size * .8 / sqrt(2))
    maskable = Image.new('RGBA', (size,size), '#fffefa')
    maskable.alpha_composite(light.resize((inner,inner), Image.Resampling.LANCZOS), ((size-inner)//2,)*2)
    maskable.convert('RGB').save(PUBLIC / 'icon-maskable-512.png', optimize=True)
    print('Layout SHA256:', hashlib.sha256(SOURCE.read_bytes()).hexdigest())
    for path in sorted(PUBLIC.iterdir()):
        if path.is_file(): print(f'{path.relative_to(ROOT)}: {path.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
