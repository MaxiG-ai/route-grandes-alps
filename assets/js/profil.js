/* profil.js -- Höhenprofil als SVG, mit Cursor der auf die Karte durchschlägt.
   Farbverlauf ist die hypsometrische Rampe in Trikolore-Tönen. */
window.RGA = window.RGA || {};

RGA.profil = (function(){
  const NS = 'http://www.w3.org/2000/svg';
  const RAMPE = [
    [0.00, [0, 61, 120]],    /* --bleu-tief: Tal   */
    [0.32, [0, 85, 164]],    /* --bleu             */
    [0.55, [240, 243, 248]], /* weiß               */
    [0.78, [239, 65, 53]],   /* --rouge            */
    [1.00, [168, 18, 31]],   /* Gipfel             */
  ];

  function rampenFarbe(t){
    t = Math.max(0, Math.min(1, t));
    for(let i = 0; i < RAMPE.length - 1; i++){
      const [t0, c0] = RAMPE[i], [t1, c1] = RAMPE[i + 1];
      if(t >= t0 && t <= t1){
        const f = (t - t0) / (t1 - t0);
        return 'rgb(' + c0.map((v, k) => Math.round(v + (c1[k] - v) * f)).join(',') + ')';
      }
    }
    return 'rgb(' + RAMPE[RAMPE.length - 1][1].join(',') + ')';
  }

  function el(tag, attrs){
    const n = document.createElementNS(NS, tag);
    if(attrs) for(const k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }

  /* opt: { svg, tip, punkte, beiHover(punkt), beiVerlassen() } */
  function zeichnen(opt){
    const { svg, tip, punkte } = opt;
    svg.innerHTML = '';
    const W = 1000, H = 220, padL = 6, padR = 6, padT = 16, padB = 26;
    const maxD = punkte[punkte.length - 1].d;
    let minE = Infinity, maxE = -Infinity;
    for(const p of punkte){ if(p.ele < minE) minE = p.ele; if(p.ele > maxE) maxE = p.ele; }
    const spanne = Math.max(1, maxE - minE);
    const yMin = minE - spanne * 0.12, yMax = maxE + spanne * 0.12;
    const X = d => padL + (d / maxD) * (W - padL - padR);
    const Y = e => H - padB - ((e - yMin) / (yMax - yMin)) * (H - padT - padB);

    const defs = el('defs');
    const grad = el('linearGradient', {id:'profGrad', x1:'0', y1:'0', x2:'0', y2:'1'});
    [[1.0, 0], [0.78, 0.22], [0.55, 0.45], [0.30, 0.7], [0.0, 1.0]].forEach(([rt, off]) => {
      grad.appendChild(el('stop', {offset:(off * 100) + '%', 'stop-color':rampenFarbe(rt)}));
    });
    defs.appendChild(grad);
    svg.appendChild(defs);

    for(let g = 0; g <= 3; g++){
      const y = Y(yMin + (yMax - yMin) * g / 3);
      svg.appendChild(el('line', {x1:padL, y1:y, x2:W - padR, y2:y, stroke:'#dfe4ee', 'stroke-width':1}));
    }

    let d = `M ${X(0)} ${Y(punkte[0].ele)}`;
    for(const p of punkte) d += ` L ${X(p.d)} ${Y(p.ele)}`;
    svg.appendChild(el('path', {d: d + ` L ${X(maxD)} ${H - padB} L ${X(0)} ${H - padB} Z`,
      fill:'url(#profGrad)', opacity:'0.5'}));
    svg.appendChild(el('path', {d, fill:'none', stroke:'#003d78', 'stroke-width':2}));

    const hoverG = el('g', {opacity:'0'});
    const hoverLinie = el('line', {y1:padT, y2:H - padB, stroke:'#111827', 'stroke-width':1, 'stroke-dasharray':'3,3'});
    const hoverPunkt = el('circle', {r:4.5, fill:'#111827', stroke:'#fff', 'stroke-width':2});
    hoverG.appendChild(hoverLinie); hoverG.appendChild(hoverPunkt);
    svg.appendChild(hoverG);

    const flaeche = el('rect', {x:padL, y:0, width:W - padL - padR, height:H, fill:'transparent'});
    svg.appendChild(flaeche);

    function bewegen(clientX){
      const rect = svg.getBoundingClientRect();
      const ziel = ((clientX - rect.left) / rect.width) * maxD;
      let nah = punkte[0], abstand = Infinity;
      for(const p of punkte){
        const diff = Math.abs(p.d - ziel);
        if(diff < abstand){ abstand = diff; nah = p; }
      }
      const x = X(nah.d), y = Y(nah.ele);
      hoverLinie.setAttribute('x1', x); hoverLinie.setAttribute('x2', x);
      hoverPunkt.setAttribute('cx', x); hoverPunkt.setAttribute('cy', y);
      hoverG.setAttribute('opacity', '1');
      if(tip){
        tip.textContent = RGA.fmt.km(nah.d) + ' · ' + RGA.fmt.meter(nah.ele);
        tip.style.left = ((x / W) * rect.width) + 'px';
        tip.classList.add('zeigen');
      }
      if(opt.beiHover) opt.beiHover(nah);
    }
    flaeche.addEventListener('pointermove', e => bewegen(e.clientX));
    flaeche.addEventListener('pointerleave', () => {
      hoverG.setAttribute('opacity', '0');
      if(tip) tip.classList.remove('zeigen');
      if(opt.beiVerlassen) opt.beiVerlassen();
    });
  }

  return { zeichnen, rampenFarbe };
})();
