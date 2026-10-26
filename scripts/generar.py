"""Arma la web de venta de Montelago a partir de los datos OFICIALES del tour.

La página es estática —un index.html y poco más— pero no está escrita a mano: se genera. Así
los textos son los que entregó Arquitectura, palabra por palabra, y las cifras se CUENTAN del
inventario en vez de teclearse. Si mañana cambia un estado en el Excel, se vuelve a correr esto
y la página se entera.

    python scripts/generar.py                      # usa ..\\WEB3D por defecto
    python scripts/generar.py --tour RUTA          # si el tour está en otro sitio
    python scripts/generar.py --url https://montelago.condominiosvillacasa.com/

Además de index.html escribe sitemap.xml y robots.txt, y pone al día en _headers el hash de la
línea de JS que va dentro del HTML (si no, la CSP la bloquearía al cambiarla).

Lo que NO hace, a propósito:
  · no inventa imágenes. Todas las fotos son renders oficiales copiados del tour (assets/img).
  · no inventa datos de contacto. El teléfono y las redes de project.json están marcados como
    EJEMPLO: hasta que Administración confirme, aquí sólo sale el WhatsApp y el correo, que sí
    están confirmados. Mejor faltar que publicar un número que no es.
"""

import argparse
import base64
import hashlib
import html
import json
import re
from datetime import date
import sys
from pathlib import Path
from urllib.parse import urlsplit

RAIZ = Path(__file__).resolve().parent.parent

# Dónde está publicada. Hace falta entera —no relativa— porque las tarjetas de WhatsApp,
# Facebook y Google piden la dirección completa de la imagen. Si el sitio se muda al dominio
# de la empresa, se corre con --url https://montelago.condominiosvillacasa.com/
PUBLICA = 'https://areatech-cmd.github.io/montelago-web/'


def esc(s):
    return html.escape(str(s or ''), quote=True)


def img(url):
    """Del url del tour («media/clips/x.webp») al de aquí («assets/img/x.webp»)."""
    return f'assets/img/{Path(url).name}' if url else ''


def medidas(ruta):
    """El ancho y el alto de un WebP o un PNG, leídos de su cabecera.

    Van en el HTML para que el navegador reserve el hueco antes de bajar la imagen: sin eso el
    texto baja de golpe cuando cada foto aparece, y la página salta mientras se lee.

    Se LEEN del archivo y no se teclean a propósito. Un tamaño teclado sobrevive al render que
    lo reemplaza y entonces miente, que es peor que no decir nada. Son treinta líneas de leer
    cabeceras para no depender de Pillow, que este proyecto no tiene instalado.
    """
    try:
        d = Path(ruta).read_bytes()[:40]
    except OSError:
        return None
    if d[:8] == b'\x89PNG\r\n\x1a\n' and d[12:16] == b'IHDR':
        return int.from_bytes(d[16:20], 'big'), int.from_bytes(d[20:24], 'big')
    if d[:4] != b'RIFF' or d[8:12] != b'WEBP':
        return None
    tipo = d[12:16]
    if tipo == b'VP8X':                        # extendido (el que lleva alfa o animación)
        return (int.from_bytes(d[24:27], 'little') + 1,
                int.from_bytes(d[27:30], 'little') + 1)
    if tipo == b'VP8 ':                        # con pérdida, el normal
        if d[23:26] != b'\x9d\x01\x2a':         # la marca de sincronía del fotograma
            return None
        return (int.from_bytes(d[26:28], 'little') & 0x3FFF,
                int.from_bytes(d[28:30], 'little') & 0x3FFF)
    if tipo == b'VP8L':                        # sin pérdida
        bits = int.from_bytes(d[21:25], 'little')
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None


def dim(url):
    """ width="..." height="..." para esa imagen, o nada si no se pudo leer."""
    m = medidas(RAIZ / url) if url else None
    return f' width="{m[0]}" height="{m[1]}"' if m else ''


def normalizar_url(url):
    """La dirección pública, comprobada: https, con dominio, sin ?consulta ni #ancla, y con la
    barra final.

    Se comprueba porque un error aquí no se ve en local —la página carga igual— y sale después
    en todas partes a la vez: la canonical, la tarjeta de WhatsApp y el sitemap apuntando a una
    dirección que no existe. «montelago.condominiosvillacasa.com» sin el https:// es un error
    fácil de cometer y daría una canonical relativa. Se admite http sólo para localhost, que es
    para probar.
    """
    url = (url or '').strip()
    partes = urlsplit(url)
    local = partes.hostname in ('localhost', '127.0.0.1')
    if partes.scheme != 'https' and not (partes.scheme == 'http' and local):
        raise SystemExit(f'--url tiene que empezar por https:// (llegó «{url}»)')
    if not partes.hostname:
        raise SystemExit(f'--url no tiene dominio (llegó «{url}»)')
    if partes.query or partes.fragment:
        raise SystemExit(f'--url no puede llevar ? ni # (llegó «{url}»)')
    return url if url.endswith('/') else url + '/'


def jsonld_seguro(ficha):
    """La ficha JSON-LD lista para ir dentro de un <script>.

    json.dumps no escapa «<»: si algún texto del tour trajera «</script>», cerraría la etiqueta
    a mitad de la ficha y lo que viniera detrás se leería como HTML. Hoy los textos son de
    Arquitectura y no lo traen, pero es una línea. \\u003c es el mismo carácter para cualquier
    lector de JSON.
    """
    return (json.dumps(ficha, ensure_ascii=False, separators=(',', ':'))
            .replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026'))


def hashes_csp(pagina):
    """Los hash sha256 de cada <script> escrito dentro del HTML que el navegador EJECUTA.

    Los que llevan src no cuentan (los cubre 'self') y la ficha JSON-LD tampoco: es un bloque de
    datos, no código, y la CSP no lo bloquea. El hash es del texto exacto entre las etiquetas,
    espacios incluidos: por eso se calcula del HTML ya armado y no se teclea.
    """
    salida = []
    for m in re.finditer(r'<script(?P<attrs>[^>]*)>(?P<js>.*?)</script>', pagina, re.S | re.I):
        attrs = m['attrs']
        if re.search(r'\bsrc\s*=', attrs, re.I):
            continue
        tipo = re.search(r'\btype\s*=\s*["\']?([^"\'\s>]+)', attrs, re.I)
        if tipo and tipo.group(1).lower() not in ('text/javascript', 'module', 'application/javascript'):
            continue
        h = base64.b64encode(hashlib.sha256(m['js'].encode('utf-8')).digest()).decode('ascii')
        salida.append(f"'sha256-{h}'")
    return list(dict.fromkeys(salida))


def sincronizar_csp(pagina):
    """Reescribe el script-src de _headers con los hash de la página recién generada.

    Sin esto, el día que alguien toque la línea de JS de la plantilla la CSP la bloquearía en
    Cloudflare —en local y en GitHub Pages no se nota, porque ahí _headers no se aplica— y el
    formulario dejaría de aparecer sin que nadie supiera por qué.
    """
    ruta = RAIZ / '_headers'
    if not ruta.exists():
        return
    texto = ruta.read_text(encoding='utf-8')
    nuevo_src = ' '.join(["script-src 'self'"] + hashes_csp(pagina))
    nuevo, cuantos = re.subn(r"(?m)^(\s*Content-Security-Policy:.*?)script-src [^;\n]*",
                             lambda m: m.group(1) + nuevo_src, texto)
    if not cuantos:
        print('  AVISO  _headers no tiene una Content-Security-Policy con script-src: no se tocó')
        return
    if nuevo != texto:
        ruta.write_text(nuevo, encoding='utf-8')
        print(f'_headers: script-src puesto al día ({nuevo_src})')


def faltan(pagina):
    """Los archivos de assets/ que la página nombra y no están en el disco.

    Un render que el tour renombró deja aquí un <img> roto que nadie ve hasta que lo ve un
    cliente. Mejor avisar al generar.
    """
    rutas = re.findall(r'(?:src|href|poster|data-720|data-1080)="(assets/[^"#?]+)', pagina)
    return sorted({r for r in rutas if not (RAIZ / r).exists()})


def lastmod(pagina, hoy):
    """La fecha de última modificación para el sitemap.

    Si la página que sale es idéntica a la que ya había, se conserva la fecha de antes. Poner
    «hoy» cada vez que se corre el script le dice a Google que la página cambió cuando no
    cambió, y Google aprende a no creerse el lastmod de este sitio. De paso, el sitemap no
    aparece modificado en git sin motivo.
    """
    previa = RAIZ / 'index.html'
    mapa = RAIZ / 'sitemap.xml'
    if previa.exists() and mapa.exists() and previa.read_text(encoding='utf-8') == pagina:
        m = re.search(r'<lastmod>(\d{4}-\d{2}-\d{2})</lastmod>', mapa.read_text(encoding='utf-8'))
        if m:
            return m.group(1)
    return hoy


def escribir_sitemap_y_robots(base, fecha):
    """Dos archivos de tres líneas: se escriben aquí mismo."""
    (RAIZ / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url><loc>{html.escape(base)}</loc><lastmod>{fecha}</lastmod></url>\n'
        '</urlset>\n', encoding='utf-8')

    robots = ['# Generado por scripts/generar.py: no editar a mano.']
    if urlsplit(base).path not in ('', '/'):
        # En github.io/montelago-web/ el robots.txt que leen los buscadores es el de la raíz
        # del dominio (github.io/robots.txt), que no es nuestro. Éste no lo lee nadie.
        robots += ['# OJO: la web vive en una subcarpeta y los buscadores sólo leen el robots.txt',
                   '# de la raíz del dominio. Mientras siga así, el sitemap hay que darlo a mano',
                   '# en Google Search Console. En el dominio propio este archivo sí cuenta.']
    robots += ['User-agent: *', 'Allow: /', '', f'Sitemap: {base}sitemap.xml']
    (RAIZ / 'robots.txt').write_text('\n'.join(robots) + '\n', encoding='utf-8')


def foto_tarjeta(url, alt):
    """El recuadro de la foto de una tarjeta, o nada si no hay foto.

    Sin foto no se pinta: un <img src=""> es un icono roto en una página de venta, y el texto
    de la tarjeta se sostiene solo."""
    if not url:
        return ''
    return (f'<div class="tarjeta__foto"><img src="{esc(url)}" alt="{esc(alt)}"{dim(url)} '
            'loading="lazy" decoding="async"></div>')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tour', default=str(RAIZ.parent / 'WEB3D'), help='carpeta del tour')
    ap.add_argument('--url', default=PUBLICA,
                    help='dirección donde se publica (para og:image, canonical y sitemap)')
    args = ap.parse_args()

    tour = Path(args.tour)
    datos = tour / 'public' / 'data'
    if not (datos / 'project.json').exists():
        raise SystemExit(f'No encuentro los datos del tour en {datos}')

    p = json.loads((datos / 'project.json').read_text(encoding='utf-8'))
    lotes = json.loads((datos / 'lots.json').read_text(encoding='utf-8'))['lots']

    proyecto = p['project']
    mp = p['masterplan']
    galeria = {g.get('label', ''): g for g in p['gallery']['items']}

    # --- Las cifras se cuentan, no se escriben ---
    libres = [l for l in lotes if l.get('status') == 'available']
    areas = [l['area'] for l in libres if l.get('area')]
    cifras = [('3', 'etapas'), ('342', 'lotes al terminar')]
    if libres:
        cifras.append((str(len(libres)), 'disponibles hoy en la Etapa I'))
    if areas:
        # «desde» a secas, debajo de la cifra, se leía «243 m² desde» y no decía desde qué
        cifras.append((f'{round(min(areas))} m²', 'el lote disponible más pequeño'))

    # --- Las tres etapas, con el texto oficial de los puntos del masterplan ---
    etapas = []
    for hid in ('residencial', 'etapa-2', 'etapa-3'):
        h = next((x for x in mp['hotspots'] if x['id'] == hid), None)
        if not h:
            continue
        # La etiqueta tiene que aparecer como palabra entera: con startswith, «Etapa I» casaba
        # con «Etapa II · …» y la Etapa I salía con la foto de la Etapa II. Así encuentra
        # «La Etapa I desde arriba», que es la suya.
        suya = re.compile(r'(?<!\w)' + re.escape(h['label']) + r'(?!\w)')
        clip = next((g for k, g in galeria.items() if suya.search(k)), None)
        etapas.append({'label': h['label'], 'texto': h.get('shortText', ''),
                       'foto': img((clip or {}).get('posterUrl', ''))})

    # --- Áreas comunes ---
    amenidades = []
    for a in p['amenities']['items']:
        foto = next((i['url'] for i in a.get('images', []) if (i.get('url') or '').endswith('.webp')), '')
        amenidades.append({'nombre': a['name'], 'texto': a.get('shortText', ''),
                           'foto': img(foto), 'rasgos': (a.get('features') or [])[:5]})

    # --- Galería: los clips oficiales, en su versión de 720 ---
    clips = []
    for g in p['gallery']['items']:
        url = g.get('url') or ''
        if not url.endswith('.mp4'):
            continue
        clips.append({'label': g.get('label', ''),
                      'foto': img(g.get('posterUrl', '')),
                      'clip': 'assets/video/' + Path(url).name.replace('-1080.mp4', '-720.mp4')})

    plano = next((g for k, g in galeria.items() if 'masterplan-general' in (g.get('url') or '')), None)
    mapa = next((g for k, g in galeria.items() if 'mapa-rutas' in (g.get('url') or '')), None)

    # --- Contacto: sólo lo confirmado (ver el docstring) ---
    c = proyecto.get('contact', {})
    wa = (c.get('whatsAppNumber') or '').replace(' ', '').replace('+', '')
    correo = c.get('email', '')

    # El logo en WebP sin pérdida si traer_medios.py lo dejó: mismos píxeles, la mitad del peso
    logo = img(p['home']['logoImgUrl'])
    if logo and (RAIZ / logo).with_suffix('.webp').exists():
        logo = logo.rsplit('.', 1)[0] + '.webp'

    # --- Lo que necesitan los buscadores y las tarjetas de los enlaces ---
    base = normalizar_url(args.url)
    loc = p.get('location', {})
    ficha = {
        '@context': 'https://schema.org',
        '@type': 'Place',
        'name': loc.get('title') or proyecto['name'],
        'description': proyecto['description'],
        'url': base,
        'image': base + 'assets/img/tarjeta-og.jpg',
        'address': {'@type': 'PostalAddress', 'streetAddress': loc.get('address', ''),
                    'addressLocality': 'Tumán', 'addressRegion': 'Lambayeque',
                    'addressCountry': 'PE'},
        'telephone': proyecto.get('contact', {}).get('whatsAppNumber', ''),
        'isicV4': '6810',
    }
    if loc.get('latLng'):
        ficha['geo'] = {'@type': 'GeoCoordinates',
                        'latitude': loc['latLng'][0], 'longitude': loc['latLng'][1]}
    dev = proyecto.get('developer', {})
    if dev.get('name'):
        ficha['additionalProperty'] = {'@type': 'PropertyValue', 'name': 'Promotora',
                                       'value': dev['name']}

    # el sitemap y el robots se escriben DESPUÉS de armar la página: la fecha del sitemap
    # depende de si la página cambió (ver lastmod)

    html_out = PLANTILLA.format(
        titulo=esc(proyecto.get('htmlTitle') or proyecto['name']),
        nombre=esc(proyecto['name']),
        tagline=esc(proyecto['tagline']),
        descripcion=esc(proyecto['description']),
        portada=img(mp['stops'][0]['posterUrl']),
        logo=esc(logo),
        cifras='\n'.join(
            f'      <div class="dato"><strong>{esc(v)}</strong><span>{esc(t)}</span></div>'
            for v, t in cifras),
        etapas='\n'.join(
            f'''      <article class="tarjeta">
        {foto_tarjeta(e['foto'], e['label'])}
        <h3>{esc(e['label'])}</h3><p>{esc(e['texto'])}</p>
      </article>''' for e in etapas),
        plano_img=img((plano or {}).get('url', '')),
        plano_pie=esc((plano or {}).get('label', '')),
        amenidades='\n'.join(
            f'''      <article class="tarjeta">
        <div class="tarjeta__foto"><img src="{a['foto']}" alt="{esc(a['nombre'])}"{dim(a['foto'])} loading="lazy" decoding="async"></div>
        <h3>{esc(a['nombre'])}</h3><p>{esc(a['texto'])}</p>
        <ul>{''.join(f'<li>{esc(r)}</li>' for r in a['rasgos'])}</ul>
      </article>''' for a in amenidades),
        clips='\n'.join(
            f'''      <article class="clip">
        <a class="clip__abrir" href="{c['clip']}" aria-label="Ver el clip: {esc(c['label'])}">
          <img src="{c['foto']}" alt="{esc(c['label'])}"{dim(c['foto'])} loading="lazy" decoding="async">
          <span class="clip__play" aria-hidden="true"></span>
          <span class="clip__nombre">{esc(c['label'])}</span>
        </a>
      </article>''' for c in clips),
        mapa_img=img((mapa or {}).get('url', '')),
        mapa_pie=esc((mapa or {}).get('label', '')),
        wa=esc(wa), correo=esc(correo),
        tour=esc(proyecto.get('siteUrl') or 'https://montelago-tour.condominiosvillacasa.com'),
        aviso=esc(proyecto.get('disclaimer', '')),
        empresa=esc(proyecto.get('developer', {}).get('name', '')),
        base=esc(base),
        dim_portada=dim(img(mp['stops'][0]['posterUrl'])),
        dim_logo=dim(logo),
        dim_plano=dim(img((plano or {}).get('url', ''))),
        dim_mapa=dim(img((mapa or {}).get('url', ''))),
        og_img=esc(base + 'assets/img/tarjeta-og.jpg'),
        jsonld=jsonld_seguro(ficha),
    )
    fecha = lastmod(html_out, date.today().isoformat())   # antes de pisar el index.html viejo
    (RAIZ / 'index.html').write_text(html_out, encoding='utf-8')
    escribir_sitemap_y_robots(base, fecha)
    sincronizar_csp(html_out)
    for r in faltan(html_out):
        print(f'  AVISO  la página nombra {r} y no está en el disco')
    print(f'index.html generado · {len(etapas)} etapas · {len(amenidades)} áreas comunes · '
          f'{len(clips)} clips · {len(libres)} lotes disponibles de {len(lotes)}')
    print(f'sitemap.xml y robots.txt apuntando a {base}')
    print(f'cifras: {", ".join(v + " " + t for v, t in cifras)}')


PLANTILLA = '''<!doctype html>
<html lang="es-PE">
<head>
<meta charset="utf-8">
<!-- esta línea va aquí y no en main.js: marca que hay JS ANTES de pintar, para que lo que
     sólo sirve con JS (el formulario) no aparezca y desaparezca. -->
<script>document.documentElement.classList.add('js')</script>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<meta name="description" content="{descripcion}">
<link rel="canonical" href="{base}">
<meta name="theme-color" content="#044048">

<!-- El icono de pestaña es el logo oficial sobre el verde de la marca: el logo que entregó
     Arquitectura es blanco y sobre una pestaña blanca no se vería. Los compone traer_medios.py. -->
<link rel="icon" href="assets/img/icono-32.png" sizes="32x32">
<link rel="icon" href="assets/img/icono-180.png" sizes="180x180">
<link rel="apple-touch-icon" href="assets/img/icono-180.png">

<!-- Cómo se ve el enlace cuando alguien lo pega en WhatsApp, que es por donde va a circular.
     La imagen tiene que ir con la dirección COMPLETA: una ruta relativa aquí no la resuelve
     nadie. De ahí el --url de generar.py. No se declaran og:image:width ni height porque
     tendría que teclearlos, y un tamaño teclado es un tamaño que algún día será mentira. -->
<meta property="og:type" content="website">
<meta property="og:site_name" content="{nombre}">
<meta property="og:locale" content="es_PE">
<meta property="og:url" content="{base}">
<meta property="og:title" content="{titulo}">
<meta property="og:description" content="{descripcion}">
<meta property="og:image" content="{og_img}">
<meta property="og:image:alt" content="Vista aérea de {nombre}">
<meta name="twitter:card" content="summary_large_image">

<!-- La ficha para los buscadores sale de los datos del tour: el nombre y la dirección son los
     que puso Arquitectura en location, y las coordenadas, las del ingreso al proyecto. -->
<script type="application/ld+json">{jsonld}</script>

<!-- Montserrat desde el propio sitio: la fuente de la marca, y la IP del visitante no viaja
     a Google por leer una página. Es una fuente variable: UN archivo trae los tres pesos, así
     que se precarga uno solo. Antes iban dos precargas de dos copias idénticas, y el navegador
     bajaba el mismo archivo dos y tres veces. El crossorigin NO es opcional en una fuente,
     aunque sea del mismo sitio. -->
<link rel="preload" as="font" type="font/woff2" href="assets/fuentes/montserrat-400-latin.woff2" crossorigin>
<link rel="stylesheet" href="assets/fuentes/montserrat.css">

<link rel="preload" as="image" href="{portada}" fetchpriority="high">
<link rel="stylesheet" href="assets/estilos.css">
</head>
<body>

<!-- Para quien navega con el teclado: lo primero que se enfoca es un enlace que salta los seis
     enlaces de la barra y va al contenido. Sólo se ve cuando tiene el foco. -->
<a class="salto" href="#contenido">Ir al contenido</a>

<!-- La barra va encima de la portada, transparente, y se vuelve verde al dejarla atrás. El logo
     es blanco —es el único que entregó Arquitectura—, así que la barra sólida NO puede ser
     blanca: sería un logo invisible. Verde marca y letras blancas, siempre las mismas.

     En pantalla estrecha los enlaces se desplazan de lado en vez de esconderse detrás de un
     botón de hamburguesa. Un menú que hay que abrir es una cosa más que puede fallar, y aquí
     todas las secciones caben de un toque. -->
<nav class="menu" aria-label="Secciones">
  <a class="menu__marca" href="#portada" aria-label="{nombre}, ir arriba">
    <!-- alt vacío: el enlace que lo envuelve ya lleva su propia etiqueta -->
    <img src="{logo}" alt=""{dim_logo}>
  </a>
  <ul class="menu__lista">
    <li><a href="#etapas">El proyecto</a></li>
    <li><a href="#plano">Plano</a></li>
    <li><a href="#areas">Áreas comunes</a></li>
    <li><a href="#galeria">Galería</a></li>
    <li><a href="#llegar">Cómo llegar</a></li>
    <li><a href="#contacto">Contacto</a></li>
  </ul>
</nav>

<header class="portada" id="portada">
  <!-- La foto se ve siempre y de inmediato; el vídeo entra encima cuando ha bajado lo
       suficiente. Si el visitante pidió ahorro de datos, o va por una conexión lenta, o tiene
       el movimiento reducido, el vídeo no se baja: se queda la foto. Eso lo decide main.js. -->
  <img class="portada__fondo" src="{portada}" alt="Vista aérea de {nombre}"{dim_portada} fetchpriority="high">
  <video class="portada__video" poster="{portada}" muted loop playsinline preload="none"
         data-720="assets/video/portada-720.mp4" data-1080="assets/video/portada-1080.mp4"
         aria-hidden="true"></video>
  <div class="portada__velo"></div>
  <div class="portada__centro">
    <!-- El logo ES el título de la página: su texto alternativo hace de h1. Antes la página no
         tenía ningún h1 y para un buscador —o para quien la lee con un lector de pantalla— eso
         es una página sin nombre. -->
    <h1 class="portada__titulo"><img class="portada__logo" src="{logo}" alt="{nombre} · {tagline}"{dim_logo}></h1>
    <p class="tagline">{tagline}</p>
    <p class="lead">{descripcion}</p>
    <div class="acciones">
      <a class="btn btn--primario" href="{tour}" target="_blank" rel="noopener">Recorrer el proyecto</a>
      <a class="btn" href="#contacto">Quiero información</a>
    </div>
  </div>
</header>

<main id="contenido">

<section class="seccion cifras" id="cifras" aria-labelledby="cifras-titulo">
  <!-- el título no se ve —las cifras se explican solas—, pero sin él la sección es un bloque
       sin nombre para quien la recorre por encabezados con un lector de pantalla -->
  <h2 class="oculto" id="cifras-titulo">Montelago en cifras</h2>
{cifras}
</section>

<section class="seccion" id="etapas">
  <h2>El proyecto, en tres etapas</h2>
  <div class="rejilla">
{etapas}
  </div>
</section>

<section class="seccion" id="plano">
  <h2>Dónde está cada cosa</h2>
  <img class="ancha" src="{plano_img}" alt="{plano_pie}"{dim_plano} loading="lazy" decoding="async">
  <p class="pie">{plano_pie}</p>
</section>

<section class="seccion" id="areas">
  <h2>Áreas comunes</h2>
  <div class="rejilla">
{amenidades}
  </div>
</section>

<section class="seccion" id="galeria">
  <h2>El proyecto en movimiento</h2>
  <!-- Cada recuadro es una foto hasta que alguien lo pide: el clip no se baja al entrar. Sin
       JS el enlace abre el vídeo en el navegador, que es lo que un enlace a un .mp4 hace. -->
  <div class="clips">
{clips}
  </div>
  <p class="pie">No son grabaciones del lugar: son los renders oficiales de Arquitectura,
     animados. El recorrido completo, con sonido y a pantalla llena, está en el tour.</p>
</section>

<section class="seccion" id="llegar">
  <h2>Cómo llegar</h2>
  <img class="ancha" src="{mapa_img}" alt="{mapa_pie}"{dim_mapa} loading="lazy" decoding="async">
  <p class="pie">{mapa_pie}</p>
</section>

<section class="seccion cierre" id="contacto">
  <h2>¿Te interesa un lote?</h2>
  <p>Escríbenos y te contamos qué lotes quedan, sus medidas y las formas de pago.</p>

  <!-- El formulario sólo aparece si hay JS, porque es JS quien arma el mensaje: un formulario
       sin sitio a donde enviar sería un botón que no hace nada. Sin JS quedan los dos enlaces
       de abajo, que funcionan solos. -->
  <form class="consulta" id="consulta" novalidate data-wa="{wa}" data-correo="{correo}">
    <div class="consulta__fila">
      <label class="campo">
        <span>Nombre</span>
        <input name="nombre" type="text" autocomplete="name" required>
        <small data-error="nombre"></small>
      </label>
      <label class="campo">
        <span>Teléfono</span>
        <input name="telefono" type="tel" autocomplete="tel" inputmode="tel" required>
        <small data-error="telefono"></small>
      </label>
    </div>
    <div class="consulta__fila">
      <label class="campo">
        <span>Correo</span>
        <input name="correo" type="email" autocomplete="email" inputmode="email" required>
        <small data-error="correo"></small>
      </label>
      <label class="campo">
        <span>¿Qué te interesa?</span>
        <select name="interes">
          <option>Un lote en la Etapa I</option>
          <option>La Etapa II</option>
          <option>La Etapa III</option>
          <option>Las áreas comunes</option>
          <option>Todavía no lo sé</option>
        </select>
      </label>
    </div>
    <label class="campo">
      <span>Mensaje <em>(opcional)</em></span>
      <textarea name="mensaje" rows="3" placeholder="Por ejemplo: busco desde 300 m², con vista a la laguna."></textarea>
    </label>
    <!-- trampa para robots: nadie la ve, y quien la llene no es una persona -->
    <div class="trampa" aria-hidden="true"><label>No escribir aquí<input name="web" tabindex="-1" autocomplete="off"></label></div>
    <button class="btn btn--primario consulta__enviar" type="submit">Enviar por WhatsApp</button>
    <p class="consulta__nota">Se abre WhatsApp con tus datos ya escritos; el mensaje lo envías tú.
       Esta página no guarda nada de lo que escribas.</p>
  </form>

  <p class="consulta__o">o escríbenos directo</p>
  <div class="acciones">
    <a class="btn btn--primario" href="https://wa.me/{wa}" target="_blank" rel="noopener">WhatsApp</a>
    <a class="btn" href="mailto:{correo}">{correo}</a>
  </div>
  <p class="nota">{aviso}</p>
</section>

</main>

<footer class="pie-web">
  <p>{empresa}</p>
  <p><a href="{tour}" target="_blank" rel="noopener">Recorrer el proyecto</a></p>
</footer>

<a class="fija btn btn--primario" href="#contacto">Quiero información</a>
<script src="assets/main.js" defer></script>
</body>
</html>
'''

if __name__ == '__main__':
    sys.exit(main())
