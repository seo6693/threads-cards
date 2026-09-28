// Run in the browser pane on a coupang.com category page sorted by 쿠팡 랭킹순
// (the default sort), e.g. https://www.coupang.com/np/categories/502492?page=1
// Returns the ranked list: rank, product id, exact title, review count, and whether
// it carries the 로켓프레시 badge. Prices here include coupons tied to the signed-in
// account (e.g. "웰컴백 쿠폰 100%"), so never use them; take the price from Partners.
await new Promise(r => setTimeout(r, 2500));
const page = Number(new URL(location.href).searchParams.get('page') || 1);
const seen = new Set(), out = [];
for (const a of document.querySelectorAll('a[href*="/vp/products/"]')) {
  const pid = (a.href.match(/products\/(\d+)/) || [])[1];
  if (!pid || seen.has(pid)) continue;
  seen.add(pid);
  const lines = a.innerText.split('\n').map(s => s.trim()).filter(Boolean);
  const reviews = (a.innerText.match(/\(([\d,]+)\)\s*$/) || [])[1];
  out.push({rank: (page - 1) * 60 + out.length + 1, pid, title: lines[0],
            reviews: reviews ? Number(reviews.replace(/,/g, '')) : null,
            fresh: !!a.querySelector('img[src*="fresh"], img[alt*="프레시"]')});
}
out;
