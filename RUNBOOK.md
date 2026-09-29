# RUNBOOK — one scheduled run = one post for one project

A scheduled task runs this for exactly one project (`nutri`, `deals` or `fresh`).
Never touch the other project's folder. Work unattended: do not ask the
user anything; if a step cannot be done, stop and report why (nothing
gets posted, which is fine).

## 0. Setup
1. Attach the repo: `add_repo(owner="seo6693", repo="threads-cards", access="push")`,
   then clone: `git clone --depth 1 https://github.com/seo6693/threads-cards ~/threads-cards`.
2. `cd ~/threads-cards && python3 scripts/new_post.py next <project>`
   → gives `keyword`, `backup_keywords`, `skip_product_ids`, `selection`, `copy_rules`, `tone`, `theme`.

3. **Take your turn on the browser.** Every account shares one browser on the user's computer.
   Right after the duplicate guard (`slot`, below) passes, run
   `python3 scripts/browser_lock.py acquire <project>` (it waits up to 45 min while another
   account's run uses the browser). If it prints `"ok": false`, record a skip
   ("다른 계정이 브라우저 사용 중") and stop. As soon as browser work is done (after step 4,
   the image is in the workspace) run `python3 scripts/browser_lock.py release <project>`.
   Also release before stopping for any reason. Do not leave uncommitted files when calling it.
4. In the browser, open **your own tab** first (`Claude_Browser__tabs_create`) and pass that
   `tabId` to every browser call; close it (`tabs_close`) when done. Never use or close other tabs.

5. **Check the Partners sign-in first** (in your tab): open
   `https://partners.coupang.com/#affiliate/ws/link/0/test`, wait ~3s. If the tab ends on
   `login.coupang.com`, Partners has logged out. Never type a password. Then:
   - `deals`: record a skip ("쿠팡파트너스 로그인 풀림") and stop (goldbox changes daily, no bank).
   - `nutri` / `fresh`: switch to **link-bank mode** if `next` shows `linkbank_unused` > 0.
     `python3 scripts/linkbank.py pick <project>` lists unused pre-made links. For `fresh`, still read
     the category ranking (coupang.com works without Partners) and take the highest-ranked item that is
     in the bank; for `nutri`, prefer an entry matching this run's keyword. Get price, discount, reviews
     and image from the entry's public `product_url` (step 3-4), use the bank `link` as the draft `link` (and add `"link_source": "bank"` to the draft),
     and skip step 2. If the bank is empty, record a skip ("쿠팡파트너스 로그인 풀림, 링크 저장분 없음") and stop.
   In both cases put "쿠팡파트너스 로그인 풀림" in the final report so the owner signs in again.

The browser is the **built-in browser pane on the user's computer**
(`mcp__remote-devices__Claude_Browser__*`). It is already signed in to
Coupang Partners and Coupang. If a site asks for access, call
`Claude_Browser__request_access` with scope `site`. If the pane cannot be
reached (computer asleep/offline), stop: report "컴퓨터가 꺼져 있어 이번 회차는 건너뜀".
If Coupang Partners shows a login page, stop and report that a login is needed.
Never type passwords.

## 1. Find candidates (Coupang Partners search)
- If `next` says `"source": "goldbox"` (특가 계정), **only goldbox items are allowed**, because the
  deal end time must be shown on every post (`require_deal_until`) and goldbox is the only place it
  can be verified:
  1. Open `https://pages.coupang.com/p/121237?sourceType=oms_goldbox` (쿠팡 골드박스), wait ~3s and
     run the contents of `scripts/goldbox_timers.js` with `javascript_tool`. It returns
     `[{pid, name, end, seen}]` — `end` is the deal end in KST from the item's "HH:MM:SS 남음" timer.
     Keep this list; `end` and `seen` go into the draft as `deal_until` unchanged.
  2. Open `https://partners.coupang.com/#affiliate/ws/best/goldbox` (same `.product-item` list and link
     buttons as search). Keep items that are in the timer list (match by product id after step 2, or by
     name), whose discount is ≥ `selection.min_discount_pct`, that are not in `selection.avoid`, and
     that end ≥ 3 hours from now (queue rejects less). Prefer everyday impulse buys (생필품, 간식,
     주방·욕실, 소형 가전).
  3. After creating the link (step 2) confirm `product[productId]` equals the timer item's `pid`.
     If it doesn't match or the item has no timer, do not post it — pick another. If no goldbox item
     qualifies, record a skip ("골드박스에 조건 맞는 상품 없음"). Never invent or guess an end time.
  - The goldbox list shows a "와우 가입 쿠폰" price for new WOW members; never use it. Take price and
    discount from the product page (step 3).
- If `next` says `"source": "category_ranking"` (로켓프레시 간편식 계정), do **not** keyword-search Partners:
  1. Open the config's `category_url` (default sort is 쿠팡 랭킹순; add `?page=2` for ranks 61-120) and run
     `scripts/category_ranking.js` with `javascript_tool`. It returns `[{rank, pid, title, reviews, fresh}]`.
  2. Walk the list from the top. Skip ids in `skip_product_ids`, items with `fresh: false`, items in
     `selection.avoid`, and items with fewer than `selection.min_reviews` reviews. Prefer the first item
     that fits this run's `keyword` (세부 분류) if one is in the top 60; otherwise take the first that fits.
  3. Paste its exact `title` into `https://partners.coupang.com/#affiliate/ws/link/0/<title>`, pick the
     `.product-item` with the same title and a `img[src*="rocket-fresh"]` badge, create the link (step 2)
     and confirm `product[productId]` equals the ranking `pid`. If not, try the next list item.
  4. Prices on the category page include coupons tied to the signed-in account (e.g. "웰컴백 쿠폰 100%" → 0원);
     never use them. Use the Partners price (`product[salesPrice]`, `product[originPrice]`,
     `product[discountRate]` in the URL after step 2) and confirm on the product page.
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

## 5. Write the draft (`/tmp/draft.json`) — this is what earns clicks
`next` gave you a `format` (rotation), `formats` (what each one is), `avoid_openings`
(first lines of recent posts), `theme_variants` and `topic_tags`. Use the suggested format
unless the product clearly does not fit it (e.g. `price_drop` needs ≥30% off); then pick
another format that is **not** in `recent_formats[-2:]`.

**Facts:** every number and claim comes from the product page or its reviews — never invent.
Never write as if the account owner used the product (no "제가 써보니"). Say "리뷰에 따르면",
"구매자들은". Card quotes are short paraphrases of real reviews.

### How to get views and clicks (apply every time)
1. **First line decides everything.** Threads shows ~2 lines before "더 보기". The first line
   must be specific and concrete, never generic ("추천템 소개해요" ✗). Pick ONE hook type, and
   don't reuse the type or the wording of `avoid_openings`:
   - 숫자 충격: "리뷰 23만 개, 불만은 딱 이것 하나"
   - 상황 공감: "새벽에 충전기 선 짧아서 폰 떨어뜨린 적 있죠"
   - 손해 회피: "이거 정가 주고 샀으면 1만3천 원 날린 거예요"
   - 반전/오해: "유산균, 균 수만 보고 고르면 반은 틀려요" (사실일 때만)
   - 비교: "2만 원대 vs 5만 원대, 리뷰 차이는 딱 하나"
2. **Structure must differ from the last posts.** Rotate between: 짧은 문단 2~3개 / 번호 목록 /
   질문-답 / 한 줄 요약형. Do not use a ✔️ list twice in a row (the checker rejects it).
   Vary length: quick_pick 3~5줄, others 6~12줄.
3. **Give a reason to open the comments.** End the body with a genuine question people can
   answer from their own life (the checker requires a question), e.g. "여러분은 유산균 아침에 드세요,
   저녁에 드세요?", "충전기 몇 W 쓰세요?". Replies are what Threads boosts.
4. **Then point to the comment**: "링크는 첫 댓글에 둘게요" / "궁금하면 댓글 확인" — vary it.
5. **One honest downside** (from reviews) builds trust and clicks; living: required when reviews show one.
6. Emojis: 0~2 in the whole post, never at the start of every line.
7. `topic_tag`: one tag from `topic_tags` or the product keyword (no spaces, dots or &).
8. First comment (`reply_text`, optional): one line that makes the click worth it, e.g.
   "오늘 가격 기준 쿠폰 적용가 확인해보세요 👇" — the link and price note are appended for you.

### Draft shape
```json
{
  "product_id": "<pid>", "product_name": "<short name>", "keyword": "<keyword>",
  "link": "https://link.coupang.com/a/XXXX", "image": "/tmp/product.jpg",
  "format": "<format id>", "topic_tag": "<tag>", "reply_text": "<optional one line>",
  "cards": { ...see below... },
  "text": "<본문 ≤500자, 링크 없음, 질문으로 끝나고, 마지막 줄에 고지 문구>",
  "reply_note": "※ 가격·쿠폰은 시점마다 달라질 수 있어요",
  "deal_until": {"end": "<end from goldbox_timers.js>", "seen": "<seen from goldbox_timers.js>"}
}
```
**특가(deals) — deal end time is mandatory.** `deal_until` must come from `scripts/goldbox_timers.js`
for the exact product. `queue` turns it into a label like `9/29(화) 오전 7시까지` and rejects the draft
unless `text` contains that label verbatim — put it in an early line, e.g.
`⏰ 골드박스 특가 9/29(화) 오전 7시까지`. The label is added automatically to the product card, the
video (top pill) and the first comment (`⏰ 특가 … (쿠팡 골드박스 표시 기준)`). If the product has
no timer, do not post it. The publisher also refuses to post a deal that ends within 30 minutes.
Cards needed per format (`formats[fmt].cards.order`); only fill what the format uses:
- `hook` for **number**: `{"kicker","big1","big2","line1","line2"}`
- `hook` for **question**: `{"kicker","question" (use \n for 2 lines),"answer"}`
- `hook` for **checklist**: `{"title" (\n ok),"items":[3 short criteria],"note"}`
- `hook` for **versus**: `{"kicker","left_label":"정가","left","right_label":"지금","right","saving","note":"가격은 수시로 바뀌어요"}`
- `product`: `{"pill","brand","name","sub","badge_top","badge_price"}`
- `reviews`: `{"title","big","caption","quotes":[[q,sub]×3],"footer"}` (`nutri` title "먼저 먹어본 사람들 반응")

**Video format (`price_motion`, about every third post).** No `cards`; give `motion` instead:
```json
"motion": {
  "hook": ["밀크씨슬", "아직도", "237원에", "드세요?"],   // 3-4 words, ≤5 chars each is best; last word is the punch (shown red)
  "unit": "한 알",                                      // 한 알 / 1포 / 1개 / 1롤 … whatever the product is sold in
  "from_price": 237, "to_price": 118,                  // per-unit: 정가 ÷ 개수 and 일반할인가 ÷ 개수, rounded
  "stamp": "반값",                                      // ≥50% off → "반값", otherwise "<할인율>%↓" (e.g. "38%↓")
  "name": "나우푸드 밀크씨슬 200정",                     // short
  "badge_price": "23,660원",                            // 일반할인가
  "stats": [["리뷰", 73428, "개"], ["'복용 아주 편해요'", 74, "%"]],   // real numbers from the page
  "cta": "첫 댓글에 링크",
  // leave out "style" and "palette": queue rotates them automatically (slam / receipt / slot / split
  // styles, never the same look twice in a row). Each style uses the same fields above.
}
```
Only use it for products with ≥20% off and a countable unit. Otherwise pick another format.
The hook must make a true statement or honest question from those numbers. The text body is short
(3-6 lines) and still ends with a question. Watch one frame of the video (the `poster.jpg`) before pushing; check that no text overlaps and the price is readable.

The last line of `text` is always exactly:
`이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.`
Use the 일반할인가 (not the 와우 쿠폰가) as the price. If the 와우 price is lower,
set `reply_note` to `※ 가격·쿠폰은 시점마다 달라질 수 있어요 (와우 회원은 쿠폰가 더 저렴)`.

## 6. Queue, check, publish
1. `python3 scripts/new_post.py queue <project> /tmp/draft.json` — fix and retry if it rejects the draft.
2. Look at every rendered card (or `poster.jpg` for a video) in the printed `cards` folder (Read tool).
   Fix overlaps or wrong text by editing the draft and re-running (delete the
   previous `cards/<slug>` and `queue/<slug>.json` first).
3. Commit only this project's files plus `state.json`:
   `git add projects/<project> && git commit -m "Queue <project>: <product_name>"` and push.
   If the push is rejected, `git pull --rebase origin main` and push again.
4. The post goes out at its random `publish_after` time (printed by `queue`, 4–42 min later),
   picked up by a GitHub Actions job that runs every 10 minutes. Poll `git fetch` every 60s
   (max ~60 min) until
   `projects/<project>/done/<slug>.json` or `failed/<slug>.json` exists on origin/main,
   then read it.

**One run = at most one post.** If the result lands in `failed/`:
- transient/5xx error → move that same file back to `queue/` (drop `error`/`published_at`), push, and wait once more;
- anything else → stop and report.
Never pick or queue a second product in the same run, even if the first one failed.
Duplicate guard (run it right after step 0, before any browser work):
`python3 scripts/new_post.py slot <project>` prints this run's slot and whether it was
already posted. **Make-up run:** if the run's message says it is a 보충(make-up) run for a slot
skipped earlier today, use `python3 scripts/new_post.py slot <project> makeup` instead; it allows
one more post only while today's posts are below the daily quota.
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
