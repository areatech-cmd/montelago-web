"""Trae del tour el material que esta web usa, y sólo ése.

El tour pesa unos 190 MB. Aquí hacen falta las imágenes que la página nombra, el vídeo de la
portada y los clips de la galería, nada más: copiarlo entero sería arrastrar peso muerto a un
repositorio público.

    python scripts/traer_medios.py                 # usa ..\\WEB3D
    python scripts/traer_medios.py --tour RUTA

Las imágenes se copian tal cual: son renders oficiales y no se tocan. El vídeo de la portada SÍ
se vuelve a comprimir, y conviene explicar por qué: el original de 1080 va a 11,2 Mbps —21 MB
por quince segundos—, que es una barbaridad para lo primero que ve alguien que llega de un
anuncio. A 4 Mbps son unos 7 MB y en un bucle de fondo, detrás de un velo y con el logo encima,
no se distingue. El de 720 se queda como está: ya pesa poco.

De los clips de la galería se trae **sólo la versión de 720**, no la de 1080. Son siete; en
1080 suman 17 MB y en 720, cinco. En un recuadro de la galería no se distinguen, y el que
quiera verlo en grande tiene el tour, que es justo a donde esta página lleva.

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
    ap.add_argument('--rehacer', action='store_true',
                    help='volver a comprimir el vídeo y las imágenes derivadas aunque ya estén')
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
    salida = destino_vid / 'portada-1080.mp4'
    if grande and not grande.exists():
        print('  AVISO  el tour no tiene el vídeo de 1080 de la portada')
        grande = None
    # Si ya está, NO se vuelve a comprimir. x264 con varios hilos no da dos veces el mismo
    # archivo, así que cada pasada de más sería un blob de 7 MB nuevo en el historial de git sin
    # que haya cambiado nada. Con --rehacer se fuerza, que es lo que toca si Arquitectura manda
    # un vídeo nuevo.
    if grande and salida.exists() and not args.rehacer:
        print(f'  portada-1080.mp4 ya estaba ({salida.stat().st_size / 1048576:.1f} MB), '
              f'no se recomprime · --rehacer para forzarlo')
        grande = None
    if grande:
        subprocess.run(
            [exe, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(grande),
             '-an',                       # sin audio: el bucle va mudo de todas formas
             '-c:v', 'libx264', '-b:v', BITRATE_1080, '-maxrate', BITRATE_1080,
             '-bufsize', '8000k', '-preset', 'slow', '-profile:v', 'high', '-pix_fmt', 'yuv420p',
             '-movflags', '+faststart',   # para que empiece a verse antes de bajarlo entero
             str(salida)], check=True)
        print(f'  portada-1080.mp4 {salida.stat().st_size / 1048576:.1f} MB  '
              f'(de {grande.stat().st_size / 1048576:.0f} MB, recomprimido a {BITRATE_1080})')

    # --- La fuente de la marca, servida desde aquí ---
    # Sin esto la página caía a la fuente del sistema y no se parecía a la marca. Se copian las
    # cuatro variantes que esta página usa y SÓLO la subserie «latin»: cubre tildes, ñ, · y ²,
    # que es todo lo que hay en un texto en español. La «latin-ext» son 276 KB para alfabetos
    # que aquí no aparecen.
    #
    # Se sirven desde el propio sitio, como en el tour: así la IP del visitante no viaja a
    # Google por el hecho de leer una página.
    RANGO_LATIN = (
        'U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, '
        'U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, '
        'U+FEFF, U+FFFD'
    )
    fuentes = RAIZ / 'assets' / 'fuentes'
    fuentes.mkdir(parents=True, exist_ok=True)
    reglas = []
    for peso in (400, 600, 700):   # el 500 no lo usa nadie: son 37 KB que no se bajan
        src = publico / 'fonts' / f'montserrat-{peso}-latin.woff2'
        if not src.exists():
            print(f'  AVISO  falta la variante de {peso} de la fuente')
            continue
        shutil.copy2(src, fuentes / src.name)
        reglas.append(
            '@font-face {\n'
            "  font-family: 'Montserrat';\n"
            '  font-style: normal;\n'
            f'  font-weight: {peso};\n'
            '  font-display: swap;\n'
            f"  src: url(./{src.name}) format('woff2');\n"
            f'  unicode-range: {RANGO_LATIN};\n'
            '}'
        )
    if reglas:
        (fuentes / 'montserrat.css').write_text(
            '/* Generado por scripts/traer_medios.py: no editar a mano.\n'
            '   Montserrat servida desde el propio sitio, subserie latin. */\n'
            + '\n'.join(reglas) + '\n', encoding='utf-8')
        peso_f = sum(p.stat().st_size for p in fuentes.glob('*.woff2'))
        print(f'fuentes: {len(reglas)} variantes · {peso_f / 1024:.0f} KB')

    # --- La imagen de la tarjeta del enlace ---
    # Esta página va a circular por WhatsApp, y WhatsApp no siempre pinta un WebP en la vista
    # previa. Así que la aérea de la portada se guarda además en JPEG y al tamaño que esperan
    # las tarjetas (1200x630): se recorta un poco arriba y abajo, que en una aérea no se nota.
    portada_src = publico / p['masterplan']['stops'][0]['posterUrl']
    if portada_src.exists():
        salida = RAIZ / 'assets' / 'img' / 'tarjeta-og.jpg'
        subprocess.run(
            [exe, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(portada_src),
             '-vf', 'scale=1200:-1:flags=lanczos,crop=1200:630',
             # calidad 7 y no 3: medido sobre esta misma aérea, el 3 da 292 KB, el 5 da 213
             # y el 7 da 166. Algunas versiones de WhatsApp dejan de pintar la vista previa
             # pasados los 200 KB, y en una tarjeta de 1200 px mirada de paso en un chat la
             # diferencia entre el 3 y el 7 no se ve.
             '-q:v', '7', '-frames:v', '1', str(salida)], check=True)
        print(f'  tarjeta-og.jpg  {salida.stat().st_size / 1024:.0f} KB  (para WhatsApp y Facebook)')

    # --- Iconos de pestaña ---
    # El único logo que entregó Arquitectura es blanco (1187x830), y un logo blanco sobre la
    # pestaña blanca de un navegador no se ve. Así que se compone sobre el verde de la marca: el
    # logo es el oficial, el fondo es el color oficial, y no hay que inventar ningún símbolo.
    # Si algún día Marketing entrega un icono propio, se reemplazan estos dos y ya.
    logo = publico / p['home']['logoImgUrl']
    if logo.exists():
        for lado, dentro in ((180, 148), (32, 30)):
            salida = destino_img / f'icono-{lado}.png'
            subprocess.run(
                [exe, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(logo),
                 '-vf', f'scale={dentro}:-1:flags=lanczos,'
                        f'pad={lado}:{lado}:(ow-iw)/2:(oh-ih)/2:color=0x044048',
                 '-frames:v', '1', str(salida)], check=True)
            print(f'  icono-{lado}.png  {salida.stat().st_size / 1024:.1f} KB')

    # --- Clips de la galería: de cada uno, el de 720 ---
    clips = copiados = peso_clips = 0
    for g in p['gallery']['items']:
        url = g.get('url') or ''
        if not url.endswith('.mp4'):
            continue
        clips += 1
        src = publico / url.replace('-1080.mp4', '-720.mp4')
        if not src.exists():
            print(f'  AVISO  no está el 720 de {Path(url).name}')
            continue
        shutil.copy2(src, destino_vid / src.name)
        copiados += 1
        peso_clips += src.stat().st_size
    print(f'clips de galería: {copiados} de {clips} · {peso_clips / 1048576:.1f} MB')

    print('\nAhora: python scripts/generar.py')


if __name__ == '__main__':
    sys.exit(main())
