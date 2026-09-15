/* day.js -- controller for one stage page.
   Text, figures and the photo grid are already in the HTML (tools/build.py);
   this only adds the map, the elevation profile and the lightbox. */
(function(){
  const stage = window.RGA_STAGE;
  if(!stage) return;

  RGA.lightbox.init(document.getElementById('photoGrid'));

  const mapElement = document.getElementById('map');
  if(!mapElement || typeof L === 'undefined') return;

  const { map } = RGA.map.create(mapElement, { toggle: document.getElementById('layerToggle') });
  const group = L.layerGroup().addTo(map);
  const svg = document.getElementById('profileSvg');
  const tip = document.getElementById('profileTip');
  let cursor = null;

  /* Waypoint names come out of komoot in English; data/waypoints.json
     translates them without touching the generated track files. If the file
     is missing, the original names stay. */
  const namesReady = fetch('data/waypoints.json')
    .then(response => response.ok ? response.json() : {})
    .then(data => (data && data.names) || {})
    .catch(() => ({}));

  Promise.all([
    fetch('data/tracks/' + stage.id + '.json')
      .then(response => {
        if(!response.ok) throw new Error(response.status + ' ' + response.statusText);
        return response.json();
      }),
    namesReady,
  ])
    .then(([track, names]) => {
      const latlngs = track.points.map(p => [p.lat, p.lon]);
      RGA.map.line(group, latlngs);
      RGA.map.startMarker(group, latlngs[0], stage.from);
      RGA.map.finishMarker(group, latlngs[latlngs.length - 1], stage.to);
      for(const w of track.waypoints){
        RGA.map.waypointMarker(group, [w.lat, w.lon], names[w.name] || w.name);
      }
      if(stage.lodging) RGA.map.lodgingMarker(group, stage.lodging.pos, stage.lodging.html);

      cursor = L.circleMarker(latlngs[0], {
        radius:6, color:'#fff', weight:2, fillColor:'#111827', opacity:0, fillOpacity:0,
      }).addTo(group);

      map.fitBounds(L.latLngBounds(latlngs), { padding:[28, 28] });

      if(svg) RGA.profile.draw({
        svg, tip, points: track.points,
        onHover: point => cursor.setLatLng([point.lat, point.lon]).setStyle({opacity:1, fillOpacity:1}),
        onLeave: () => cursor.setStyle({opacity:0, fillOpacity:0}),
      });
    })
    .catch(error => {
      mapElement.innerHTML = '<p class="map-error">Track konnte nicht geladen werden ('
        + error.message + '). Liegt <code>data/tracks/' + stage.id + '.json</code> auf dem Server?</p>';
      if(svg) svg.closest('.profile-block').hidden = true;
    });
})();
