/* packliste.js -- Häkchen zum Abpacken, gemerkt im Browser des Besuchers.
   Die Liste selbst und alle Gewichte sind vorgerendert. */
(function(){
  const liste = document.getElementById('packliste');
  if(!liste) return;
  const SCHLUESSEL = 'rga-packliste-v1';
  const kaesten = [...liste.querySelectorAll('input[type=checkbox][data-id]')];
  const anzeige = document.getElementById('packFortschritt');
  const balken = document.getElementById('packFortschrittBalken');

  function lesen(){
    try { return JSON.parse(localStorage.getItem(SCHLUESSEL)) || {}; }
    catch(e){ return {}; }
  }
  function schreiben(stand){
    try { localStorage.setItem(SCHLUESSEL, JSON.stringify(stand)); }
    catch(e){ /* Privatmodus: dann eben nur für diese Sitzung */ }
  }
  function aktualisieren(){
    const fertig = kaesten.filter(k => k.checked);
    const gramm = fertig.reduce((s, k) => s + Number(k.dataset.gramm || 0), 0);
    kaesten.forEach(k => k.closest('.pack-zeile').classList.toggle('erledigt', k.checked));
    if(anzeige){
      anzeige.innerHTML = '<b>' + fertig.length + '</b> von <b>' + kaesten.length
        + '</b> Posten gepackt · <b>' + RGA.fmt.gramm(gramm) + '</b> im Gepäck';
    }
    if(balken) balken.style.width = (kaesten.length ? fertig.length / kaesten.length * 100 : 0).toFixed(1) + '%';
  }

  const stand = lesen();
  kaesten.forEach(k => {
    k.checked = !!stand[k.dataset.id];
    k.addEventListener('change', () => {
      const s = lesen();
      if(k.checked) s[k.dataset.id] = 1; else delete s[k.dataset.id];
      schreiben(s);
      aktualisieren();
    });
  });
  aktualisieren();

  const zuruecksetzen = document.getElementById('packReset');
  if(zuruecksetzen) zuruecksetzen.addEventListener('click', () => {
    kaesten.forEach(k => { k.checked = false; });
    schreiben({});
    aktualisieren();
  });
})();
