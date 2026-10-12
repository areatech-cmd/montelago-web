"""Trae del tour el material que esta web usa, y sólo ése.

El tour pesa unos 190 MB. Aquí hacen falta 25 imágenes y el vídeo de la portada, nada más, así
que copiarlo entero sería arrastrar peso muerto a un repositorio público.

    python scripts/traer_medios.py                 # usa ..\\WEB3D
    python scripts/traer_medios.py --tour RUTA

Las imágenes se copian tal cual: son renders oficiales y no se tocan. El vídeo de la portada SÍ
se vuelve a comprimir, y conviene explicar por qué: el original de 1080 va a 11,2 Mbps —21 MB
por quince segundos—, que es una barbaridad para lo primero que ve alguien que llega de un
anuncio. A 4 Mbps son unos 7 MB y en un bucle de fondo, detrás de un velo y con el logo encima,
no se distingue. El de 720 se queda como está: ya pesa poco.

Necesita ffmpeg. Si el tour está al lado, usa el suyo (node_modules/ffmpeg-static).
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BITRATE_1080 = '4000k'


def ffmpeg(tour):
    propio = tour / 'node_modules' / 'ffmpeg-static' / 'ffmpeg.exe'
    if propio.exists():
        return str(propio)
    if shutil.which('ffmpeg'):
        return 'ffmpeg'
    raise SystemExit('No encuentro ffmpeg (ni el del tour ni uno en el PATH)')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tour', default=str(RAIZ.parent / 'WEB3D'))
    args = ap.parse_args()
    tour = Path(args.tour)
    publico = tour / 'public'
    if not (publico / 'data' / 'project.json').exists():
        raise SystemExit(f'No encuentro el tour en {tour}')

    p = json.loads((publico / 'data' / 'project.json').read_text(encoding='utf-8'))

    # --- Imágenes: las que la página nombra, ni una más ---
    quiero = [p['masterplan']['stops'][0]['posterUrl'], p['home']['logoImgUrl']]
    for g in p['gallery']['items']:
        if g.get('posterUrl'):
            quiero.append(g['posterUrl'])
        if (g.get('url') or '').endswith('.webp'):
            quiero.append(g['url'])
    for a in p['amenities']['items']:
        for i in a.get('images', []):
            if (i.get('url') or '').endswith('.webp'):
                quiero.append(i['url'])

    destino_img = RAIZ / 'assets' / 'img'
    destino_img.mkdir(parents=True, exist_ok=True)
    copiadas = peso = 0
    for rel in dict.fromkeys(quiero):
        src = publico / rel
        if not src.exists():
            print(f'  AVISO  no está en el tour: {rel}')
            continue
        shutil.copy2(src, destino_img / src.name)
        copiadas += 1
        peso += src.stat().st_size
    print(f'imágenes: {copiadas} · {peso / 1048576:.1f} MB')

    # --- Vídeo de la portada ---
    destino_vid = RAIZ / 'assets' / 'video'
    destino_vid.mkdir(parents=True, exist_ok=True)
    exe = ffmpeg(tour)
    videos = {v['width']: publico / v['url'] for v in p['masterplan']['stops'][0]['videos']}

    chico = videos.get(1280)
    if chico and chico.exists():
        shutil.copy2(chico, destino_vid / 'portada-720.mp4')
        print(f'  portada-720.mp4  {chico.stat().st_size / 1048576:.1f} MB  (copiado tal cual)')

    grande = videos.get(1920)
    if grande and grande.exists():
        salida = destino_vid / 'portada-1080.mp4'
        subprocess.run(
            [exe, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(grande),
             '-an',                       # sin audio: el bucle va mudo de todas formas
             '-c:v', 'libx264', '-b:v', BITRATE_1080, '-maxrate', BITRATE_1080,
             '-bufsize', '8000k', '-preset', 'slow', '-profile:v', 'high', '-pix_fmt', 'yuv420p',
             '-movflags', '+faststart',   # para que empiece a verse antes de bajarlo entero
             str(salida)], check=True)
        print(f'  portada-1080.mp4 {salida.stat().st_size / 1048576:.1f} MB  '
              f'(de {grande.stat().st_size / 1048576:.0f} MB, recomprimido a {BITRATE_1080})')

    print('\nAhora: python scripts/generar.py')


if __name__ == '__main__':
    sys.exit(main())
