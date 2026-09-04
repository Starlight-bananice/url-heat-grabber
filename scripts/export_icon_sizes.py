"""Export platform icon sizes from the finished PNG using macOS sips."""
import struct
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1] / 'assets'
iconset = root / 'app_icon.iconset'
iconset.mkdir(exist_ok=True)
sizes = {
    'icon_16x16.png': 16, 'icon_16x16@2x.png': 32,
    'icon_32x32.png': 32, 'icon_32x32@2x.png': 64,
    'icon_128x128.png': 128, 'icon_128x128@2x.png': 256,
    'icon_256x256.png': 256, 'icon_256x256@2x.png': 512,
    'icon_512x512.png': 512, 'icon_512x512@2x.png': 1024,
}
for name, size in sizes.items():
    subprocess.run(['sips', '-z', str(size), str(size), str(root / 'app_icon.png'),
                    '--out', str(iconset / name)], stdout=subprocess.DEVNULL, check=True)
subprocess.run(['sips', '-z', '48', '48', str(root / 'app_icon.png'),
                '--out', str(root / 'sidebar_icon.png')], stdout=subprocess.DEVNULL, check=True)

entries = [(size, (iconset / name).read_bytes()) for size, name in (
    (16, 'icon_16x16.png'), (32, 'icon_32x32.png'), (64, 'icon_32x32@2x.png'),
    (128, 'icon_128x128.png'), (256, 'icon_256x256.png'))]
offset = 6 + 16 * len(entries)
index, images = b'', b''
for size, data in entries:
    index += struct.pack('<BBBBHHII', size if size < 256 else 0,
                         size if size < 256 else 0, 0, 0, 1, 32, len(data), offset)
    images += data
    offset += len(data)
(root / 'app_icon.ico').write_bytes(struct.pack('<HHH', 0, 1, len(entries)) + index + images)
print('Exported macOS 16-1024 px, Windows 16-256 px and sidebar 48 px resources.')
