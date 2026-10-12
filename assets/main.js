// Lo único que necesita JS: que las secciones aparezcan al entrar en pantalla.
//
// La clase que las oculta (.js) la pone este archivo, no el HTML. Si el JS no carga, no se
// ejecuta o falla, la página se ve entera igual. Una animación que no funciona no puede dejar
// una página de venta en blanco.
document.documentElement.classList.add('js')

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
