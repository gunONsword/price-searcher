(() => {
  const intro = document.getElementById('brandIntro');
  try { if (!sessionStorage.getItem('hardprice-entered')) intro.showModal(); } catch {}
  document.getElementById('enterApp').onclick = () => { intro.close(); try { sessionStorage.setItem('hardprice-entered','1'); } catch {} };
  document.getElementById('openBrand').onclick = () => intro.showModal();
  const select = document.getElementById('categorySelect'), chips = document.getElementById('categoryChips');
  const names = {gpu:'GPU',cpu:'CPU',ram:'RAM',ssd:'SSD',motherboard:'主板',custom:'自定义'};
  [...select.options].forEach(option => {
    const b = document.createElement('button'); b.type = 'button'; b.textContent = names[option.value] || option.text;
    b.dataset.category = option.value; b.setAttribute('aria-pressed',String(option.value === select.value));
    b.onclick = () => { select.value = option.value; select.dispatchEvent(new Event('change')); };
    chips.appendChild(b);
  });
  const sync = () => chips.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.category===select.value)));
  select.addEventListener('change',sync);
  const price = document.getElementById('cardLow');
  new MutationObserver(() => {price.classList.remove('price-refresh');requestAnimationFrame(()=>price.classList.add('price-refresh'));}).observe(price,{childList:true});
  // Keep the brand hero on the overview; let real price charts lead the detail view.
  new MutationObserver(() => {document.getElementById('brandHero').hidden=!document.getElementById('detailSection').classList.contains('hidden');}).observe(document.getElementById('detailSection'),{attributes:true,attributeFilter:['class']});
})();
