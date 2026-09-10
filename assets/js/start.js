/* start.js -- Übersichtskarte der Startseite: alle Etappen aus data/uebersicht.json.
   Kennzahlen und Etappentabelle sind vorgerendert, hier nur die Karte. */
(function(){
  const el = document.getElementById('uebersichtKarte');
  if(!el || typeof L === 'undefined') return;
  const status = window.RGA_STATUS || {};   /* {"tag-01":"gefahren", ...} */
  const namen = window.RGA_NAMEN || {};

  const { karte } = RGA.karte.erstellen(el, { scrollWheelZoom:false });
  const gruppe = L.layerGroup().addTo(karte);

  fetch('data/uebersicht.json')
    .then(a => { if(!a.ok) throw new Error(a.status); return a.json(); })
    .then(etappen => {
      const alle = [];
      for(const e of etappen){
        const linie = RGA.karte.linie(gruppe, e.punkte, status[e.id] || 'geplant', { weight:3.5 });
        linie.bindTooltip('Tag ' + e.nr + ' · ' + (namen[e.id] || ''), {sticky:true});
        linie.on('click', () => { window.location.href = e.id + '.html'; });
        linie.on('mouseover', () => linie.setStyle({weight:5.5}));
        linie.on('mouseout', () => linie.setStyle({weight:3.5}));
        alle.push(...e.punkte);
      }
      if(alle.length) karte.fitBounds(L.latLngBounds(alle), { padding:[24, 24] });
    })
    .catch(() => {
      el.innerHTML = '<p class="karte-fehler">Übersichtskarte konnte nicht geladen werden '
        + '(<code>data/uebersicht.json</code>).</p>';
    });
})();
