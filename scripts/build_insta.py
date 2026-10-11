"""Build insta/index.html: a phone-friendly 'Instagram pack' page.
For every Threads post published in the last 7 days it shows the images (or the video),
an Instagram-ready caption (ad label first, link line rewritten to point at the profile
link, disclosure kept, 5 hashtags) with one-tap copy, and a one-tap 'save all photos'.
The person posts on Instagram by hand from their phone; nothing here touches Instagram.
Served at https://seo6693.github.io/threads-cards/insta/"""
import datetime as dt
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
KST = dt.timezone(dt.timedelta(hours=9))
DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
SHOP = "https://seo6693.github.io/threads-cards/shop/{}/"
# Only projects whose config has "channel": "instagram_manual" appear here (Instagram is a
# different topic from the Threads accounts). Hashtags come from that config's topic_tags.
LINK_LINE = "👉 상품 링크는 프로필 링크 '상품 모음'에 모아뒀어요"


def caption(d, cfg):
    lines = d.get("text", "").replace(DISCLOSURE, "").rstrip().split("\n")
    out, replaced = [], False
    for ln in lines:
        if "댓글" in ln and re.search(r"링크|제품|상품", ln):
            if not replaced:
                out.append(LINK_LINE)
                replaced = True
            continue
        out.append(ln)
    if not replaced:
        out += ["", LINK_LINE]
    body = "\n".join(out).strip()
    tags = []
    for t in (cfg.get("topic_tags") or [])[:3] + [d.get("topic_tag"), d.get("keyword")] + ["쿠팡추천"]:
        t = re.sub(r"[^0-9A-Za-z가-힣]", "", t or "")
        if t and t not in tags:
            tags.append(t)
    tags = tags[:5]  # Instagram allows at most 5 hashtags per post
    return f"[광고] {body}\n\n{DISCLOSURE}\n\n" + " ".join("#" + t for t in tags)


def media(proj, slug, d):
    card_dir = proj / "cards" / slug
    rel = lambda f: "../" + str(f.relative_to(ROOT)).replace("\\", "/")
    imgs = sorted(card_dir.glob("card*.jpg")) if card_dir.exists() else []
    if not imgs and (card_dir / "poster.jpg").exists():
        imgs = [card_dir / "poster.jpg"]
    video = card_dir / "video.mp4"
    return [rel(f) for f in imgs], (rel(video) if video.exists() else "")


PAGE = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>인스타 올리기 묶음</title>
<style>
:root{--bg:#f6f5f1;--card:#fff;--ink:#16181d;--muted:#6b7078;--line:#e6e3dc;--accent:#d6336c}
@media (prefers-color-scheme:dark){:root{--bg:#121316;--card:#1c1e22;--ink:#f2f2f2;--muted:#a2a6ad;--line:#2b2e33}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 -apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}
main{max-width:640px;margin:0 auto;padding:18px 16px 60px}
h1{font-size:23px;margin:6px 0 4px}.sub{color:var(--muted);font-size:14px;margin:0}
.how{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 14px;margin:12px 0 18px;font-size:14px}
.how ol{margin:6px 0 0;padding-left:20px}
.post{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px;margin:0 0 18px}
.post.done{opacity:.45}
.head{display:flex;justify-content:space-between;gap:8px;align-items:center;font-size:14px;color:var(--muted);margin-bottom:8px}
.acct{font-weight:700;color:var(--ink)}
.strip{display:flex;gap:8px;overflow-x:auto;padding-bottom:6px}
.strip img,.strip video{height:200px;border-radius:10px;flex:none;background:#ddd}
.deal{font-weight:700;color:#c92a2a;margin:0 0 8px;font-size:15px}
.post.over{opacity:.5;padding:10px 14px}.post.over .head{margin:0}
.ai{display:inline-block;font-size:12.5px;background:#fff3bf;color:#5c4400;border-radius:8px;padding:3px 8px;margin:6px 0 0}
textarea{width:100%;min-height:150px;margin:10px 0 8px;border:1px solid var(--line);border-radius:10px;padding:10px;font-size:14px;line-height:1.5;font-family:inherit;background:var(--bg);color:var(--ink)}
.btns{display:flex;flex-wrap:wrap;gap:8px}
button,a.btn{flex:1 1 140px;border:0;border-radius:10px;padding:12px;font-weight:600;font-size:15px;font-family:inherit;text-align:center;text-decoration:none;cursor:pointer;background:var(--ink);color:var(--bg)}
button.alt,a.btn{background:transparent;color:var(--ink);border:1px solid var(--line)}
label.chk{display:flex;gap:8px;align-items:center;margin-top:10px;font-size:14px}
#viewer{position:fixed;inset:0;background:var(--bg);overflow-y:auto;z-index:9;padding:0 16px 40px}
#viewer[hidden]{display:none}
.vtop{position:sticky;top:0;background:var(--bg);display:flex;gap:10px;align-items:center;justify-content:space-between;padding:12px 0;font-size:14px}
.vtop .close{flex:none;padding:10px 16px}
#viewer .list img,#viewer .list video{display:block;width:100%;border-radius:10px;margin:0 0 12px}
.links{font-size:13.5px;color:var(--muted);margin-top:24px}.links a{color:inherit}
</style></head><body><main>
<h1>인스타 올리기 묶음</h1>
<p class="sub">매일 아침 골드박스 특가를 인스타용으로 만들어둬요 · 업데이트 __UPDATED__</p>
<div class="how"><b>올리는 순서</b><ol>
<li>[사진 한꺼번에 저장] → 뜨는 창에서 <b>'이미지 저장'</b>(아이폰) 또는 <b>'갤러리/사진에 저장'</b>(안드로이드). 창이 안 뜨면 사진이 크게 나오니 길게 눌러 저장</li>
<li>[글 복사]</li>
<li>인스타 + → 게시물 → 미리보기 왼쪽 아래 <b>↔ 버튼을 눌러 세로로</b> 바꾼 뒤 → '여러 장 선택'으로 저장한 사진 순서대로 선택 → 글 붙여넣기 <span style="color:#c92a2a">(세로로 안 바꾸면 위아래가 잘려요)</span></li>
<li>노란 'AI 이미지' 표시가 있으면: 고급 설정 → <b>AI 레이블 추가</b> 켜기</li>
<li>올린 뒤 [올렸어요] 체크</li>
</ol>하루 1개, 특가가 끝나기 전에 위에서부터(가장 최근 것) 올리세요.</div>
__BODY__
<div class="links">인스타 프로필 링크에 넣을 주소(한 번만):<br>__SHOPS__</div>
</main>
<div id="viewer" hidden><div class="vtop"><span>사진을 <b>길게 눌러</b> → '사진 앱에 저장'<br>위에서부터 순서대로 저장하세요</span><button class="close">닫기</button></div><div class="list"></div></div>
<script>
function key(id){return 'insta-done-'+id}
function openViewer(urls){
  var v=document.getElementById('viewer'), list=v.querySelector('.list'); list.innerHTML='';
  urls.forEach(function(u){var el=document.createElement(u.endsWith('.mp4')?'video':'img');el.src=u;
    if(el.tagName==='VIDEO'){el.controls=true;el.playsInline=true}list.appendChild(el)});
  v.hidden=false; window.scrollTo(0,0);
}
document.addEventListener('click',function(e){if(e.target.closest('.close'))document.getElementById('viewer').hidden=true});
document.querySelectorAll('.post:not(.over)').forEach(function(p){
  var id=p.dataset.id, box=p.querySelector('input[type=checkbox]');
  try{ if(localStorage.getItem(key(id))){box.checked=true;p.classList.add('done')} }catch(e){}
  box.addEventListener('change',function(){p.classList.toggle('done',box.checked);
    try{ box.checked?localStorage.setItem(key(id),'1'):localStorage.removeItem(key(id)) }catch(e){} });
  p.querySelector('.copy').addEventListener('click',function(ev){
    var t=p.querySelector('textarea'); var b=ev.currentTarget;
    function ok(){b.textContent='복사됐어요 ✓';setTimeout(function(){b.textContent='글 복사'},1800)}
    if(navigator.clipboard){navigator.clipboard.writeText(t.value).then(ok,function(){t.select();document.execCommand('copy');ok()})}
    else{t.select();document.execCommand('copy');ok()}
  });
  // Fetch the photos as soon as the page opens: phones only open the save sheet when it is
  // called right away from the tap, not after a download finishes.
  var urls=JSON.parse(p.dataset.files), files=null, saveBtn=p.querySelector('.save'), orig=saveBtn.textContent;
  Promise.all(urls.map(function(u,i){return fetch(u).then(function(r){return r.blob()}).then(function(bl){
    var mp4=u.endsWith('.mp4');
    return new File([bl],id+'_'+(i+1)+(mp4?'.mp4':'.jpg'),{type:bl.type||(mp4?'video/mp4':'image/jpeg')});})}))
    .then(function(fs){files=fs}).catch(function(){files=[]});
  saveBtn.addEventListener('click',function(){
    if(files===null){saveBtn.textContent='사진 받는 중… 잠깐 뒤 다시 눌러주세요';setTimeout(function(){saveBtn.textContent=orig},2000);return}
    if(files.length&&navigator.canShare&&navigator.canShare({files:files})){
      navigator.share({files:files}).catch(function(e){if(e.name!=='AbortError')openViewer(urls)});
    }else{openViewer(urls)}
  });
  p.querySelectorAll('.strip img').forEach(function(im){im.addEventListener('click',function(){openViewer(urls)})});
});
</script></body></html>"""


def build():
    cutoff = dt.datetime.now(KST) - dt.timedelta(days=7)
    rows, shops = [], []
    for proj in sorted((ROOT / "projects").iterdir()):
        if not (proj / "config.json").exists():
            continue
        cfg = json.loads((proj / "config.json").read_text())
        if cfg.get("channel") != "instagram_manual":
            continue
        shops.append(f'{html.escape(cfg.get("label", proj.name))}: <a href="{SHOP.format(proj.name)}">{SHOP.format(proj.name)}</a>')
        for f in (proj / "done").glob("*.json"):
            d = json.loads(f.read_text())
            if d.get("reply_to_media_id") or not d.get("published_at") or not (d.get("result") or {}).get("manual"):
                continue
            t = dt.datetime.strptime(d["published_at"], "%Y-%m-%dT%H:%M:%S%z").astimezone(KST)
            if t < cutoff:
                continue
            imgs, video = media(proj, f.stem, d)
            if not imgs and not video:
                continue
            rows.append((t, cfg, cfg.get("label", proj.name), f.stem, d, imgs, video))
    rows.sort(key=lambda r: r[0], reverse=True)
    parts = []
    now = dt.datetime.now(KST)
    for t, cfg, label, slug, d, imgs, video in rows:
        end = d.get("deal_until") and dt.datetime.fromisoformat(d["deal_until"])
        if end and end < now:
            parts.append(f'<section class="post over"><div class="head"><span><span class="acct">{html.escape(label)}</span> · '
                         f'{t.strftime("%m/%d %H:%M")}</span><span>특가 끝남 · 올리지 마세요</span></div></section>')
            continue
        deal = (f'<div class="deal">⏰ 특가 {html.escape(d.get("deal_label", ""))} · 그 전에 올려야 해요</div>' if end else "")
        # a video post goes up as a Reel (video only); a card post as a carousel (images)
        files = [video] if video else imgs
        strip = "".join(f'<video src="{html.escape(video)}" controls muted playsinline preload="metadata"></video>' if video else "" for _ in [0])
        strip += "".join(f'<img src="{html.escape(u)}" alt="" loading="lazy">' for u in ([] if video else imgs))
        kind = "릴스(영상)" if video else f"사진 {len(imgs)}장"
        ai = '<div class="ai">AI 이미지 포함 → AI 레이블 켜기</div>' if d.get("format") in ("scene_story", "deal_story") else ""
        parts.append(
            f'<section class="post" data-id="{slug}" data-files=\'{html.escape(json.dumps(files))}\'>'
            f'<div class="head"><span><span class="acct">{html.escape(label)}</span> · {t.strftime("%m/%d %H:%M")}</span><span>{kind}</span></div>'
            f'{deal}<div class="strip">{strip}</div>{ai}'
            f'<textarea readonly>{html.escape(caption(d, cfg))}</textarea>'
            f'<div class="btns"><button class="save">{"영상 저장" if video else "사진 한꺼번에 저장"}</button><button class="copy alt">글 복사</button></div>'
            f'<label class="chk"><input type="checkbox"> 올렸어요</label></section>')
    if not parts:
        parts.append('<p class="sub">아직 만든 묶음이 없어요. 매일 아침 8시쯤 새 묶음이 생겨요.</p>')
    out = (PAGE.replace("__BODY__", "\n".join(parts)).replace("__SHOPS__", "<br>".join(shops))
           .replace("__UPDATED__", (rows[0][0] if rows else dt.datetime.now(KST)).strftime("%m/%d %H:%M")))
    dest = ROOT / "insta" / "index.html"
    dest.parent.mkdir(exist_ok=True)
    if not dest.exists() or dest.read_text() != out:
        dest.write_text(out)
    return len(rows)


if __name__ == "__main__":
    print("insta/index.html", build(), "posts")
