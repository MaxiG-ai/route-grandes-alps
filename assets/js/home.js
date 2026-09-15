/* home.js -- overview map on the landing page, drawn from data/overview.json.
   Figures and the stage table are pre-rendered, so this is only the map. */
(function(){
  const element = document.getElementById('overviewMap');
  if(!element || typeof L === 'undefined') return;
  const status = window.RGA_STATUS || {};   /* {"day-01": "ridden", ...} */
  const names = window.RGA_NAMES || {};

  const { map } = RGA.map.create(element, { scrollWheelZoom: false });
  const group = L.layerGroup().addTo(map);

  fetch('data/overview.json')
    .then(response => {
      if(!response.ok) throw new Error(response.status);
      return response.json();
    })
    .then(stages => {
      const everything = [];
      for(const stage of stages){
        const line = RGA.map.line(group, stage.points, status[stage.id] || 'planned', { weight:3.5 });
        line.bindTooltip('Tag ' + stage.no + ' · ' + (names[stage.id] || ''), { sticky:true });
        line.on('click', () => { window.location.href = stage.id + '.html'; });
        line.on('mouseover', () => line.setStyle({ weight:5.5 }));
        line.on('mouseout', () => line.setStyle({ weight:3.5 }));
        everything.push(...stage.points);
      }
      if(everything.length) map.fitBounds(L.latLngBounds(everything), { padding:[24, 24] });
    })
    .catch(() => {
      element.innerHTML = '<p class="map-error">Übersichtskarte konnte nicht geladen werden '
        + '(<code>data/overview.json</code>).</p>';
    });
})();
