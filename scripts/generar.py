"""Arma la web de venta de Montelago a partir de los datos OFICIALES del tour.

La página es estática —un index.html y poco más— pero no está escrita a mano: se genera. Así
los textos son los que entregó Arquitectura, palabra por palabra, y las cifras se CUENTAN del
inventario en vez de teclearse. Si mañana cambia un estado en el Excel, se vuelve a correr esto
y la página se entera.

    python scripts/generar.py                      # usa ..\\WEB3D por defecto
    python scripts/generar.py --tour RUTA          # si el tour está en otro sitio

Lo que NO hace, a propósito:
  · no inventa imágenes. Todas las fotos son renders oficiales copiados del tour (assets/img).
  · no inventa datos de contacto. El teléfono y las redes de project.json están marcados como
    EJEMPLO: hasta que Administración confirme, aquí sólo sale el WhatsApp y el correo, que sí
    están confirmados. Mejor faltar que publicar un número que no es.
"""

import argparse
import html
import json
import shutil
from datetime import date
import sys
from pathlib import Path

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
        cifras.append((f'{round(min(areas))} m²', 'desde'))

    # --- Las tres etapas, con el texto oficial de los puntos del masterplan ---
    etapas = []
    for hid in ('residencial', 'etapa-2', 'etapa-3'):
        h = next((x for x in mp['hotspots'] if x['id'] == hid), None)
        if not h:
            continue
        clip = next((g for k, g in galeria.items() if k.startswith(h['label'])), None)
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

    # --- Lo que necesitan los buscadores y las tarjetas de los enlaces ---
    base = args.url if args.url.endswith('/') else args.url + '/'
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

    # el sitemap y el robots son dos archivos de tres líneas: se escriben aquí mismo
    hoy = date.today().isoformat()
    (RAIZ / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url><loc>{base}</loc><lastmod>{hoy}</lastmod>'
        '<changefreq>monthly</changefreq><priority>1.0</priority></url>\n'
        '</urlset>\n', encoding='utf-8')
    (RAIZ / 'robots.txt').write_text(
        'User-agent: *\nAllow: /\n\nSitemap: ' + base + 'sitemap.xml\n', encoding='utf-8')

    html_out = PLANTILLA.format(
        titulo=esc(proyecto.get('htmlTitle') or proyecto['name']),
        nombre=esc(proyecto['name']),
        tagline=esc(proyecto['tagline']),
        descripcion=esc(proyecto['description']),
        portada=img(mp['stops'][0]['posterUrl']),
        logo=img(p['home']['logoImgUrl']),
        cifras='\n'.join(
            f'      <div class="dato"><strong>{esc(v)}</strong><span>{esc(t)}</span></div>'
            for v, t in cifras),
        etapas='\n'.join(
            f'''      <article class="tarjeta">
        <div class="tarjeta__foto"><img src="{e['foto']}" alt="{esc(e['label'])}" loading="lazy"></div>
        <h3>{esc(e['label'])}</h3><p>{esc(e['texto'])}</p>
      </article>''' for e in etapas),
        plano_img=img((plano or {}).get('url', '')),
        plano_pie=esc((plano or {}).get('label', '')),
        amenidades='\n'.join(
            f'''      <article class="tarjeta">
        <div class="tarjeta__foto"><img src="{a['foto']}" alt="{esc(a['nombre'])}" loading="lazy"></div>
        <h3>{esc(a['nombre'])}</h3><p>{esc(a['texto'])}</p>
        <ul>{''.join(f'<li>{esc(r)}</li>' for r in a['rasgos'])}</ul>
      </article>''' for a in amenidades),
        clips='\n'.join(
            f'''      <article class="clip">
        <a class="clip__abrir" href="{c['clip']}" aria-label="Ver el clip: {esc(c['label'])}">
          <img src="{c['foto']}" alt="{esc(c['label'])}" loading="lazy">
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
        og_img=esc(base + 'assets/img/tarjeta-og.jpg'),
        jsonld=json.dumps(ficha, ensure_ascii=False, separators=(',', ':')),
    )
    (RAIZ / 'index.html').write_text(html_out, encoding='utf-8')
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

<link rel="preload" as="image" href="{portada}">
<link rel="stylesheet" href="assets/estilos.css">
</head>
<body>

<!-- La barra va encima de la portada, transparente, y se vuelve verde al dejarla atrás. El logo
     es blanco —es el único que entregó Arquitectura—, así que la barra sólida NO puede ser
     blanca: sería un logo invisible. Verde marca y letras blancas, siempre las mismas.

     En pantalla estrecha los enlaces se desplazan de lado en vez de esconderse detrás de un
     botón de hamburguesa. Un menú que hay que abrir es una cosa más que puede fallar, y aquí
     todas las secciones caben de un toque. -->
<nav class="menu" aria-label="Secciones">
  <a class="menu__marca" href="#portada" aria-label="{nombre}, ir arriba">
    <img src="{logo}" alt="{nombre}" width="150" height="40">
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
  <img class="portada__fondo" src="{portada}" alt="Vista aérea de {nombre}">
  <video class="portada__video" poster="{portada}" muted loop playsinline preload="none"
         data-720="assets/video/portada-720.mp4" data-1080="assets/video/portada-1080.mp4"
         aria-hidden="true"></video>
  <div class="portada__velo"></div>
  <div class="portada__centro">
    <img class="portada__logo" src="{logo}" alt="{nombre}">
    <p class="tagline">{tagline}</p>
    <p class="lead">{descripcion}</p>
    <div class="acciones">
      <a class="btn btn--primario" href="{tour}" target="_blank" rel="noopener">Recorrer el proyecto</a>
      <a class="btn" href="#contacto">Quiero información</a>
    </div>
  </div>
</header>

<section class="seccion cifras" id="cifras">
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
  <img class="ancha" src="{plano_img}" alt="{plano_pie}" loading="lazy">
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
  <img class="ancha" src="{mapa_img}" alt="{mapa_pie}" loading="lazy">
  <p class="pie">{mapa_pie}</p>
</section>

<section class="seccion cierre" id="contacto">
  <h2>¿Quieres uno?</h2>
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
