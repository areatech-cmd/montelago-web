# Montelago · web de venta

Una sola página, de la aérea a pantalla completa hasta el formulario, para quien llega de un
anuncio y no va a recorrer el tour entero. Termina llevando al tour.

**Esto es un proyecto aparte del tour.** El tour vive en `../WEB3D` y se publica en
`montelago-tour.condominiosvillacasa.com`. Esta web no depende de él para funcionar: toma sus
textos e imágenes una vez, al generarse, y después es HTML plano.

## Qué hay aquí

```
index.html          generado — no editar a mano
assets/estilos.css  los colores y la retícula
assets/main.js      lo único con JS: las secciones aparecen al hacer scroll
assets/img/         renders oficiales copiados del tour (8 MB)
scripts/generar.py  arma index.html con los datos del tour
```

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

Si llegan renders nuevos, se copian a `assets/img/` con el mismo nombre y se vuelve a generar.

## Cómo se publica

Es estática: sirve la carpeta y ya. No hay build, ni dependencias, ni Node.

```bash
python -m http.server 4500      # para verla en local
```

Para publicarla, cualquier hosting estático sirve (Cloudflare Pages, Netlify, el mismo VPS).
Conviene darle su propio dominio o un subdominio, no colgarla del tour.

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
- **Formulario propio.** Hoy el botón lleva a WhatsApp y a correo. Un formulario con captura de
  datos necesita decidir dónde aterrizan esos datos (el tour los manda a WhatsApp) y un aviso de
  privacidad con el RUC de la empresa, que también está pendiente.
