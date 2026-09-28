// Run in the browser pane on https://pages.coupang.com/p/121237?sourceType=oms_goldbox
// (쿠팡 골드박스). Scrolls to load every item, then returns each item's product id,
// name and the deal end time computed from its "HH:MM:SS 남음" timer, in KST.
// Match the chosen product by pid (the number in /vp/products/<pid>).
for (let i = 0; i < 15; i++) { window.scrollBy(0, 2500); await new Promise(r => setTimeout(r, 700)); }
const now = Date.now(), seenAt = new Date(now).toLocaleString('sv-SE', {timeZone: 'Asia/Seoul'});
const iso = ms => new Date(ms + 9 * 3600e3).toISOString().slice(0, 19) + '+09:00';
[...document.querySelectorAll('*')]
  .filter(e => e.children.length === 0 && /^\s*\d{1,2}:\d{2}:\d{2}\s*남음\s*$/.test(e.textContent))
  .map(e => {
    let p = e; while (p && !(p.querySelector('img') && p.querySelector('a[href]'))) p = p.parentElement;
    const href = p?.querySelector('a[href]')?.href || '';
    const [h, m, s] = e.textContent.match(/\d+/g).map(Number);
    return {pid: (href.match(/products\/(\d+)/) || [])[1], name: (p?.innerText || '').split('\n')[0].slice(0, 60),
            end: iso(now + ((h * 60 + m) * 60 + s) * 1000), seen: `${e.textContent.trim()} @ ${seenAt} 골드박스`};
  });
