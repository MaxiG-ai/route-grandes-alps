/* lightbox.js -- photo viewer, no third-party library.
   Expects a grid of <button data-full="..." data-caption="..."> and builds
   the overlay itself. Keys: arrows and Escape; touch: swipe. */
window.RGA = window.RGA || {};

RGA.lightbox = (function(){
  let box, image, captionEl, counterEl, photos = [], index = 0, lastFocus = null;

  function build(){
    box = document.createElement('div');
    box.className = 'lightbox';
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-modal', 'true');
    box.setAttribute('aria-label', 'Foto in groß');
    box.innerHTML = `
      <button class="close" type="button" aria-label="Schließen">✕</button>
      <div class="lightbox-image"><img alt=""></div>
      <div class="lightbox-bar">
        <button class="prev" type="button" aria-label="Vorheriges Foto">‹</button>
        <button class="next" type="button" aria-label="Nächstes Foto">›</button>
        <p class="lightbox-caption"></p>
        <span class="lightbox-counter mono"></span>
      </div>`;
    document.body.appendChild(box);
    image = box.querySelector('img');
    captionEl = box.querySelector('.lightbox-caption');
    counterEl = box.querySelector('.lightbox-counter');

    box.querySelector('.close').addEventListener('click', close);
    box.querySelector('.next').addEventListener('click', () => step(1));
    box.querySelector('.prev').addEventListener('click', () => step(-1));
    box.addEventListener('click', event => { if(event.target === box) close(); });

    let startX = null;
    box.addEventListener('pointerdown', event => { startX = event.clientX; });
    box.addEventListener('pointerup', event => {
      if(startX !== null && Math.abs(event.clientX - startX) > 55){
        step(event.clientX < startX ? 1 : -1);
      }
      startX = null;
    });
    document.addEventListener('keydown', event => {
      if(!box.classList.contains('open')) return;
      if(event.key === 'Escape') close();
      else if(event.key === 'ArrowRight') step(1);
      else if(event.key === 'ArrowLeft') step(-1);
    });
  }

  function show(){
    const photo = photos[index];
    image.src = photo.full;
    image.alt = photo.caption || 'Foto';
    captionEl.textContent = photo.caption || '';
    counterEl.textContent = (index + 1) + ' / ' + photos.length;
    const several = photos.length > 1;
    box.querySelector('.next').hidden = !several;
    box.querySelector('.prev').hidden = !several;
  }

  function step(delta){
    index = (index + delta + photos.length) % photos.length;
    show();
  }

  function open(at){
    lastFocus = document.activeElement;
    index = at;
    box.classList.add('open');
    document.body.style.overflow = 'hidden';
    show();
    box.querySelector('.close').focus();
  }

  function close(){
    box.classList.remove('open');
    document.body.style.overflow = '';
    if(lastFocus) lastFocus.focus();
  }

  /* grid: the element holding the <button data-full data-caption> thumbnails */
  function init(grid){
    if(!grid) return;
    const buttons = [...grid.querySelectorAll('button[data-full]')];
    if(!buttons.length) return;
    if(!box) build();
    photos = buttons.map(b => ({ full: b.dataset.full, caption: b.dataset.caption || '' }));
    buttons.forEach((button, at) => button.addEventListener('click', () => open(at)));
  }

  return { init };
})();
