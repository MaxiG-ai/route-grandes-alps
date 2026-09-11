/* profile.js -- elevation profile as SVG, with a cursor that shows on the map.
   The fill is a hypsometric ramp in tricolore tones: valley blue, summit red. */
window.RGA = window.RGA || {};

RGA.profile = (function(){
  const NS = 'http://www.w3.org/2000/svg';
  const RAMP = [
    [0.00, [0, 61, 120]],    /* --blue-deep: valley floor */
    [0.32, [0, 85, 164]],    /* --blue                    */
    [0.55, [240, 243, 248]], /* white                     */
    [0.78, [239, 65, 53]],   /* --red                     */
    [1.00, [168, 18, 31]],   /* summit                    */
  ];

  function rampColour(t){
    t = Math.max(0, Math.min(1, t));
    for(let i = 0; i < RAMP.length - 1; i++){
      const [t0, c0] = RAMP[i], [t1, c1] = RAMP[i + 1];
      if(t >= t0 && t <= t1){
        const f = (t - t0) / (t1 - t0);
        return 'rgb(' + c0.map((v, k) => Math.round(v + (c1[k] - v) * f)).join(',') + ')';
      }
    }
    return 'rgb(' + RAMP[RAMP.length - 1][1].join(',') + ')';
  }

  function el(tag, attrs){
    const node = document.createElementNS(NS, tag);
    if(attrs) for(const key in attrs) node.setAttribute(key, attrs[key]);
    return node;
  }

  /* opts: { svg, tip, points, onHover(point), onLeave() } */
  function draw(opts){
    const { svg, tip, points } = opts;
    svg.innerHTML = '';
    const W = 1000, H = 220, padL = 6, padR = 6, padT = 16, padB = 26;
    const maxD = points[points.length - 1].d;
    let minEle = Infinity, maxEle = -Infinity;
    for(const p of points){
      if(p.ele < minEle) minEle = p.ele;
      if(p.ele > maxEle) maxEle = p.ele;
    }
    const span = Math.max(1, maxEle - minEle);
    const yMin = minEle - span * 0.12, yMax = maxEle + span * 0.12;
    const X = d => padL + (d / maxD) * (W - padL - padR);
    const Y = ele => H - padB - ((ele - yMin) / (yMax - yMin)) * (H - padT - padB);

    const defs = el('defs');
    const gradient = el('linearGradient', {id:'profileGradient', x1:'0', y1:'0', x2:'0', y2:'1'});
    [[1.0, 0], [0.78, 0.22], [0.55, 0.45], [0.30, 0.7], [0.0, 1.0]].forEach(([t, offset]) => {
      gradient.appendChild(el('stop', {offset:(offset * 100) + '%', 'stop-color':rampColour(t)}));
    });
    defs.appendChild(gradient);
    svg.appendChild(defs);

    for(let i = 0; i <= 3; i++){
      const y = Y(yMin + (yMax - yMin) * i / 3);
      svg.appendChild(el('line', {x1:padL, y1:y, x2:W - padR, y2:y, stroke:'#dfe4ee', 'stroke-width':1}));
    }

    let path = `M ${X(0)} ${Y(points[0].ele)}`;
    for(const p of points) path += ` L ${X(p.d)} ${Y(p.ele)}`;
    svg.appendChild(el('path', {d: path + ` L ${X(maxD)} ${H - padB} L ${X(0)} ${H - padB} Z`,
      fill:'url(#profileGradient)', opacity:'0.5'}));
    svg.appendChild(el('path', {d: path, fill:'none', stroke:'#003d78', 'stroke-width':2}));

    const hover = el('g', {opacity:'0'});
    const hoverLine = el('line', {y1:padT, y2:H - padB, stroke:'#111827', 'stroke-width':1, 'stroke-dasharray':'3,3'});
    const hoverDot = el('circle', {r:4.5, fill:'#111827', stroke:'#fff', 'stroke-width':2});
    hover.appendChild(hoverLine);
    hover.appendChild(hoverDot);
    svg.appendChild(hover);

    const hitArea = el('rect', {x:padL, y:0, width:W - padL - padR, height:H, fill:'transparent'});
    svg.appendChild(hitArea);

    function move(clientX){
      const box = svg.getBoundingClientRect();
      const target = ((clientX - box.left) / box.width) * maxD;
      let nearest = points[0], best = Infinity;
      for(const p of points){
        const gap = Math.abs(p.d - target);
        if(gap < best){ best = gap; nearest = p; }
      }
      const x = X(nearest.d), y = Y(nearest.ele);
      hoverLine.setAttribute('x1', x);
      hoverLine.setAttribute('x2', x);
      hoverDot.setAttribute('cx', x);
      hoverDot.setAttribute('cy', y);
      hover.setAttribute('opacity', '1');
      if(tip){
        tip.textContent = RGA.fmt.km(nearest.d) + ' · ' + RGA.fmt.metres(nearest.ele);
        tip.style.left = ((x / W) * box.width) + 'px';
        tip.classList.add('show');
      }
      if(opts.onHover) opts.onHover(nearest);
    }

    hitArea.addEventListener('pointermove', event => move(event.clientX));
    hitArea.addEventListener('pointerleave', () => {
      hover.setAttribute('opacity', '0');
      if(tip) tip.classList.remove('show');
      if(opts.onLeave) opts.onLeave();
    });
  }

  return { draw, rampColour };
})();
