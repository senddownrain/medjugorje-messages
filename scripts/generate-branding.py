"""Resize the approved artwork without cropping, tracing, or redrawing it.

Install scripts/requirements-branding.txt, then run from any working directory.
"""
from pathlib import Path
from math import sqrt

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/branding/approved-logo.jpg'
PUBLIC = ROOT / 'public'


def main():
    artwork = ImageOps.exif_transpose(Image.open(SOURCE)).convert('RGB')
    if artwork.size != (1280, 1280):
        raise ValueError('Expected the approved 1280×1280 original')

    def resize(size):
        return artwork.resize((size, size), Image.Resampling.LANCZOS)

    for size in (96, 192):
        resize(size).save(PUBLIC / f'logo-{size}.webp', lossless=True, method=6)
    for size, name in ((64, 'favicon-64.png'), (180, 'apple-touch-icon.png'),
                       (192, 'icon-192.png'), (512, 'icon-512.png')):
        resize(size).save(PUBLIC / name, optimize=True)
    artwork.save(PUBLIC / 'favicon.ico', sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])

    # The ENTIRE original square fits inside the guaranteed central circle
    # (radius 40% of the canvas), including its corners. No artwork is cropped.
    size = 512
    inner = int(size * 0.8 / sqrt(2))
    maskable = Image.new('RGB', (size, size), '#fffefa')
    inset = (size - inner) // 2
    maskable.paste(resize(inner), (inset, inset))
    maskable.save(PUBLIC / 'icon-maskable-512.png', optimize=True)
    for path in sorted(PUBLIC.iterdir()):
        if path.is_file():
            print(f'{path.relative_to(ROOT)}: {path.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
