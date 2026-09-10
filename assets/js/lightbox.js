/* lightbox.js -- Fotogalerie ohne Fremdbibliothek.
   Erwartet ein Raster mit <button data-gross="..." data-titel="..."> und
   baut die Overlay-Schicht selbst. Tastatur: ← → Escape, dazu Wischen. */
window.RGA = window.RGA || {};

RGA.lightbox = (function(){
  let box, bild, titelEl, zaehlerEl, bilder = [], index = 0, letzterFokus = null;

  function aufbauen(){
    box = document.createElement('div');
    box.className = 'lightbox';
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-modal', 'true');
    box.setAttribute('aria-label', 'Foto in groß');
    box.innerHTML = `
      <button class="zu" type="button" aria-label="Schließen">✕</button>
      <div class="lightbox-bild"><img alt=""></div>
      <div class="lightbox-fuss">
        <button class="zurueck" type="button" aria-label="Vorheriges Foto">‹</button>
        <button class="vor" type="button" aria-label="Nächstes Foto">›</button>
        <p class="lightbox-titel"></p>
        <span class="lightbox-zaehler mono"></span>
      </div>`;
    document.body.appendChild(box);
    bild = box.querySelector('img');
    titelEl = box.querySelector('.lightbox-titel');
    zaehlerEl = box.querySelector('.lightbox-zaehler');

    box.querySelector('.zu').addEventListener('click', schliessen);
    box.querySelector('.vor').addEventListener('click', () => springen(1));
    box.querySelector('.zurueck').addEventListener('click', () => springen(-1));
    box.addEventListener('click', (e) => { if(e.target === box) schliessen(); });

    let startX = null;
    box.addEventListener('pointerdown', e => { startX = e.clientX; });
    box.addEventListener('pointerup', e => {
      if(startX !== null && Math.abs(e.clientX - startX) > 55) springen(e.clientX < startX ? 1 : -1);
      startX = null;
    });
    document.addEventListener('keydown', (e) => {
      if(!box.classList.contains('offen')) return;
      if(e.key === 'Escape'){ schliessen(); }
      else if(e.key === 'ArrowRight'){ springen(1); }
      else if(e.key === 'ArrowLeft'){ springen(-1); }
    });
  }

  function zeigen(){
    const b = bilder[index];
    bild.src = b.gross;
    bild.alt = b.titel || 'Foto';
    titelEl.textContent = b.titel || '';
    zaehlerEl.textContent = (index + 1) + ' / ' + bilder.length;
    const mehrere = bilder.length > 1;
    box.querySelector('.vor').hidden = !mehrere;
    box.querySelector('.zurueck').hidden = !mehrere;
  }
  function springen(d){
    index = (index + d + bilder.length) % bilder.length;
    zeigen();
  }
  function oeffnen(i){
    letzterFokus = document.activeElement;
    index = i;
    box.classList.add('offen');
    document.body.style.overflow = 'hidden';
    zeigen();
    box.querySelector('.zu').focus();
  }
  function schliessen(){
    box.classList.remove('offen');
    document.body.style.overflow = '';
    if(letzterFokus) letzterFokus.focus();
  }

  /* raster: Element, das die <button data-gross data-titel> enthält. */
  function init(raster){
    if(!raster) return;
    const knoepfe = [...raster.querySelectorAll('button[data-gross]')];
    if(!knoepfe.length) return;
    if(!box) aufbauen();
    bilder = knoepfe.map(k => ({ gross: k.dataset.gross, titel: k.dataset.titel || '' }));
    knoepfe.forEach((k, i) => k.addEventListener('click', () => oeffnen(i)));
  }

  return { init };
})();
