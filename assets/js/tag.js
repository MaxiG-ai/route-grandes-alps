/* tag.js -- Controller einer Etappenseite.
   Texte, Zahlen und Fotoraster stehen schon im HTML (tools/build.py);
   hier kommen nur Karte, Höhenprofil und Lightbox dazu. */
(function(){
  const meta = window.RGA_TAG;
  if(!meta) return;

  RGA.lightbox.init(document.getElementById('fotoRaster'));

  const karteEl = document.getElementById('karte');
  if(!karteEl || typeof L === 'undefined') return;

  const { karte } = RGA.karte.erstellen(karteEl, { schalter: document.getElementById('layerSchalter') });
  const gruppe = L.layerGroup().addTo(karte);
  const svg = document.getElementById('profilSvg');
  const tip = document.getElementById('profilTip');
  let cursor = null;

  fetch('data/tracks/' + meta.id + '.json')
    .then(a => { if(!a.ok) throw new Error(a.status + ' ' + a.statusText); return a.json(); })
    .then(track => {
      const latlngs = track.punkte.map(p => [p.lat, p.lon]);
      RGA.karte.linie(gruppe, latlngs, meta.status);
      RGA.karte.markerStart(gruppe, latlngs[0], meta.von);
      RGA.karte.markerZiel(gruppe, latlngs[latlngs.length - 1], meta.nach);
      for(const w of track.wegpunkte) RGA.karte.markerWegpunkt(gruppe, [w.lat, w.lon], w.name);
      if(meta.bett) RGA.karte.markerBett(gruppe, meta.bett.pos, meta.bett.html);

      cursor = L.circleMarker(latlngs[0], {
        radius:6, color:'#fff', weight:2, fillColor:'#111827', opacity:0, fillOpacity:0,
      }).addTo(gruppe);

      karte.fitBounds(L.latLngBounds(latlngs), { padding:[28, 28] });

      if(svg) RGA.profil.zeichnen({
        svg, tip, punkte: track.punkte,
        beiHover: p => { cursor.setLatLng([p.lat, p.lon]).setStyle({opacity:1, fillOpacity:1}); },
        beiVerlassen: () => { cursor.setStyle({opacity:0, fillOpacity:0}); },
      });
    })
    .catch(err => {
      karteEl.innerHTML = '<p class="karte-fehler">Track konnte nicht geladen werden ('
        + err.message + '). Liegt <code>data/tracks/' + meta.id + '.json</code> auf dem Server?</p>';
      if(svg) svg.closest('.profil-block').hidden = true;
    });
})();
