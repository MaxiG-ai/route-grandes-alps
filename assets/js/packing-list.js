/* packing-list.js -- packing checkboxes, remembered in the visitor's browser.
   The list itself and every weight are pre-rendered. */
(function(){
  const list = document.getElementById('packingList');
  if(!list) return;
  const STORAGE_KEY = 'rga-packing-list-v1';
  const boxes = [...list.querySelectorAll('input[type=checkbox][data-id]')];
  const readout = document.getElementById('packProgress');
  const bar = document.getElementById('packProgressBar');

  function load(){
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; }
    catch(error){ return {}; }
  }

  function save(state){
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
    catch(error){ /* private mode: keep it for this session only */ }
  }

  function update(){
    const packed = boxes.filter(b => b.checked);
    const grams = packed.reduce((sum, b) => sum + Number(b.dataset.grams || 0), 0);
    boxes.forEach(b => b.closest('.pack-row').classList.toggle('done', b.checked));
    if(readout){
      readout.innerHTML = '<b>' + packed.length + '</b> von <b>' + boxes.length
        + '</b> Posten gepackt · <b>' + RGA.fmt.grams(grams) + '</b> im Gepäck';
    }
    if(bar) bar.style.width = (boxes.length ? packed.length / boxes.length * 100 : 0).toFixed(1) + '%';
  }

  const state = load();
  boxes.forEach(box => {
    box.checked = !!state[box.dataset.id];
    box.addEventListener('change', () => {
      const current = load();
      if(box.checked) current[box.dataset.id] = 1;
      else delete current[box.dataset.id];
      save(current);
      update();
    });
  });
  update();

  const reset = document.getElementById('packReset');
  if(reset) reset.addEventListener('click', () => {
    boxes.forEach(box => { box.checked = false; });
    save({});
    update();
  });
})();
