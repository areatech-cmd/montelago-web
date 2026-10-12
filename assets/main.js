// Lo único que necesita JS: que las secciones aparezcan al hacer scroll, y el vídeo de portada.
//
// Todo lo de aquí es un añadido. Si el JS no carga, no se ejecuta o falla, la página se ve
// entera igual y la portada enseña su foto. Una animación que no funciona no puede dejar una
// página de venta en blanco.
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

/* ---------- El botón fijo, sólo cuando hace falta ---------- */
// En la portada ya hay un «Quiero información» a la vista; el fijo se le montaba encima en
// pantalla estrecha y quedaban dos botones iguales pegados. Aparece al dejar atrás la portada.
//
// Esto va con el scroll a pelo, NO con IntersectionObserver, y es a propósito. Con el
// observador el botón se quedaba escondido para siempre: la clase se pone al arrancar y la
// llamada que debía quitarla no llegaba nunca. El botón de contacto es el que vende; no puede
// depender de un aviso que quizá no venga. Y si el JS entero falla, la clase no se pone y el
// botón se ve siempre: el lado seguro.
const fijo = document.querySelector('.fija')
const portada = document.querySelector('.portada')
const barra = document.querySelector('.menu')
// cada enlace del menú con la sección a la que apunta, resuelto una sola vez
const enlaces = [...document.querySelectorAll('.menu__lista a')]
  .map((a) => ({ a, seccion: document.querySelector(a.getAttribute('href')) }))
  .filter((e) => e.seccion)

if (portada) {
  // Un ÚNICO manejador para las tres cosas que dependen de dónde está el scroll: el botón fijo,
  // el fondo de la barra y el enlace marcado. Tres observadores separados harían tres veces el
  // mismo trabajo y podrían contradecirse.
  //
  // Sin requestAnimationFrame ni temporizadores: mide y decide en el acto. Una versión anterior
  // agrupaba los avisos en un rAF y, donde el navegador no pinta, el «ya lo pedí» se quedaba
  // puesto y nada se movía más. Son unas pocas lecturas por evento de scroll, sin escribir nada
  // entre medias: no hay reflujo que ahorrar.
  let activo = null
  const decidir = () => {
    const enPortada = portada.getBoundingClientRect().bottom > innerHeight / 2
    if (fijo) fijo.classList.toggle('fija--oculta', enPortada)   // en la portada ya hay un botón igual
    if (barra) barra.classList.toggle('menu--solido', !enPortada)

    // el enlace marcado es el de la última sección que ya cruzó el primer tercio de la pantalla
    let cual = null
    for (const e of enlaces) if (e.seccion.getBoundingClientRect().top <= innerHeight * 0.35) cual = e
    if (cual !== activo) {
      if (activo) activo.a.removeAttribute('aria-current')
      if (cual) cual.a.setAttribute('aria-current', 'true')
      activo = cual
    }
  }
  addEventListener('scroll', decidir, { passive: true })
  addEventListener('resize', decidir, { passive: true })
  decidir()
}

/* ---------- El vídeo de la portada ---------- */
// Son 4 MB o 7 según la pantalla. Eso NO se le baja a cualquiera.
//
// El corte es el mismo que usa el tour, que ya estaba pensado: con AHORRO DE DATOS o con 2G se
// queda la foto, que al fin y al cabo es la misma imagen. Con 3G sí hay vídeo, pero el chico.
// Antes esto trataba el 3G como si fuera 2G y dejaba sin vídeo a media Latinoamérica.
//
// Con ?foto=1 en la dirección se prueba el caso de sólo foto.
const video = document.querySelector('.portada__video')
if (video) {
  const con = navigator.connection || {}
  const muyLenta = /(^|-)2g$/.test(con.effectiveType || '')
  const floja = /(^|-)[23]g$/.test(con.effectiveType || '')
  const soloFoto = quieto || con.saveData || muyLenta || /[?&]foto=1/.test(location.search)

  if (!soloFoto) {
    // El de 1080 sólo donde se va a notar y la conexión aguante. En un móvil, o con 3G, el de
    // 720 se ve igual y pesa la mitad.
    const ancho = Math.max(innerWidth, (innerHeight * 16) / 9) * (devicePixelRatio || 1)
    video.src = ancho > 1400 && !floja ? video.dataset['1080'] : video.dataset['720']
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
      video.replaceWith(enlace)
      const aviso = document.createElement('p')
      aviso.className = 'clip__fallo'
      aviso.textContent = 'Este clip no cargó. Se puede ver en el tour.'
      enlace.after(aviso)
    }, { once: true })

    enlace.replaceWith(video)
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
      primero.scrollIntoView({ block: 'center', behavior: 'smooth' })
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
    const wa = consulta.dataset.wa
    const ventana = wa && window.open('https://wa.me/' + wa + '?text=' + encodeURIComponent(texto), '_blank', 'noopener')

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

    const gracias = document.createElement('p')
    gracias.className = 'consulta__gracias'
    gracias.textContent = 'Abrimos tu mensaje en WhatsApp con los datos puestos. Sólo falta que lo envíes.'
    consulta.querySelector('.consulta__nota').replaceWith(gracias)
  })
}
