// Lo que necesita JS: que las secciones aparezcan al hacer scroll, el menú de la hamburguesa,
// los dos vídeos de fondo (portada y lema), el recorrido sobre la aérea, la galería y el
// formulario.
//
// Todo lo de aquí es un añadido. Si el JS no carga, no se ejecuta o falla, la página se ve
// entera igual: la portada enseña su foto, el recorrido es la aérea con su lista y el menú es una
// lista al final. Una animación que no funciona no puede dejar una página de venta en blanco.
document.documentElement.classList.add('js')

/* ---------- Las secciones aparecen al entrar en pantalla ---------- */
const secciones = [...document.querySelectorAll('.seccion:not(.portada)')]
secciones.forEach((s) => s.classList.add('aparece'))

const quieto = matchMedia('(prefers-reduced-motion: reduce)').matches
const todas = () => secciones.forEach((s) => s.classList.add('dentro'))

if (quieto || !('IntersectionObserver' in window)) {
  todas()
} else {
  const ojo = new IntersectionObserver(
    (entradas) => entradas.forEach((e) => e.isIntersecting && e.target.classList.add('dentro')),
    { rootMargin: '0px 0px -12% 0px' },
  )
  secciones.forEach((s) => ojo.observe(s))
  setTimeout(todas, 2500) // red de seguridad, por si el observador no se dispara
}

/* ---------- Lo que depende de dónde está el scroll ---------- */
// Un ÚNICO manejador para las dos cosas que miran el scroll de toda la página: el enlace marcado
// del menú y la pausa del vídeo de la portada. (El recorrido tiene el suyo, más abajo, porque
// sólo trabaja mientras se ve.)
//
// Sin requestAnimationFrame: mide y decide en el acto. Una versión anterior agrupaba los avisos
// en un rAF y, donde el navegador no pinta, el «ya lo pedí» se quedaba puesto y nada se movía
// más. Son unas pocas lecturas por evento, sin escribir nada entre medias: no hay reflujo que
// ahorrar.
const portada = document.querySelector('.portada')
const videoPortada = document.querySelector('.portada__video')
// cada enlace del menú con la sección a la que apunta, resuelto una sola vez
const enlaces = [...document.querySelectorAll('.menu__lista a')]
  .map((a) => ({ a, seccion: document.querySelector(a.getAttribute('href')) }))
  .filter((e) => e.seccion)

if (portada) {
  let activo = null
  let pausadoPorScroll = false
  const decidir = () => {
    // El vídeo de la portada no tiene por qué seguir girando cuando nadie lo ve: en un móvil es
    // batería y procesador gastados mientras se lee el resto. Se pausa al salir y sigue al volver.
    // Sólo si ya arrancó (tiene la clase visible): antes de eso lo decide el bloque del vídeo.
    // Sólo se reanuda lo que se pausó aquí: si el navegador no dejó reproducirlo, no se le
    // insiste en cada evento de scroll.
    if (videoPortada && videoPortada.isConnected && videoPortada.classList.contains('visible')) {
      const fuera = portada.getBoundingClientRect().bottom <= 0
      if (fuera && !videoPortada.paused) {
        videoPortada.pause()
        pausadoPorScroll = true
      } else if (!fuera && pausadoPorScroll) {
        pausadoPorScroll = false
        videoPortada.play().catch(() => {})
      }
    }

    // el enlace marcado es el de la última sección que ya cruzó el primer tercio de la pantalla
    let cual = null
    for (const e of enlaces) if (e.seccion.getBoundingClientRect().top <= innerHeight * 0.35) cual = e
    if (cual !== activo) {
      if (activo) activo.a.removeAttribute('aria-current')
      // «location» y no «true»: es lo que el lector de pantalla anuncia como «ubicación actual»
      if (cual) cual.a.setAttribute('aria-current', 'location')
      activo = cual
    }
  }
  addEventListener('scroll', decidir, { passive: true })
  addEventListener('resize', decidir, { passive: true })
  decidir()
}

/* ---------- El menú de la hamburguesa ---------- */
// Sin JS el menú es una lista al final de la página y el botón ni aparece (lleva «hidden» en el
// HTML). Con JS el menú pasa a ser un panel a pantalla completa que abre el botón de la píldora.
//
// Abierto, lo de detrás queda «inert»: ni el teclado ni el lector de pantalla se pierden por la
// página que está tapada. La píldora queda fuera del inert porque su botón es el que cierra.
// Escape también cierra, y el foco vuelve al botón, que es donde estaba.
const menu = document.querySelector('#menu')
const botonMenu = document.querySelector('.pildora__menu')
if (menu && botonMenu) {
  const detras = [...document.querySelectorAll('.salto, .portada, main, .pie-web, .pildora__cta')]
  menu.classList.add('menu--panel')
  botonMenu.hidden = false
  const etiqueta = botonMenu.querySelector('.oculto')

  const abrir = (si) => {
    menu.classList.toggle('abierto', si)
    botonMenu.setAttribute('aria-expanded', String(si))
    if (etiqueta) etiqueta.textContent = si ? 'Cerrar el menú' : 'Menú'
    document.documentElement.classList.toggle('menu-abierto', si)
    detras.forEach((el) => { el.inert = si })
    if (si) menu.querySelector('a')?.focus()
  }
  // cerrado, el panel tampoco se puede recorrer con el tabulador aunque esté en el DOM
  menu.inert = true
  const alternar = (si) => { menu.inert = !si; abrir(si) }

  botonMenu.addEventListener('click', () => alternar(botonMenu.getAttribute('aria-expanded') !== 'true'))
  // al elegir una sección se cierra y el navegador sigue el enlace como siempre
  menu.addEventListener('click', (ev) => { if (ev.target.closest('a')) alternar(false) })
  addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape' && botonMenu.getAttribute('aria-expanded') === 'true') {
      alternar(false)
      botonMenu.focus()
    }
  })
}

/* ---------- El vídeo de la portada ---------- */
// Son 4 MB o 7 según la pantalla. Eso NO se le baja a cualquiera.
//
// El corte es el mismo que usa el tour, que ya estaba pensado: con AHORRO DE DATOS o con 2G se
// queda la foto, que al fin y al cabo es la misma imagen. Con 3G sí hay vídeo, pero el chico.
// Antes esto trataba el 3G como si fuera 2G y dejaba sin vídeo a media Latinoamérica.
//
// Con ?foto=1 en la dirección se prueba el caso de sólo foto.
const video = videoPortada
if (video) {
  const con = navigator.connection || {}
  const muyLenta = /(^|-)2g$/.test(con.effectiveType || '')
  const floja = /(^|-)[23]g$/.test(con.effectiveType || '')
  const soloFoto = quieto || con.saveData || muyLenta || /[?&]foto=1/.test(location.search)

  if (!soloFoto) {
    // El de 1080 sólo donde se va a notar y la conexión aguante. En un móvil, o con 3G, el de
    // 720 se ve igual y pesa la mitad.
    //
    // Se mide en píxeles CSS, sin multiplicar por la densidad de la pantalla. Antes se
    // multiplicaba, y un teléfono cualquiera (390 de ancho ×3) salía «más ancho» que un
    // portátil: TODOS los móviles con 4G se bajaban los 7 MB, justo lo contrario de lo que
    // dice el párrafo de arriba. En un recuadro de teléfono tras un velo, 720 basta.
    const ancho = Math.max(innerWidth, innerHeight)
    video.src = ancho >= 1024 && !floja ? video.dataset['1080'] : video.dataset['720']
    // preload="none" está en el HTML para que no se baje nada antes de decidir; decidido ya,
    // se pide entero. Algunos navegadores (Safari) respetan el none aun después de load() y
    // nunca llegarían a «canplay».
    video.preload = 'auto'
    video.addEventListener('canplay', () => {
      video.classList.add('visible')
      video.play().catch(() => {}) // si el navegador no deja reproducir solo, queda la foto
    }, { once: true })
    video.addEventListener('error', () => video.remove(), { once: true })
    video.load()
  } else {
    video.remove()
  }
}

/* ---------- Los vídeos de fondo: el lema y las áreas comunes ---------- */
// Las tomas oficiales en bucle detrás del texto: la cenital de la Etapa I en el lema, el mirador
// y la piscina en sus áreas. Son los clips de 720 de la galería (de 0,4 a 1 MB), y cada uno se
// pide sólo cuando su sección está a punto de entrar en pantalla: quien no baja hasta ahí no lo
// descarga. Las mismas reglas que la portada: con ahorro de datos, 2G o movimiento reducido se
// queda la foto. Y cada uno se pausa al salir de la vista, para que no haya tres girando a la vez.
const fondos = [...document.querySelectorAll('video.fondo-vivo')]
if (fondos.length) {
  const con = navigator.connection || {}
  const sinVideo = quieto || con.saveData || /(^|-)2g$/.test(con.effectiveType || '') ||
    /[?&]foto=1/.test(location.search) || !('IntersectionObserver' in window)
  if (sinVideo) {
    fondos.forEach((v) => v.remove())
  } else {
    const arrancar = (v) => {
      v.dataset.pedido = '1'
      v.src = v.dataset.src
      v.preload = 'auto'
      v.addEventListener('canplay', () => {
        v.classList.add('visible')
        if (v.dataset.dentro === '1') v.play().catch(() => {})
      }, { once: true })
      v.addEventListener('error', () => v.remove(), { once: true })
      v.load()
    }
    const ojoFondos = new IntersectionObserver((entradas) => {
      entradas.forEach((e) => {
        const v = e.target.querySelector('video.fondo-vivo')
        if (!v) return
        v.dataset.dentro = e.isIntersecting ? '1' : ''
        if (e.isIntersecting && !v.dataset.pedido) arrancar(v)
        else if (v.classList.contains('visible')) {
          if (e.isIntersecting) v.play().catch(() => {})
          else v.pause()
        }
      })
    }, { rootMargin: '200px 0px' })
    fondos.forEach((v) => (v.dataset.src ? ojoFondos.observe(v.parentElement) : v.remove()))
  }
}

/* ---------- El recorrido sobre la aérea ---------- */
// La sección mide una pantalla por paso; la escena se queda pegada arriba y, según cuánto se ha
// bajado, la cámara va de un punto del masterplan al siguiente: se detiene un rato en cada uno
// (ahí aparece su nombre y su ficha) y viaja entre medias.
//
// La «cámara» es un transform sobre el lienzo (la aérea y sus puntos): translate y scale, nada
// más. Es lo único que el navegador puede mover sin volver a maquetar la página, y por eso el
// scroll no se traba ni en un teléfono modesto. Se pinta como mucho una vez por fotograma.
//
// Con movimiento reducido no hay viaje: la foto con los puntos numerados y la lista. Sin JS, ni
// eso: la foto y la lista. Las dos cosas las resuelve el CSS sin ayuda.
const recorrido = document.querySelector('.recorrido')
if (recorrido) {
  const lienzo = recorrido.querySelector('.recorrido__lienzo')
  const imagen = recorrido.querySelector('.recorrido__img')
  const pines = [...recorrido.querySelectorAll('.pin')]
  const fichas = [...recorrido.querySelectorAll('.paso')]

  // Las posiciones van como CSS custom properties y no como style="" en el HTML: la CSP de la
  // página prohíbe los estilos escritos en el marcado, pero no los que pone el JS por el CSSOM.
  pines.forEach((p) => {
    p.style.setProperty('--x', p.dataset.x)
    p.style.setProperty('--y', p.dataset.y)
  })

  if (quieto) {
    recorrido.classList.add('recorrido--quieto')
  } else {
    recorrido.classList.add('recorrido--viaje')
    recorrido.style.setProperty('--pasos', String(fichas.length + 1))

    // la proporción de la aérea, leída de sus width/height del HTML (los pone generar.py)
    const prop = (+imagen.getAttribute('width') || 16) / (+imagen.getAttribute('height') || 9)
    const pinDe = (n) => pines.find((p) => p.dataset.paso === String(n))
    let ancho = 0, alto = 0, W = 0, H = 0, vertical = false

    // Dónde mira la cámara en cada paso: un punto de la imagen (en fracción) y un zoom relativo
    // a la aérea «a cover». El paso 0 es la vista general: en horizontal, la aérea entera; en un
    // móvil en vertical, alejada lo más posible sin dejar bandas grandes, para que se entienda
    // el conjunto antes de acercarse.
    const camaras = () => fichas.map((f) => {
      const n = f.dataset.paso
      const p = pinDe(n)
      if (!p) {
        const cabe = Math.min(ancho / W, alto / H)
        return { x: 0.62, y: 0.6, z: vertical ? Math.min(1, cabe * 1.5) : 1 }
      }
      // En vertical, la aérea a «cover» ya mide su alto exacto y un punto queda donde cae en la
      // foto, que suele ser la mitad de abajo: justo detrás de la ficha. Con 1,5 la imagen pasa a
      // medir más que la pantalla y la cámara tiene margen para subir el punto por encima.
      return { x: +p.dataset.x, y: +p.dataset.y, z: vertical ? 1.5 : 1.45 }
    })
    let tomas = []

    const medir = () => {
      ancho = innerWidth
      alto = recorrido.querySelector('.recorrido__escena').clientHeight || innerHeight
      vertical = alto > ancho
      W = Math.max(ancho, alto * prop)
      H = W / prop
      lienzo.style.setProperty('--w', W + 'px')
      lienzo.style.setProperty('--h', H + 'px')
      tomas = camaras()
    }

    // Dónde cae el punto mirado en la pantalla: en horizontal, algo a la derecha del centro,
    // porque la ficha va abajo a la izquierda; en vertical, en el tercio de arriba, porque la
    // ficha ocupa la parte de abajo.
    const encuadre = (c) => {
      const ox = vertical ? 0.5 : 0.58
      const oy = vertical ? 0.36 : 0.45
      let tx = ancho * ox - c.z * c.x * W
      let ty = alto * oy - c.z * c.y * H
      // Que la imagen no deje ver lo que hay detrás: si es más grande que la pantalla, no se
      // despega de los bordes. Si es más chica (la vista general en vertical), se centra de lado
      // y, de alto, se deja arriba, porque la parte de abajo es de la ficha.
      const zw = c.z * W, zh = c.z * H
      tx = zw >= ancho ? Math.min(0, Math.max(ancho - zw, tx)) : (ancho - zw) / 2
      ty = zh >= alto ? Math.min(0, Math.max(alto - zh, ty)) : Math.max(56, alto * oy - zh / 2)
      return { tx, ty }
    }

    const suave = (t) => t * t * (3 - 2 * t)
    let activo = -1

    const pintar = () => {
      const r = recorrido.getBoundingClientRect()
      const recorrible = r.height - alto
      if (recorrible <= 0 || !tomas.length) return
      const avance = Math.min(1, Math.max(0, -r.top / recorrible))
      const pos = avance * (tomas.length - 1)
      const i = Math.min(tomas.length - 2, Math.floor(pos))
      // en cada paso la cámara se queda quieta el 35 % del tramo a cada lado y viaja en el 30 %
      // del medio: así hay tiempo de leer la ficha sin tener que parar el dedo justo
      const f = pos - i
      const t = suave(Math.min(1, Math.max(0, (f - 0.35) / 0.3)))
      const a = tomas[i], b = tomas[i + 1] || a
      const c = { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, z: a.z + (b.z - a.z) * t }
      const { tx, ty } = encuadre(c)
      lienzo.style.transform = 'translate3d(' + tx.toFixed(1) + 'px,' + ty.toFixed(1) + 'px,0) scale(' + c.z.toFixed(4) + ')'
      lienzo.style.setProperty('--z', c.z.toFixed(4))

      const cual = Math.round(pos)
      if (cual !== activo) {
        activo = cual
        fichas.forEach((el) => el.classList.toggle('activo', el.dataset.paso === String(cual)))
        pines.forEach((el) => el.classList.toggle('activo', el.dataset.paso === String(cual)))
      }
    }
    // A diferencia del manejador general, aquí sí se agrupa en un fotograma: esto escribe un
    // transform en cada evento y los eventos de scroll llegan más seguido de lo que se pinta.
    // Sin bandera de «ya lo pedí» —la que dejó trabada la versión anterior del menú—: cada
    // evento cancela el fotograma pendiente y pide otro, así que nunca se queda nada colgado.
    let fotograma = 0
    const pedir = () => {
      cancelAnimationFrame(fotograma)
      fotograma = requestAnimationFrame(pintar)
    }
    medir()
    pintar()
    addEventListener('scroll', pedir, { passive: true })
    addEventListener('resize', () => { medir(); pedir() }, { passive: true })
  }
}

/* ---------- La galería: el clip se baja cuando lo piden ---------- */
// Siete clips de 400 KB a 1,3 MB. Cargarlos al entrar serían 5 MB que casi nadie va a ver, así
// que cada recuadro es una foto con su botón de play y el vídeo aparece al pulsarlo.
//
// Sin JS esto no se rompe: el recuadro es un enlace a un .mp4 y el navegador lo abre él solo.
// Y si el vídeo no llega a cargar, el recuadro VUELVE a ser la foto con un aviso, en vez de
// quedarse como un rectángulo negro con el que no se puede hacer nada.
const galeria = document.querySelector('.clips')
if (galeria) {
  const pausarLasDemas = (menos) =>
    galeria.querySelectorAll('video').forEach((v) => v !== menos && v.pause())

  galeria.addEventListener('click', (ev) => {
    const enlace = ev.target.closest('.clip__abrir')
    if (!enlace || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.button) return // clic de «abrir aparte»
    ev.preventDefault()

    const video = document.createElement('video')
    video.src = enlace.getAttribute('href')
    video.poster = enlace.querySelector('img')?.getAttribute('src') || ''
    video.controls = true
    video.playsInline = true
    video.setAttribute('aria-label', enlace.getAttribute('aria-label') || '')

    video.addEventListener('play', () => pausarLasDemas(video))
    video.addEventListener('error', () => {
      const devolverFoco = document.activeElement === video
      video.replaceWith(enlace)
      if (devolverFoco) enlace.focus()
      // si ya falló antes, no se apila un segundo aviso igual
      if (enlace.nextElementSibling?.classList.contains('clip__fallo')) return
      const aviso = document.createElement('p')
      aviso.className = 'clip__fallo'
      aviso.textContent = 'Este clip no cargó. Se puede ver en el tour.'
      enlace.after(aviso)
    }, { once: true })

    // El enlace que tenía el foco desaparece: sin esto, quien llegó con el teclado se queda con
    // el foco en ninguna parte y tiene que empezar desde arriba. Se lo damos al vídeo, que con
    // controles se maneja con espacio y flechas.
    const teniaFoco = document.activeElement === enlace
    enlace.replaceWith(video)
    if (teniaFoco) video.focus()
    pausarLasDemas(video)
    video.play().catch(() => {}) // el clic ya es permiso, pero si el navegador dice no, quedan los controles
  })
}

/* ---------- El formulario: arma el mensaje y abre WhatsApp ---------- */
// Esta página es estática y no tiene a dónde enviar un formulario, así que no finge tenerlo:
// recoge los datos, escribe el mensaje y abre WhatsApp con todo puesto. El mensaje lo manda la
// persona desde su propio WhatsApp. Por eso aquí no se guarda nada y no hace falta pedir
// autorización de datos: no hay datos que custodiar.
//
// El día que Administración decida dónde aterrizan las consultas de verdad, esto cambia: hará
// falta la casilla de autorización y un aviso de privacidad con el RUC de la empresa. Mientras
// no exista ese sitio, prometer «te contactaremos» sería mentir.
//
// El formato del mensaje es EL MISMO que usa el tour (sendLead en src/project.js), para que a
// Comercial le lleguen las consultas iguales vengan de donde vengan.
const consulta = document.querySelector('#consulta')
if (consulta) {
  const SALTO = String.fromCharCode(10)
  const dato = (n) => consulta.elements[n]
  const campoDe = (n) => dato(n).closest('.campo')

  // Cada campo apunta a su mensaje de error con aria-describedby, para que el lector de pantalla
  // lo lea al entrar en el campo y no sólo como parte de la etiqueta.
  consulta.querySelectorAll('[data-error]').forEach((s) => {
    s.id = 'error-' + s.dataset.error
    s.setAttribute('aria-live', 'polite')
    dato(s.dataset.error).setAttribute('aria-describedby', s.id)
  })

  // El correo y el teléfono los valida el propio navegador por el type= del campo; lo único
  // nuestro es exigir que el teléfono tenga dígitos de verdad y el nombre, dos letras.
  const reglas = {
    nombre: (v) => v.trim().length >= 2 || 'Escribe tu nombre',
    telefono: (v) =>
      (dato('telefono').validity.valid && v.replace(/[^0-9]/g, '').length >= 7) ||
      'Escribe un teléfono válido',
    correo: (v) => dato('correo').validity.valid || 'Escribe un correo válido',
  }

  const revisar = (n) => {
    const fallo = reglas[n](dato(n).value)
    const campo = campoDe(n)
    campo.classList.toggle('mal', fallo !== true)
    consulta.querySelector('[data-error="' + n + '"]').textContent = fallo === true ? '' : fallo
    // el color rojo del borde no lo ve quien usa un lector de pantalla: aria-invalid sí lo dice
    if (fallo === true) dato(n).removeAttribute('aria-invalid')
    else dato(n).setAttribute('aria-invalid', 'true')
    return fallo === true
  }

  // Mientras no se haya intentado enviar no se regaña a nadie; después, cada campo se corrige
  // en cuanto se arregla.
  let intentado = false
  Object.keys(reglas).forEach((n) => {
    dato(n).addEventListener('input', () => intentado && revisar(n))
    dato(n).addEventListener('blur', () => intentado && revisar(n))
  })

  consulta.addEventListener('submit', (ev) => {
    ev.preventDefault()
    intentado = true
    const malos = Object.keys(reglas).filter((n) => !revisar(n))
    if (malos.length) {
      const primero = dato(malos[0])
      primero.focus()
      // el JS no hereda el scroll-behavior del CSS: quien pidió menos movimiento, salto directo
      primero.scrollIntoView({ block: 'center', behavior: quieto ? 'auto' : 'smooth' })
      return
    }
    if (dato('web').value) return // lo llenó un robot: no se abre nada

    const texto = [
      'Consulta desde la web de Montelago',
      'Interés: ' + dato('interes').value,
      'Nombre: ' + dato('nombre').value.trim(),
      'Correo: ' + dato('correo').value.trim(),
      'Teléfono: ' + dato('telefono').value.trim(),
      dato('mensaje').value.trim() && 'Mensaje: ' + dato('mensaje').value.trim(),
    ]
      .filter(Boolean)
      .join(SALTO)

    // window.open va AQUÍ, dentro del clic y antes de cualquier espera: si se retrasa, el
    // navegador lo toma por ventana emergente y lo bloquea. Es la misma razón por la que el
    // tour abre WhatsApp antes de guardar nada.
    //
    // SIN 'noopener' en el tercer argumento, y es a propósito. Con él, window.open devuelve
    // SIEMPRE null —así lo dice el estándar—, aunque la ventana se haya abierto. El código de
    // abajo lo leía como «bloqueada» y además saltaba al correo: la persona acababa con
    // WhatsApp abierto en otra pestaña y su programa de correo encima. El aislamiento que daba
    // noopener se consigue igual cortando el opener a mano.
    const wa = consulta.dataset.wa
    const ventana = wa && window.open('https://wa.me/' + wa + '?text=' + encodeURIComponent(texto), '_blank')
    if (ventana) {
      try { ventana.opener = null } catch (e) { /* si no deja, tampoco pasa nada */ }
    }

    if (!ventana) {
      // Sin WhatsApp —o con las ventanas bloqueadas— se va por correo, que no se puede bloquear.
      const correo = consulta.dataset.correo
      if (correo) {
        location.href =
          'mailto:' + correo +
          '?subject=' + encodeURIComponent('Consulta desde la web de Montelago') +
          '&body=' + encodeURIComponent(texto)
      }
      return
    }

    // Se reutiliza si ya está: quien envía dos veces no puede encontrarse con un error porque
    // la nota que se reemplazaba la primera vez ya no existe. role=status para que el lector
    // de pantalla anuncie que algo pasó, porque la pestaña nueva se abre fuera de su vista.
    let gracias = consulta.querySelector('.consulta__gracias')
    if (!gracias) {
      gracias = document.createElement('p')
      gracias.className = 'consulta__gracias'
      gracias.setAttribute('role', 'status')
      const nota = consulta.querySelector('.consulta__nota')
      if (nota) nota.replaceWith(gracias)
      else consulta.append(gracias)
    }
    gracias.textContent = 'Abrimos tu mensaje en WhatsApp con los datos puestos. Sólo falta que lo envíes.'
  })
}
