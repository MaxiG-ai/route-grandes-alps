/* format.js -- deutsche Zahlen- und Datumsformate, Reisestatus.
   Wird von allen Seiten geladen; legt window.RGA an. */
window.RGA = window.RGA || {};

RGA.fmt = (function(){
  const WOCHENTAG = ['So.','Mo.','Di.','Mi.','Do.','Fr.','Sa.'];
  const MONAT = ['Jan.','Feb.','März','Apr.','Mai','Juni','Juli','Aug.','Sep.','Okt.','Nov.','Dez.'];

  function zahl(n){ return Math.round(n).toLocaleString('de-DE'); }
  function km(v){ return v.toLocaleString('de-DE', {minimumFractionDigits:1, maximumFractionDigits:1}) + ' km'; }
  function meter(n, vorzeichen){
    const z = zahl(Math.abs(n)) + ' m';
    if(vorzeichen === '+') return '+' + z;
    if(vorzeichen === '-') return '−' + z;   /* echtes Minuszeichen */
    return z;
  }
  function gramm(g){
    if(g >= 1000) return (g/1000).toLocaleString('de-DE', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' kg';
    return zahl(g) + ' g';
  }
  function datumTeile(iso){
    const d = new Date(iso + 'T12:00:00');
    return { wt: WOCHENTAG[d.getDay()], tag: d.getDate(), monat: MONAT[d.getMonth()], jahr: d.getFullYear() };
  }
  function datumKurz(iso){
    const t = datumTeile(iso);
    return `${t.wt}, ${t.tag}. ${t.monat}`;
  }
  return { zahl, km, meter, gramm, datumKurz, datumTeile };
})();
