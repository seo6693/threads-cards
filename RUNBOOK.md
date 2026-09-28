# RUNBOOK — one scheduled run = one post for one project

A scheduled task runs this for exactly one project (`nutri` or `living`).
Never touch the other project's folder. Work unattended: do not ask the
user anything; if a step cannot be done, stop and report why (nothing
gets posted, which is fine).

## 0. Setup
1. Attach the repo: `add_repo(owner="seo6693", repo="threads-cards", access="push")`,
   then clone: `git clone --depth 1 https://github.com/seo6693/threads-cards ~/threads-cards`.
2. `cd ~/threads-cards && python3 scripts/new_post.py next <project>`
   → gives `keyword`, `backup_keywords`, `skip_product_ids`, `selection`, `copy_rules`, `tone`, `theme`.

The browser is the **built-in browser pane on the user's computer**
(`mcp__remote-devices__Claude_Browser__*`). It is already signed in to
Coupang Partners and Coupang. If a site asks for access, call
`Claude_Browser__request_access` with scope `site`. If the pane cannot be
reached (computer asleep/offline), stop: report "컴퓨터가 꺼져 있어 이번 회차는 건너뜀".
If Coupang Partners shows a login page, stop and report that a login is needed.
Never type passwords.

## 1. Find candidates (Coupang Partners search)
- Open `https://partners.coupang.com/#affiliate/ws/link/0/<keyword>` and wait ~3s.
- Read the list with JS:
  ```js
  [...document.querySelectorAll('.product-item')].slice(0,20).map((e,i)=>({i,
    name:e.querySelector('.product-description')?.innerText,
    discount:e.querySelector('.discount')?.innerText,
    price:e.querySelector('.sale-price')?.innerText}))
  ```
- Prefer items with a discount and a price inside `selection.min_price..max_price`.
  Skip price 0원 items and anything off-topic for the project
  (e.g. a car charger in the 무드등 results for `living` is fine only if it is 생활용품;
  nothing non-supplement for `nutri`).

## 2. Create the partner link for the chosen item
- Click its link button: `document.querySelectorAll('.product-item')[i].querySelector('.btn-generate-link').click()`,
  wait ~3s.
- The page URL now contains `product[productId]=...`; the body shows `단축 URL` then
  `https://link.coupang.com/a/XXXX`. Read both:
  ```js
  ({pid:new URL(location.href.replace('#','')).searchParams.get('product[productId]'),
    link:(document.body.innerText.match(/https:\/\/link\.coupang\.com\/a\/\w+/)||[])[0]})
  ```
- If `pid` is in `skip_product_ids`, go back and pick another item.

## 3. Check the product page (quality gate + facts)
- Navigate to the short link; it lands on the coupang.com product page.
- Read with JS: `document.title`, `document.body.innerText` from the start
  (name, prices: 일반할인가 / 와우 쿠폰가, delivery line, spec lines like `총 캡슐/정 수량`),
  the `상품 리뷰` block (review count, 최고 %, the aspect lines such as
  `청소 성능 / 아주뛰어나요 / 92%`) and the first ~4 reviews after `베스트순`,
  plus `meta[property="og:image"]` (640x640 main image).
- Gate: review count ≥ `min_reviews` and 최고 % ≥ `min_top_rating_pct`.
  If it fails, go back to step 1 and try the next candidate (max 5 tries,
  then the backup keywords). If nothing passes, stop and report.

## 4. Get the product image into the workspace
The shell cannot reach coupangcdn, so pass the image through the browser:
1. Navigate the pane to the og:image URL (prefix `https:` if it starts with `//`).
2. Run:
   ```js
   (()=>{const i=document.images[0],c=document.createElement('canvas');
    c.width=i.naturalWidth;c.height=i.naturalHeight;const x=c.getContext('2d');
    x.fillStyle='#fff';x.fillRect(0,0,c.width,c.height);x.drawImage(i,0,0);
    return 'BEGIN'+c.toDataURL('image/jpeg',0.9).split(',')[1]+'END'+'#'.repeat(40000)})()
   ```
   The padding makes the tool save the result to a file (path is in the tool message).
3. Decode it:
   ```python
   import json,re,base64
   t=json.load(open(PATH))[0]['text']
   open('/tmp/product.jpg','wb').write(base64.b64decode(re.search(r'BEGIN([A-Za-z0-9+/=]+)END',t).group(1)))
   ```
4. Look at the image (Read tool) to make sure it is the product, not a blank/banner.

## 5. Write the draft (`/tmp/draft.json`)
Follow `copy_rules` and `tone`. **Every fact and number must come from the
product page or its reviews — never invent.** Card quotes are short paraphrases
of real reviews (the card already says "구매자 리뷰를 요약한 내용이에요").

```json
{
  "product_id": "<pid>", "product_name": "<short name>", "keyword": "<keyword>",
  "link": "https://link.coupang.com/a/XXXX", "image": "/tmp/product.jpg",
  "cards": {
    "hook":    {"kicker": "고민/상황 한 줄 (질문형)", "big1": "핵심 2~6자", "big2": "숫자 또는 결론 2~5자",
                "line1": "핵심 장점 한 줄", "line2": "리뷰 N개 · M%가 '최고' 평가"},
    "product": {"pill": "특징 · 특징 · 배송", "brand": "브랜드 모델", "name": "상품 종류 (짧게)",
                "sub": "구성/용량 한 줄", "badge_top": "N% 할인", "badge_price": "X원"},
    "reviews": {"title": "먼저 써본 사람들 반응", "big": "M%", "caption": "리뷰 N개 중 '최고' 평가",
                "quotes": [["“짧은 인용”","근거 한 줄"],["“…”","…"],["“…”","…"]],
                "footer": "링크는 댓글에"}
  },
  "text": "<본문>",
  "reply_note": "※ 가격·쿠폰은 시점마다 달라질 수 있어요"
}
```
(`nutri` title: "먼저 먹어본 사람들 반응".)

Body template (≤ 500 chars, **no links in the body**):
```
<후킹 한 줄> <이모지 1개>

<브랜드 상품명>
✔️ <장점 1>
✔️ <장점 2>
✔️ <장점 3>

리뷰 N개 중 M%가 '최고' ⭐
<리뷰 세부 지표 1개가 있으면>

<리뷰에 자주 나온 단점 한 줄 — living은 있으면 필수>

지금 N% 할인 X원
링크는 댓글에 👇

이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.
```
Use the 일반할인가 (not the 와우 쿠폰가) as the price. If the 와우 price is lower,
set `reply_note` to `※ 가격·쿠폰은 시점마다 달라질 수 있어요 (와우 회원은 쿠폰가 더 저렴)`.

## 6. Queue, check, publish
1. `python3 scripts/new_post.py queue <project> /tmp/draft.json` — fix and retry if it rejects the draft.
2. Look at the three rendered cards in the printed `cards` folder (Read tool).
   Fix overlaps or wrong text by editing the draft and re-running (delete the
   previous `cards/<slug>` and `queue/<slug>.json` first).
3. Commit only this project's files plus `state.json`:
   `git add projects/<project> && git commit -m "Queue <project>: <product_name>"` and push.
   If the push is rejected, `git pull --rebase origin main` and push again.
4. GitHub Actions publishes it. Poll `git fetch` every 15s (max ~5 min) until
   `projects/<project>/done/<slug>.json` or `failed/<slug>.json` exists on origin/main,
   then read it.

**One run = at most one post.** If the result lands in `failed/`:
- transient/5xx error → move that same file back to `queue/` (drop `error`/`published_at`), push, and wait once more;
- anything else → stop and report.
Never pick or queue a second product in the same run, even if the first one failed.
Duplicate guard (run it right after step 0, before any browser work):
`python3 scripts/new_post.py slot <project>` prints this run's slot and whether it was
already posted.
If it prints `"blocked": true`, Meta has blocked this account's API access: stop immediately
(no browser work, no skip record needed) and report "계정 차단 상태라 건너뜀". Only a person clears
`projects/<project>/BLOCKED.json` after fixing the account. Only if it says `"already_posted": true` stop — another run covered this slot.
(Posts made before this slot's start time never count, so a manual/test post earlier does not
block the next scheduled slot.)

**Whenever a run ends without posting** (duplicate guard, browser unreachable, login needed,
no product passed the gate, publish failed for a non-transient reason), record it so the
dashboard can show why:
`python3 scripts/new_post.py skip <project> "<짧은 한국어 이유>"`, then commit and push
`projects/<project>/skipped/`.

## 7. Report (last message of the run)
One short Korean summary: 계정, 상품명, 가격, 게시물 주소(permalink), 첫 댓글 성공 여부.
If it failed, the reason. Nothing else.
