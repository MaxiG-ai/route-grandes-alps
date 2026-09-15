/* format.js -- German number and date formats. Loaded by every page and
   sets up window.RGA. The site is German, the code is not. */
window.RGA = window.RGA || {};

RGA.fmt = (function(){
  const WEEKDAY = ['So.','Mo.','Di.','Mi.','Do.','Fr.','Sa.'];
  const MONTH = ['Jan.','Feb.','März','Apr.','Mai','Juni','Juli','Aug.','Sep.','Okt.','Nov.','Dez.'];

  function number(n){ return Math.round(n).toLocaleString('de-DE'); }

  function km(value){
    return value.toLocaleString('de-DE', {minimumFractionDigits:1, maximumFractionDigits:1}) + ' km';
  }

  function metres(n, sign){
    const text = number(Math.abs(n)) + ' m';
    if(sign === '+') return '+' + text;
    if(sign === '-') return '−' + text;   /* real minus sign, not a hyphen */
    return text;
  }

  function grams(g){
    if(g >= 1000){
      return (g / 1000).toLocaleString('de-DE', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' kg';
    }
    return number(g) + ' g';
  }

  function shortDate(iso){
    const d = new Date(iso + 'T12:00:00');
    return `${WEEKDAY[d.getDay()]}, ${d.getDate()}. ${MONTH[d.getMonth()]}`;
  }

  return { number, km, metres, grams, shortDate };
})();
