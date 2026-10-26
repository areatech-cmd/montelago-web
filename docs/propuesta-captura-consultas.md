# Propuesta: que las consultas del formulario queden registradas

> **NADA DE ESTO ESTÁ ACTIVO.** Es una propuesta para cuando Administración decida a dónde van
> las consultas. El código de abajo vive en este documento y no en el sitio a propósito: en
> Cloudflare Pages, una carpeta `functions/` en la raíz del repositorio **se ejecuta sola** en
> el siguiente despliegue. No crear esa carpeta hasta que esté todo lo de la
> [lista de activación](#lista-de-activación) resuelto.
>
> Y aunque se creara, en GitHub Pages —donde está la web hoy— no se ejecutaría: Pages sólo sirve
> archivos. Esto exige antes la mudanza a Cloudflare que describe el README.

## Por qué hace falta, y por qué no se hizo ya

Hoy el formulario arma el mensaje y abre WhatsApp con todo escrito; lo envía la persona. La
página no guarda nada, y por eso no necesita ni casilla de autorización ni aviso de privacidad.
Eso fue deliberado y sigue siendo una buena forma de empezar.

Lo que se pierde: quien rellena el formulario y **no** pulsa *enviar* en WhatsApp (o no tiene
WhatsApp en ese aparato, o se distrae) no deja rastro. Para una página que va a recibir
tráfico pagado, esas son las consultas más caras. Y no hay forma de saber cuántas llegan por
cada anuncio.

En el momento en que la página **guarde** datos, la Ley N.º 29733 de Protección de Datos
Personales pide consentimiento previo, expreso e informado, y un aviso con quién es el
responsable —razón social y RUC—, para qué se usan, cuánto se guardan y cómo pedir que se
borren. El RUC y el aviso son justo lo que el README marca como pendiente. **Sin eso, no se
activa.**

## Cómo queda

```
navegador ── clic en «Enviar»
   │
   ├─(1) abre WhatsApp con el mensaje, como hoy. Va primero y sin esperar a nada: si se retrasa,
   │      el navegador lo toma por ventana emergente y lo bloquea.
   │
   └─(2) a la vez, POST /api/consulta  (fetch con keepalive: sobrevive aunque la página se vaya)
              │
              ▼
   Cloudflare Pages Function  functions/api/consulta.js
     1. ¿viene de nuestra página?          Origin en la lista            → si no, 403
     2. ¿tamaño y formato razonables?      JSON, < 8 KB                  → 413 / 415 / 400
     3. ¿es un robot tonto?                la casilla trampa «web»       → 200 falso, no se guarda
     4. ¿es un robot listo?                Turnstile, verificado aquí    → 403
     5. ¿los datos tienen sentido?         validación campo a campo      → 422 con los campos
     6. ¿autorizó?                         casilla + versión del aviso   → 422
     7. ¿está insistiendo?                 ≤ 5 por IP cada 10 min (D1)   → 429
     8. GUARDAR en D1                      la fuente de verdad, primero
     9. reenviar (hoja / Odoo / correo)    después, en segundo plano; si falla, queda marcado
                                           en D1 como pendiente y no se pierde nada
              ▼
            201 { ok, id }
```

Dos decisiones de diseño que conviene ver claras:

- **WhatsApp sigue siendo el canal principal.** El registro es un efecto secundario. Si la
  función falla, la persona igual llega a WhatsApp y no se entera de nada. Lo contrario
  —esperar al servidor y *luego* abrir WhatsApp— hace que el navegador bloquee la ventana.
- **Primero se guarda, después se reenvía.** Una hoja de Google o un Odoo pueden estar caídos
  o lentos; D1 está en el mismo sitio que la función. Si el reenvío falla, la consulta está en
  D1 con `reenviado_en` vacío y se puede reenviar después. Nunca se pierde una consulta porque
  el CRM estaba en mantenimiento.

Consecuencia que Comercial tiene que saber: si la persona además envía el WhatsApp, la misma
consulta llega **dos veces** (por WhatsApp y por el registro). El teléfono es la clave para
juntarlas; el mensaje de WhatsApp ya tiene el mismo formato que el del tour.

## Qué decide el negocio

| Decisión | Opciones | Recomendación |
|---|---|---|
| ¿A dónde llegan? | Hoja de Google · Odoo (CRM) · correo a ventas@ | Odoo si ya se usa para el tour; si no, hoja. El correo sólo como aviso, no como registro: un buzón no es una base de datos. |
| ¿Cuánto se guardan? | 6 / 12 / 24 meses | 12 meses desde la última interacción. Lo que dure la venta de la Etapa I, como mucho. |
| ¿Se pide permiso para publicidad? | No · casilla aparte, opcional | Casilla aparte y **sin marcar**. Mezclarla con la obligatoria invalida las dos. |
| ¿Quién responde a «borren mis datos»? | Un correo, una persona | Un buzón tipo `privacidad@condominiosvillacasa.com` con responsable nombrado. |
| ¿Qué pasa con la copia de github.io? | Despublicarla · dejarla sin formulario | Despublicar GitHub Pages al terminar la mudanza: allí la función no existe y el registro fallaría siempre. |
| ¿Se inscribe el banco de datos? | — | Lo exige la ley: banco «prospectos / clientes potenciales» ante la Autoridad Nacional de Protección de Datos Personales. Lo tramita Legal. |

## El código

Todo lo de esta sección es para copiar **el día que se active**, no antes.

### 1. `functions/api/consulta.js`

```js
// NO ACTIVO hasta que se apruebe: ver docs/propuesta-captura-consultas.md
//
// Recibe una consulta del formulario, la valida, la guarda en D1 y la reenvía al destino que
// decida Administración. Nunca escribe en los registros ni el nombre, ni el teléfono, ni el
// correo: sólo el id de la consulta, el código del error y un trozo del hash de la IP. Si
// alguien tiene que mirar los registros de Cloudflare, no tiene por qué ver datos personales.

// La versión del aviso de privacidad que la persona aceptó. Si se cambia el texto del aviso,
// se sube esta fecha, y la página tiene que mandar la misma: así se sabe qué aceptó cada uno.
const VERSION_AVISO = '2026-11-01'

const INTERESES = new Set([
  'Un lote en la Etapa I',
  'La Etapa II',
  'La Etapa III',
  'Las áreas comunes',
  'Todavía no lo sé',
])

const MAX_BYTES = 8 * 1024           // un formulario lleno ocupa menos de 2 KB
const VENTANA_MIN = 10               // límite por IP: cuántas consultas en cuántos minutos
const MAX_POR_VENTANA = 5
const MESES_RETENCION = 12
const TIMEOUT_MS = 5000              // para Turnstile y para el reenvío: nada espera más que esto

export async function onRequestPost(context) {
  const { request, env } = context
  const id = crypto.randomUUID()

  try {
    // 1. Sólo desde nuestra página. No es una barrera contra un script hecho a propósito
    //    (el Origin se puede falsificar fuera de un navegador; para eso está Turnstile), pero
    //    corta de raíz que otra web use este formulario desde el navegador de sus visitantes.
    const origen = request.headers.get('Origin') || ''
    const permitidos = (env.ORIGENES_PERMITIDOS || '').split(',').map((s) => s.trim())
    if (!permitidos.includes(origen)) return error(403, 'origen_no_permitido', id)

    // 2. Formato y tamaño, antes de leer nada
    if (!(request.headers.get('Content-Type') || '').startsWith('application/json')) {
      return error(415, 'tipo_no_admitido', id)
    }
    if (Number(request.headers.get('Content-Length') || 0) > MAX_BYTES) {
      return error(413, 'demasiado_grande', id)
    }
    const crudo = await request.text()
    if (crudo.length > MAX_BYTES) return error(413, 'demasiado_grande', id)
    let d
    try {
      d = JSON.parse(crudo)
    } catch {
      return error(400, 'json_invalido', id)
    }
    if (!d || typeof d !== 'object') return error(400, 'json_invalido', id)

    // 3. La trampa. Se contesta como si hubiera ido bien: a un robot no se le enseña qué lo
    //    delató.
    if (d.web) {
      log('info', id, 'trampa')
      return json(201, { ok: true, id })
    }

    // 4. Turnstile: el token lo da el widget en la página y se comprueba AQUÍ, con la clave
    //    secreta. Comprobarlo sólo en el navegador no sirve de nada.
    const ip = request.headers.get('CF-Connecting-IP') || ''
    if (!(await turnstileValido(env, d.turnstile, ip, id))) {
      return error(403, 'verificacion_fallida', id)
    }

    // 5 y 6. Los datos y la autorización
    const { datos, errores } = validar(d)
    if (errores) return json(422, { error: 'datos_invalidos', campos: errores, id })

    // 7. Límite por IP. La IP no se guarda tal cual: se guarda su hash con una sal secreta,
    //    que sirve para contar y no para saber quién es.
    const ipHash = await sha256((env.SAL_IP || '') + ip)
    const recientes = await env.DB.prepare(
      `SELECT COUNT(*) AS n FROM consultas
        WHERE ip_hash = ?1 AND creado > datetime('now', ?2)`,
    ).bind(ipHash, `-${VENTANA_MIN} minutes`).first('n')
    if (recientes >= MAX_POR_VENTANA) {
      return error(429, 'demasiadas_consultas', id, { 'Retry-After': String(VENTANA_MIN * 60) })
    }

    // 8. Guardar. clave_idempotencia es UNIQUE: si el navegador reintenta el mismo envío
    //    (red móvil que se corta y vuelve), no sale una consulta repetida.
    const res = await env.DB.prepare(
      `INSERT INTO consultas
         (id, clave_idempotencia, nombre, telefono, correo, interes, mensaje,
          aviso_version, acepta_publicidad, ip_hash, user_agent,
          utm_source, utm_medium, utm_campaign, borrar_despues_de)
       VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14,
               datetime('now', ?15))
       ON CONFLICT (clave_idempotencia) DO NOTHING`,
    ).bind(
      id, datos.clave, datos.nombre, datos.telefono, datos.correo, datos.interes,
      datos.mensaje, VERSION_AVISO, datos.publicidad ? 1 : 0, ipHash,
      (request.headers.get('User-Agent') || '').slice(0, 300),
      datos.utm_source, datos.utm_medium, datos.utm_campaign,
      `+${MESES_RETENCION} months`,
    ).run()

    if (!res.meta.changes) {
      log('info', id, 'repetida')
      return json(200, { ok: true, repetida: true })
    }

    // 9. Reenviar sin hacer esperar a la persona. Si falla, queda anotado en D1.
    context.waitUntil(reenviar(env, id, datos))

    log('info', id, 'guardada')
    return json(201, { ok: true, id })
  } catch (e) {
    log('error', id, 'interno', { msg: String(e && e.message).slice(0, 200) })
    return error(500, 'interno', id)
  }
}

// --- Validación ---------------------------------------------------------------------------

function texto(v, max) {
  // fuera los caracteres de control (salvo el salto de línea), y recortado
  return String(v ?? '').replace(/[\u0000-\u0009\u000B-\u001F\u007F]/g, '').trim().slice(0, max)
}

function validar(d) {
  const errores = {}
  const nombre = texto(d.nombre, 80)
  if (nombre.length < 2) errores.nombre = 'Escribe tu nombre'

  // Perú: celular de 9 cifras que empieza por 9, con o sin +51. Del extranjero: de 8 a 15
  // cifras con el prefijo del país (E.164). Se guarda sólo con cifras y el +.
  const tel = String(d.telefono ?? '').replace(/[\s().-]/g, '')
  let telefono = ''
  if (/^(\+?51)?9\d{8}$/.test(tel)) telefono = '+51' + tel.slice(-9)
  else if (/^\+[1-9]\d{7,14}$/.test(tel)) telefono = tel
  else errores.telefono = 'Revisa el teléfono'

  const correo = texto(d.correo, 254).toLowerCase()
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(correo)) errores.correo = 'Revisa el correo'

  const interes = texto(d.interes, 60)
  if (!INTERESES.has(interes)) errores.interes = 'Elige una opción'

  const mensaje = texto(d.mensaje, 1000)

  // La autorización: tiene que venir marcada, y para la MISMA versión del aviso que está
  // publicada. Si la página es vieja y el aviso cambió, se le pide que recargue.
  if (d.autoriza !== true) errores.autoriza = 'Necesitamos tu autorización para responderte'
  else if (d.aviso_version !== VERSION_AVISO) errores.autoriza = 'El aviso cambió: recarga la página'

  const clave = texto(d.clave, 64)
  if (!/^[0-9a-f-]{36}$/i.test(clave)) errores.clave = 'falta'

  const utm = (k) => texto(d[k], 100) || null

  if (Object.keys(errores).length) return { errores }
  return {
    datos: {
      clave, nombre, telefono, correo, interes, mensaje: mensaje || null,
      publicidad: d.publicidad === true,
      utm_source: utm('utm_source'), utm_medium: utm('utm_medium'), utm_campaign: utm('utm_campaign'),
    },
  }
}

// --- Turnstile -----------------------------------------------------------------------------

async function turnstileValido(env, token, ip, id) {
  if (typeof token !== 'string' || !token || token.length > 2048) return false
  const cuerpo = new FormData()
  cuerpo.append('secret', env.TURNSTILE_SECRET)
  cuerpo.append('response', token)
  if (ip) cuerpo.append('remoteip', ip)
  cuerpo.append('idempotency_key', id)
  try {
    const r = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
      method: 'POST', body: cuerpo, signal: AbortSignal.timeout(TIMEOUT_MS),
    })
    const v = await r.json()
    // además de «success», que el token sea de NUESTRO widget y para ESTA acción: un token
    // sacado de otra página con la misma cuenta no vale aquí
    const host = (env.ORIGENES_PERMITIDOS || '').split(',').map((o) => o.trim().replace(/^https:\/\//, ''))
    const ok = v.success === true && v.action === 'consulta' && host.includes(v.hostname)
    if (!ok) log('info', id, 'turnstile_rechazado', { codigos: v['error-codes'] })
    return ok
  } catch (e) {
    // Si Turnstile no contesta, se rechaza: la persona igual tiene su WhatsApp abierto.
    log('error', id, 'turnstile_sin_respuesta', { msg: String(e && e.message).slice(0, 200) })
    return false
  }
}

// --- Reenvío -------------------------------------------------------------------------------
//
// Una sola función con un webhook genérico: vale para una hoja de Google (Apps Script) o para
// un Make/Zapier/n8n. Para Odoo, ver la variante más abajo. El secreto va en el cuerpo y no en
// una cabecera porque Apps Script no deja leer las cabeceras de la petición.

async function reenviar(env, id, datos) {
  try {
    const r = await fetch(env.WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ secreto: env.WEBHOOK_SECRETO, id, origen: 'web-montelago', ...datos }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    })
    if (!r.ok) throw new Error('HTTP ' + r.status)
    await env.DB.prepare(`UPDATE consultas SET reenviado_en = datetime('now'), reenvio_error = NULL WHERE id = ?1`)
      .bind(id).run()
    log('info', id, 'reenviada')
  } catch (e) {
    await env.DB.prepare(`UPDATE consultas SET reenvio_error = ?2 WHERE id = ?1`)
      .bind(id, String(e && e.message).slice(0, 200)).run()
    log('error', id, 'reenvio_fallido', { msg: String(e && e.message).slice(0, 200) })
  }
}

// --- Utilidades ----------------------------------------------------------------------------

async function sha256(s) {
  const h = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s))
  return [...new Uint8Array(h)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

function json(status, cuerpo, extra = {}) {
  return new Response(JSON.stringify(cuerpo), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', ...extra },
  })
}

function error(status, codigo, id, extra) {
  log(status >= 500 ? 'error' : 'info', id, codigo)
  return json(status, { error: codigo, id }, extra)
}

function log(nivel, id, evento, extra = {}) {
  console.log(JSON.stringify({ nivel, id, evento, ...extra }))
}
```

**Variante Odoo** (si el destino es el CRM): en lugar del `fetch` al webhook, una llamada
JSON-RPC que crea una oportunidad. La clave es una *API key* de un usuario de Odoo creado sólo
para esto, con permiso únicamente de crear en CRM.

```js
async function crearEnOdoo(env, id, d) {
  const r = await fetch(env.ODOO_URL + '/jsonrpc', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal: AbortSignal.timeout(TIMEOUT_MS),
    body: JSON.stringify({
      jsonrpc: '2.0', method: 'call', id: 1,
      params: {
        service: 'object', method: 'execute_kw',
        args: [env.ODOO_DB, Number(env.ODOO_UID), env.ODOO_API_KEY, 'crm.lead', 'create', [{
          name: `Web Montelago · ${d.interes}`,
          contact_name: d.nombre, email_from: d.correo, phone: d.telefono,
          description: d.mensaje || '',
          // ref: id  → para poder cruzarla con D1
        }]],
      },
    }),
  })
  const v = await r.json()
  if (v.error) throw new Error('Odoo: ' + (v.error.data?.name || v.error.message))
}
```

### 2. `_routes.json` (en la raíz, junto con `functions/`)

Sin esto, **cada** petición del sitio —cada imagen, cada trozo de vídeo— pasaría por la función
antes de servirse, y contaría para el límite gratuito de 100 000 invocaciones al día. Con esto
sólo `/api/*` la toca; lo demás se sirve directo como hoy.

```json
{ "version": 1, "include": ["/api/*"], "exclude": [] }
```

### 3. La tabla en D1 (`docs/consultas.sql` cuando se active; se corre una vez)

```sql
-- Una fila por consulta. Lo que identifica a la persona (nombre, teléfono, correo) es lo
-- mínimo para responderle; la IP NO se guarda, sólo su hash con sal, para el límite.
CREATE TABLE consultas (
  id                  TEXT PRIMARY KEY,
  clave_idempotencia  TEXT NOT NULL UNIQUE,
  creado              TEXT NOT NULL DEFAULT (datetime('now')),
  nombre              TEXT NOT NULL,
  telefono            TEXT NOT NULL,
  correo              TEXT NOT NULL,
  interes             TEXT NOT NULL,
  mensaje             TEXT,
  aviso_version       TEXT NOT NULL,          -- qué texto del aviso aceptó
  acepta_publicidad   INTEGER NOT NULL DEFAULT 0,
  ip_hash             TEXT NOT NULL,
  user_agent          TEXT,
  utm_source          TEXT,
  utm_medium          TEXT,
  utm_campaign        TEXT,
  reenviado_en        TEXT,                    -- NULL = todavía no llegó al destino
  reenvio_error       TEXT,
  borrar_despues_de   TEXT NOT NULL
);
CREATE INDEX idx_consultas_ip_creado  ON consultas (ip_hash, creado);
CREATE INDEX idx_consultas_pendientes ON consultas (creado) WHERE reenviado_en IS NULL;
CREATE INDEX idx_consultas_caducan    ON consultas (borrar_despues_de);
```

Mantenimiento (una vez al mes, o con un Worker programado si se quiere automático):

```sql
-- lo que no llegó al destino: reenviar a mano o con un script
SELECT id, creado, reenvio_error FROM consultas WHERE reenviado_en IS NULL ORDER BY creado;
-- lo que ya cumplió su plazo
DELETE FROM consultas WHERE borrar_despues_de < datetime('now');
-- alguien pide que se borren sus datos (derecho de cancelación)
DELETE FROM consultas WHERE correo = ?1 OR telefono = ?2;
```

### 4. Configuración en el panel de Cloudflare (proyecto de Pages → *Settings*)

| Qué | Nombre | Valor |
|---|---|---|
| Enlace D1 | `DB` | la base `montelago-consultas` |
| Variable | `ORIGENES_PERMITIDOS` | `https://montelago.condominiosvillacasa.com` |
| Secreto | `TURNSTILE_SECRET` | la clave secreta del widget de Turnstile |
| Secreto | `SAL_IP` | 32 caracteres al azar (`openssl rand -hex 16`) |
| Secreto | `WEBHOOK_URL`, `WEBHOOK_SECRETO` | los del destino elegido |
| (Odoo) | `ODOO_URL`, `ODOO_DB`, `ODOO_UID`, `ODOO_API_KEY` | los del usuario de integración |

Los secretos van **sólo** en el panel. Para probar en local con `wrangler pages dev`, en un
`.dev.vars` que ya está en `.gitignore`.

Además, en *Security → WAF → Rate limiting rules*, una regla para la ruta: `URI Path equals
/api/consulta` y `Method equals POST`, más de 3 peticiones en 10 segundos por IP → bloquear.
El plan gratuito sólo deja ventanas de 10 s; el límite largo (5 cada 10 min) lo hace la
función con D1. Las dos capas se complementan: la del WAF corta la ráfaga antes de que cueste
nada, la de D1 corta al insistente.

## Lo que cambia en la página (para quien lleve el frontend)

Esto no se toca hasta activar, y lo hace quien lleve `main.js` y la plantilla de `generar.py`:

1. **El widget de Turnstile** dentro del formulario, en modo que casi nunca se ve:

   ```html
   <div class="cf-turnstile" data-sitekey="CLAVE_PUBLICA" data-action="consulta"
        data-appearance="interaction-only"></div>
   <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
   ```

2. **La casilla de autorización**, obligatoria y **sin marcar**, con el enlace al aviso. Y la
   de publicidad, aparte y opcional:

   ```html
   <label class="campo campo--casilla">
     <input type="checkbox" name="autoriza" required>
     <span>Autorizo a Villacasa Group S.A.C. a usar mis datos para responder esta consulta,
       según el <a href="privacidad.html" target="_blank">aviso de privacidad</a>.</span>
   </label>
   <label class="campo campo--casilla">
     <input type="checkbox" name="publicidad">
     <span>Quiero recibir novedades de Montelago (opcional).</span>
   </label>
   ```

3. **El envío**, en `main.js`, justo DESPUÉS del `window.open` y sin esperarlo:

   ```js
   // El registro es un extra: si falla, la persona ya tiene su WhatsApp abierto.
   const p = new URLSearchParams(location.search)
   fetch('/api/consulta', {
     method: 'POST',
     keepalive: true,            // que llegue aunque la página se vaya al mailto
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       clave: crypto.randomUUID(),
       nombre: dato('nombre').value, telefono: dato('telefono').value,
       correo: dato('correo').value, interes: dato('interes').value,
       mensaje: dato('mensaje').value, web: dato('web').value,
       autoriza: dato('autoriza').checked, publicidad: dato('publicidad').checked,
       aviso_version: '2026-11-01',
       turnstile: consulta.querySelector('[name="cf-turnstile-response"]')?.value || '',
       utm_source: p.get('utm_source'), utm_medium: p.get('utm_medium'),
       utm_campaign: p.get('utm_campaign'),
     }),
   }).catch(() => {})
   ```

   Y la nota de debajo del botón deja de decir «esta página no guarda nada»: pasa a decir
   que se guarda, para qué y con enlace al aviso.

4. **La CSP de `_headers`** tiene que abrirle sitio a Turnstile, o el widget no carga:

   ```
   script-src 'self' 'sha256-…' https://challenges.cloudflare.com;
   frame-src https://challenges.cloudflare.com;
   ```

   (`connect-src 'self'` ya cubre el `fetch` a `/api/consulta`.)

## Borrador del aviso de privacidad

> **Borrador para que lo revise Legal.** Los corchetes son datos que faltan. La referencia
> legal es la Ley N.º 29733 y su reglamento vigente; Legal debe confirmar la versión y si
> hace falta algo más (por ejemplo, el código de inscripción del banco de datos).

**Aviso de privacidad — consultas de la web de Montelago** · versión 2026-11-01

**Quién es responsable de tus datos.** Villacasa Group S.A.C., RUC [RUC], con domicilio en
[domicilio fiscal]. Banco de datos «[nombre]», inscrito en el Registro Nacional de Protección
de Datos Personales con el código [código].

**Qué datos y para qué.** Tu nombre, teléfono, correo, el tema que te interesa y tu mensaje, para
**responder tu consulta** sobre Montelago y hacerte seguimiento comercial sobre ella. Si
marcas la casilla de novedades, también para enviarte información de Montelago; puedes
retirarlo cuando quieras. Nombre, teléfono y correo son necesarios para responderte: sin ellos
no podemos contactarte.

**Quién más los ve.** El equipo comercial de Villacasa. Se almacenan con Cloudflare, Inc.
(servidores que pueden estar fuera del Perú) y en [la hoja / el CRM elegido], que actúan
como encargados de tratamiento. No vendemos ni cedemos tus datos.

**Cuánto tiempo.** [12 meses] desde tu última comunicación con nosotros; después se borran.

**Tus derechos.** Puedes pedir acceder, corregir, cancelar u oponerte al uso de tus datos
escribiendo a [privacidad@condominiosvillacasa.com], con tu nombre y una copia de tu documento
de identidad. Respondemos en los plazos que fija la ley. Si no estás conforme, puedes reclamar
ante la Autoridad Nacional de Protección de Datos Personales del Ministerio de Justicia y
Derechos Humanos.

## Cómo se prueba antes de abrirlo al público

Con el proyecto en una rama de vista previa de Cloudflare y las claves de prueba de Turnstile
(la secreta `1x0000000000000000000000000000000AA` siempre aprueba y la
`2x0000000000000000000000000000000AA` siempre rechaza):

```bash
U=https://<rama>.montelago-web.pages.dev/api/consulta
O=https://<rama>.montelago-web.pages.dev
# feliz: 201
curl -si -X POST $U -H "Origin: $O" -H 'Content-Type: application/json' \
  -d '{"clave":"'$(uuidgen)'","nombre":"Prueba","telefono":"913 000 000","correo":"a@b.pe",
       "interes":"Todavía no lo sé","autoriza":true,"aviso_version":"2026-11-01",
       "turnstile":"XXXX.DUMMY.TOKEN.XXXX"}'
# sin autorización: 422 · otro Origin: 403 · sexta en 10 min: 429 · trampa llena: 201 y no se guarda
```

## Lista de activación

- [ ] La web está en Cloudflare Pages con el dominio propio (README, «Cuando haya que moverla»).
- [ ] Legal aprobó el aviso, con RUC, domicilio y el banco de datos inscrito.
- [ ] Administración eligió destino y plazo de conservación, y nombró quién atiende `privacidad@`.
- [ ] Creados: la base D1, el widget de Turnstile (dominio propio + `pages.dev`), los secretos y la regla del WAF.
- [ ] Publicada la página del aviso (`privacidad.html`) y enlazada desde el pie.
- [ ] Hecho el cambio del frontend (casillas, widget, `fetch`) y el de la CSP.
- [ ] Probado en una rama de vista previa con las claves de prueba, los seis casos de arriba.
- [ ] Sólo entonces: copiar `functions/api/consulta.js` y `_routes.json` a la raíz y desplegar.
- [ ] Despublicar la copia de GitHub Pages, donde la función no existe.
