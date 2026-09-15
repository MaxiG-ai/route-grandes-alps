/* map.js -- Leaflet setup, tile layers, lines and markers in tricolore colours. */
window.RGA = window.RGA || {};

RGA.map = (function(){
  const COLOUR = {
    route:  '#ef4135',
    start:  '#0055a4',
    finish: '#c8102e',
    point:  '#111827',
  };

  /* Creates the map. opts.toggle is the terrain/streets switch, if present. */
  function create(element, opts){
    opts = opts || {};
    const map = L.map(element, {
      zoomControl: opts.zoomControl !== false,
      attributionControl: true,
      scrollWheelZoom: opts.scrollWheelZoom !== false,
      minZoom: 5, maxZoom: 17,
    });
    const terrain = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
      maxZoom: 17, subdomains: 'abc',
      attribution: 'Kartendaten: &copy; OpenStreetMap-Mitwirkende, SRTM | Stil: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA)',
    });
    const streets = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      maxZoom: 19, subdomains: 'abcd',
      attribution: '&copy; OpenStreetMap-Mitwirkende &copy; <a href="https://carto.com/attributions">CARTO</a>',
    });
    terrain.addTo(map);

    if(opts.toggle){
      opts.toggle.addEventListener('click', (event) => {
        const button = event.target.closest('button[data-layer]');
        if(!button) return;
        opts.toggle.querySelectorAll('button').forEach(b => b.classList.remove('active'));
        button.classList.add('active');
        if(button.dataset.layer === 'terrain'){ map.removeLayer(streets); terrain.addTo(map); }
        else { map.removeLayer(terrain); streets.addTo(map); }
      });
    }
    return { map, terrain, streets };
  }

  /* White casing under a coloured line, so the route reads on any tile. */
  function line(group, latlngs, opts){
    opts = opts || {};
    L.polyline(latlngs, {
      color:'#ffffff', weight: (opts.weight || 4.5) + 3.5, opacity:.85,
      lineCap:'round', lineJoin:'round', interactive:false,
    }).addTo(group);
    return L.polyline(latlngs, {
      color: COLOUR.route, weight: opts.weight || 4.5, opacity:1,
      lineCap:'round', lineJoin:'round',
    }).addTo(group);
  }

  function startMarker(group, latlng, name){
    return L.circleMarker(latlng, {radius:8, color:COLOUR.start, weight:3, fillColor:'#fff', fillOpacity:1})
      .bindTooltip('Start · ' + name, {direction:'top'}).addTo(group);
  }

  function finishMarker(group, latlng, name){
    return L.circleMarker(latlng, {radius:8, color:COLOUR.finish, weight:3, fillColor:'#fff', fillOpacity:1})
      .bindTooltip('Ziel · ' + name, {direction:'top'}).addTo(group);
  }

  function waypointMarker(group, latlng, name){
    return L.circleMarker(latlng, {radius:5.5, color:'#fff', weight:2, fillColor:COLOUR.point, fillOpacity:1})
      .bindPopup('<div class="rr-popup">' + name + '</div>').addTo(group);
  }

  function lodgingMarker(group, latlng, html){
    return L.marker(latlng, {
      icon: L.divIcon({ className:'bed-pin', html:'<span>⚑</span>', iconSize:[26,26], iconAnchor:[13,13] }),
    }).bindPopup('<div class="rr-popup">' + html + '</div>').addTo(group);
  }

  return { create, line, startMarker, finishMarker, waypointMarker, lodgingMarker, COLOUR };
})();
