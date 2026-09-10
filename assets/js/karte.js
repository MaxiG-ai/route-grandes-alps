/* karte.js -- Leaflet-Grundgerüst, Kachel-Layer, Linien in Trikolore-Farben. */
window.RGA = window.RGA || {};

RGA.karte = (function(){
  const FARBE = {
    gefahren: '#ef4135',   /* rouge: schon gefahren */
    heute:    '#ef4135',
    geplant:  '#0055a4',   /* bleu, gestrichelt: noch vor uns */
    start:    '#0055a4',
    ziel:     '#c8102e',
    punkt:    '#111827',
  };

  /* Karte mit Gelände-/Straßen-Umschalter. schalterEl darf fehlen. */
  function erstellen(el, opts){
    opts = opts || {};
    const karte = L.map(el, {
      zoomControl: opts.zoomControl !== false,
      attributionControl: true,
      scrollWheelZoom: opts.scrollWheelZoom !== false,
      minZoom: 5, maxZoom: 17,
    });
    const gelaende = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
      maxZoom: 17, subdomains: 'abc',
      attribution: 'Kartendaten: &copy; OpenStreetMap-Mitwirkende, SRTM | Stil: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA)',
    });
    const strassen = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      maxZoom: 19, subdomains: 'abcd',
      attribution: '&copy; OpenStreetMap-Mitwirkende &copy; <a href="https://carto.com/attributions">CARTO</a>',
    });
    gelaende.addTo(karte);

    if(opts.schalter){
      opts.schalter.addEventListener('click', (e) => {
        const knopf = e.target.closest('button[data-layer]');
        if(!knopf) return;
        opts.schalter.querySelectorAll('button').forEach(b => b.classList.remove('aktiv'));
        knopf.classList.add('aktiv');
        if(knopf.dataset.layer === 'gelaende'){ karte.removeLayer(strassen); gelaende.addTo(karte); }
        else { karte.removeLayer(gelaende); strassen.addTo(karte); }
      });
    }
    return { karte, gelaende, strassen };
  }

  /* Weiße Fassung unter farbiger Linie -- bleibt auf jeder Kachel lesbar. */
  function linie(gruppe, latlngs, status, opts){
    opts = opts || {};
    const geplant = status === 'geplant';
    L.polyline(latlngs, {
      color:'#ffffff', weight: (opts.weight || 4.5) + 3.5, opacity:.85,
      lineCap:'round', lineJoin:'round', interactive:false,
    }).addTo(gruppe);
    return L.polyline(latlngs, {
      color: geplant ? FARBE.geplant : FARBE.gefahren,
      weight: opts.weight || 4.5, opacity:1, lineCap:'round', lineJoin:'round',
      dashArray: geplant ? '9 7' : null,
    }).addTo(gruppe);
  }

  function markerStart(gruppe, latlng, name){
    return L.circleMarker(latlng, {radius:8, color:FARBE.start, weight:3, fillColor:'#fff', fillOpacity:1})
      .bindTooltip('Start · ' + name, {direction:'top'}).addTo(gruppe);
  }
  function markerZiel(gruppe, latlng, name){
    return L.circleMarker(latlng, {radius:8, color:FARBE.ziel, weight:3, fillColor:'#fff', fillOpacity:1})
      .bindTooltip('Ziel · ' + name, {direction:'top'}).addTo(gruppe);
  }
  function markerWegpunkt(gruppe, latlng, name){
    return L.circleMarker(latlng, {radius:5.5, color:'#fff', weight:2, fillColor:FARBE.punkt, fillOpacity:1})
      .bindPopup('<div class="rr-popup">' + name + '</div>').addTo(gruppe);
  }
  function markerBett(gruppe, latlng, html){
    return L.marker(latlng, {
      icon: L.divIcon({
        className:'bett-pin', html:'<span>⚑</span>', iconSize:[26,26], iconAnchor:[13,13],
      }),
    }).bindPopup('<div class="rr-popup">' + html + '</div>').addTo(gruppe);
  }

  return { erstellen, linie, markerStart, markerZiel, markerWegpunkt, markerBett, FARBE };
})();
