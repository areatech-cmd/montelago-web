# Montelago · web de venta

Una sola página, de la aérea a pantalla completa hasta el formulario, para quien llega de un
anuncio y no va a recorrer el tour entero. Termina llevando al tour.

Por orden: portada con el vídeo, el lema sobre la toma cenital, el recorrido sobre la aérea, las
cifras, las tres etapas, el plano, las áreas comunes (la Laguna artificial 1 y el Club House a
pantalla completa con su clip de fondo, y las demás en rejilla), la galería de clips, cómo llegar
y el formulario. Arriba a la izquierda, siempre a la vista, una píldora con el menú y «Quiero
información».

La composición sigue la de damare.gt —oscuro, mucha imagen, poco texto, mayúsculas finas y
espaciadas, una línea manuscrita de acento— con los colores de Montelago. Su pieza central, el
**recorrido**, es la aérea oficial de la portada con los puntos oficiales del masterplan del tour:
al bajar, la cámara va de la entrada a la segunda laguna y en cada punto sale su nombre y su
texto. No es un render nuevo ni un plano dibujado aquí: es la misma imagen y los mismos puntos que
el tour. Monte Hermoso, el condominio vecino, no entra. Con movimiento reducido es la foto con los
puntos numerados; sin JS, la foto y la lista.

Las cuatro frases que no vienen del tour (el titular de la portada, la línea manuscrita y el
texto de la vista general del recorrido) están juntas al principio de `scripts/generar.py`, para
cambiarlas sin buscar.

**Esto es un proyecto aparte del tour.** El tour vive en `../WEB3D` y se publica en
`montelago-tour.condominiosvillacasa.com`. Esta web no depende de él para funcionar: toma sus
textos e imágenes una vez, al generarse, y después es HTML plano.

## Qué hay aquí

```
index.html             generado — no editar a mano
assets/estilos.css     los colores y la retícula
assets/main.js         el único JS: aparecer al scroll, el menú, los dos vídeos de
                       fondo, el recorrido, la galería y el formulario
assets/img/            renders oficiales copiados del tour (8 MB)
assets/video/          la aérea de la portada (720 y 1080) y los 7 clips en 720 (16 MB)
assets/fuentes/        Montserrat variable (un archivo, del 300 al 700, 38 KB) y la manuscrita
                       Allura (26 KB, licencia OFL al lado)
scripts/generar.py     arma index.html con los datos del tour
scripts/traer_medios.py  copia imágenes y clips, y compone el icono y la tarjeta
sitemap.xml, robots.txt  generados
_headers               cuánto puede guardar en caché cada cosa
```

Los vídeos pesan 16 MB y viven en el repositorio. Cada vez que se vuelva a comprimir uno, el
historial se queda también con la copia vieja: conviene no recomprimirlos por gusto. De los
clips de la galería se trae sólo la versión de 720 —en 1080 serían 17 MB en vez de 5, y en un
recuadro no se distinguen—; el que los quiera en grande tiene el tour.

## Cómo se actualiza

La página **no está escrita a mano, se genera**. Así los textos son los que entregó
Arquitectura, palabra por palabra, y las cifras se *cuentan* del inventario en vez de teclearse.

```bash
python scripts/generar.py                 # usa ../WEB3D
python scripts/generar.py --tour RUTA     # si el tour está en otro sitio
python scripts/generar.py --url https://montelago.condominiosvillacasa.com/
```

Lo de `--url` no es un adorno: la tarjeta que se ve al pegar el enlace en WhatsApp, la etiqueta
canónica y el sitemap necesitan la dirección **completa**. Por defecto apunta a la de GitHub
Pages; el día que el sitio se mude, se genera con `--url` y queda todo apuntando bien.

Cuando cambie un estado o un precio en el Excel del inventario, se corre el importador del tour
y después esto: la página se entera sola. Hoy dice «68 disponibles» y «desde 243 m²» porque eso
es lo que hay.

Si llegan renders nuevos o clips nuevos:

```bash
python scripts/traer_medios.py            # copia imágenes y clips, comprime lo que haga falta
python scripts/generar.py
```

El vídeo de la portada **no se vuelve a comprimir si ya está**: x264 con varios hilos no da dos
veces el mismo archivo, y cada pasada de más sería un blob de 7 MB nuevo en el historial sin que
haya cambiado nada. Si Arquitectura manda un vídeo nuevo, `--rehacer`.

```bash
python scripts/traer_medios.py --rehacer  # fuerza la recompresión
```

La galería se arma con los clips que el tour tenga en `gallery.items`: si mañana Arquitectura
manda uno más y entra al tour, aquí sale solo.

## Cómo se publica

Es estática: sirve la carpeta y ya. No hay build, ni dependencias, ni Node.

```bash
python -m http.server 4500      # para verla en local
```

Está en **github.com/areatech-cmd/montelago-web**, repositorio **público**, y se publica sola con
**GitHub Pages** desde `main`:

> https://areatech-cmd.github.io/montelago-web/

Cada `git push` a `main` la actualiza en un par de minutos. No hay que tocar nada más.

### Cuando haya que moverla al dominio de la empresa

Pages está bien para enseñarla y para los anuncios de prueba, pero deja una dirección
`github.io`. El sitio definitivo debería ir al dominio de Villacasa, y lo más corto es
**Cloudflare Pages**, que es donde ya vive el tour: ahí el subdominio y el certificado salen
solos. Es una conexión que se hace una vez desde el panel, con la cuenta de la empresa:

1. Cloudflare → **Workers & Pages** → *Create* → *Pages* → **Connect to Git**.
2. Elegir el repositorio `montelago-web`.
3. **Framework preset:** None. **Build command:** vacío. **Output directory:** `/`.
   No hay build: la carpeta ya es el sitio.
4. *Save and Deploy*. Después, en **Custom domains**, el subdominio que se quiera —por ejemplo
   `montelago.condominiosvillacasa.com`.

Los dos sitios pueden convivir: Pages para probar, Cloudflare para la dirección de verdad.

### Que el repositorio sea público, qué significa

Cualquiera puede leer el código y descargar los renders. Se decidió a sabiendas, porque Pages
gratis lo exige. Lo que **no** está aquí sigue sin estar: el Excel del inventario con los
nombres de los clientes y de las asesoras, los precios cash y cualquier credencial. Esta página
sólo publica lo que de todas formas se le enseña a quien pregunta.

## Detalles que parecen pequeños y no lo son

**Las medidas de cada imagen se leen del archivo, no se teclean.** Van en el HTML para que el
navegador reserve el hueco antes de bajar la foto; sin eso el texto baja de golpe cada vez que
aparece una imagen y la página salta mientras se lee. Las lee `generar.py` de la cabecera del
WebP o del PNG —treinta líneas, sin depender de Pillow—, porque un tamaño teclado sobrevive al
render que lo reemplaza y entonces miente.

**La fuente se sirve desde aquí.** Montserrat es la de la marca; sin ella la página caía a la
del sistema y no se parecía. Van tres pesos y sólo la subserie *latin*, que cubre tildes, ñ, ·
y ² —todo lo que hay en un texto en español—. Se sirve desde el propio sitio, como en el tour:
así la IP del visitante no viaja a Google por el hecho de leer una página.

**Lo que pesa la primera carga: 760 KB**, de los cuales 577 son la aérea de la portada. Se midió
si convenía recomprimirla y **no**: al 60 % de calidad baja a 384 KB, y recomprimir un WebP ya
comprimido sólo degrada. Es un render oficial a 1920x1080 detrás de un velo, y en un móvil en
vertical el recorte *cover* necesita más ancho, no menos, así que tampoco sirve una variante
pequeña. El logo sí bajó de 59 a 29 KB pasándolo a WebP **sin pérdida**: los mismos píxeles
exactos, la mitad del peso. El vídeo y los clips no cuentan aquí: no se bajan hasta que hace
falta.

**Se puede recorrer con el teclado.** Lo primero que se enfoca es un salto al contenido, el
foco se ve sobre cualquier fondo, el logo de la portada hace de `h1` y el formulario marca el
campo mal escrito con `aria-invalid`, no sólo con un borde rojo que nadie oye.

## Dos reglas que este proyecto hereda del tour

**Ni una imagen generada por IA.** Todas las fotos son renders oficiales de Arquitectura. La IA
puede animar o retocar lo que ellos entregaron; no puede inventar el proyecto. Una aérea
inventada, enseñada a alguien que va a comprar un lote, es exactamente lo que esa regla evita.

**No se publica el precio cash.** Es el piso de negociación de Comercial. Esta página no publica
precios en absoluto: lleva a preguntar.

## Lo que falta, y de quién depende

- **Teléfono y redes sociales.** En los datos del tour están marcados como EJEMPLO y las redes
  apuntan a `facebook.com` a secas. Por eso aquí sólo salen el WhatsApp y el correo, que sí
  están confirmados. Son las consultas 11 y 14 del documento de pendientes.
- **Dónde aterrizan las consultas.** El formulario ya está, pero no envía a ningún servidor:
  arma el mensaje y abre WhatsApp con todo escrito, y lo manda la persona. Se hizo así a
  propósito —esta página es estática y no tiene a dónde enviar nada—, y tiene una ventaja: al no
  guardar datos, no hace falta pedir autorización ni publicar un aviso de privacidad.

  El día que Administración decida que las consultas van a un registro (una hoja, el CRM, Odoo),
  hay que añadir **la casilla de autorización de datos y un aviso de privacidad con el RUC**, que
  sigue pendiente. El formato del mensaje es ya el mismo que usa el tour (`sendLead` en
  `src/project.js`), así que a Comercial le llegan iguales vengan de donde vengan.
