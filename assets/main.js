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
if (fijo && portada) {
  // Sin requestAnimationFrame ni temporizadores: el manejador mide y decide en el acto. Una
  // versión anterior agrupaba los avisos en un rAF y, donde el navegador no pinta, el «ya lo
  // pedí» se quedaba puesto y el botón no se movía más. Es una lectura por evento de scroll,
  // sin escribir nada antes: no hay reflujo que ahorrar.
  const decidir = () =>
    // visible en cuanto la portada ha salido más de media pantalla
    fijo.classList.toggle('fija--oculta', portada.getBoundingClientRect().bottom > innerHeight / 2)
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
