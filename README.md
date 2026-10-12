# Montelago · web de venta

Una sola página, de la aérea a pantalla completa hasta el formulario, para quien llega de un
anuncio y no va a recorrer el tour entero. Termina llevando al tour.

**Esto es un proyecto aparte del tour.** El tour vive en `../WEB3D` y se publica en
`montelago-tour.condominiosvillacasa.com`. Esta web no depende de él para funcionar: toma sus
textos e imágenes una vez, al generarse, y después es HTML plano.

## Qué hay aquí

```
index.html             generado — no editar a mano
assets/estilos.css     los colores y la retícula
assets/main.js         el único JS: aparecer al scroll, el botón fijo, el vídeo,
                       la galería y el formulario
assets/img/            renders oficiales copiados del tour (8 MB)
assets/video/          la aérea de la portada (720 y 1080) y los 7 clips en 720 (16 MB)
scripts/generar.py     arma index.html con los datos del tour
scripts/traer_medios.py  copia las imágenes y comprime el vídeo
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
```

Cuando cambie un estado o un precio en el Excel del inventario, se corre el importador del tour
y después esto: la página se entera sola. Hoy dice «68 disponibles» y «desde 243 m²» porque eso
es lo que hay.

Si llegan renders nuevos o clips nuevos:

```bash
python scripts/traer_medios.py            # copia imágenes y clips, comprime el de la portada
python scripts/generar.py
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
