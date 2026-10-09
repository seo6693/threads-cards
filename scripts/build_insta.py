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
BASE_TAGS = {
    "nutri": ["영양제", "영양제추천", "건강기능식품"],
    "fresh": ["로켓프레시", "냉동식품", "간편식"],
}
LINK_LINE = "👉 상품 링크는 프로필 링크 '상품 모음'에 모아뒀어요"


def caption(d, project):
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
    for t in [d.get("topic_tag"), d.get("keyword")] + BASE_TAGS.get(project, []) + ["쿠팡추천"]:
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
.ai{display:inline-block;font-size:12.5px;background:#fff3bf;color:#5c4400;border-radius:8px;padding:3px 8px;margin:6px 0 0}
textarea{width:100%;min-height:150px;margin:10px 0 8px;border:1px solid var(--line);border-radius:10px;padding:10px;font-size:14px;line-height:1.5;font-family:inherit;background:var(--bg);color:var(--ink)}
.btns{display:flex;flex-wrap:wrap;gap:8px}
button,a.btn{flex:1 1 140px;border:0;border-radius:10px;padding:12px;font-weight:600;font-size:15px;font-family:inherit;text-align:center;text-decoration:none;cursor:pointer;background:var(--ink);color:var(--bg)}
button.alt,a.btn{background:transparent;color:var(--ink);border:1px solid var(--line)}
label.chk{display:flex;gap:8px;align-items:center;margin-top:10px;font-size:14px}
.links{font-size:13.5px;color:var(--muted);margin-top:24px}.links a{color:inherit}
</style></head><body><main>
<h1>인스타 올리기 묶음</h1>
<p class="sub">최근 7일 쓰레드 게시물을 인스타용으로 바꿔뒀어요 · 업데이트 __UPDATED__</p>
<div class="how"><b>올리는 순서</b><ol>
<li>[사진 한꺼번에 저장] → 사진 앱에 저장</li>
<li>[글 복사]</li>
<li>인스타 + → 게시물 → 저장한 사진 순서대로 선택 → 글 붙여넣기</li>
<li>노란 'AI 이미지' 표시가 있으면: 고급 설정 → <b>AI 레이블 추가</b> 켜기</li>
<li>올린 뒤 [올렸어요] 체크</li>
</ol>하루 1개면 충분해요. 위에서부터(가장 최근 것) 올리세요.</div>
__BODY__
<div class="links">인스타 프로필 링크(최대 5개)에 넣을 주소:<br>__SHOPS__</div>
</main>
<script>
function key(id){return 'insta-done-'+id}
document.querySelectorAll('.post').forEach(function(p){
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
  p.querySelector('.save').addEventListener('click',async function(ev){
    var b=ev.currentTarget, orig=b.textContent, urls=JSON.parse(p.dataset.files); b.textContent='준비 중…';
    try{
      var files=await Promise.all(urls.map(async function(u,i){
        var r=await fetch(u); var bl=await r.blob();
        return new File([bl],id+'_'+(i+1)+(u.endsWith('.mp4')?'.mp4':'.jpg'),{type:bl.type});}));
      if(navigator.canShare&&navigator.canShare({files:files})){await navigator.share({files:files})}
      else{files.forEach(function(f){var a=document.createElement('a');a.href=URL.createObjectURL(f);a.download=f.name;document.body.appendChild(a);a.click();a.remove()})}
    }catch(e){ if(e.name!=='AbortError') alert('저장이 안 되면 사진을 길게 눌러 저장하세요') }
    b.textContent=orig;
  });
});
</script></body></html>"""


def build():
    cutoff = dt.datetime.now(KST) - dt.timedelta(days=7)
    rows, shops = [], []
    for proj in sorted((ROOT / "projects").iterdir()):
        if not (proj / "config.json").exists():
            continue
        cfg = json.loads((proj / "config.json").read_text())
        shops.append(f'{html.escape(cfg.get("label", proj.name))}: <a href="{SHOP.format(proj.name)}">{SHOP.format(proj.name)}</a>')
        for f in (proj / "done").glob("*.json"):
            d = json.loads(f.read_text())
            if d.get("reply_to_media_id") or not d.get("published_at") or not (d.get("result") or {}).get("media_id"):
                continue
            t = dt.datetime.strptime(d["published_at"], "%Y-%m-%dT%H:%M:%S%z").astimezone(KST)
            if t < cutoff:
                continue
            imgs, video = media(proj, f.stem, d)
            if not imgs and not video:
                continue
            rows.append((t, proj.name, cfg.get("label", proj.name), f.stem, d, imgs, video))
    rows.sort(key=lambda r: r[0], reverse=True)
    parts = []
    for t, pname, label, slug, d, imgs, video in rows:
        # a video post goes up as a Reel (video only); a card post as a carousel (images)
        files = [video] if video else imgs
        strip = "".join(f'<video src="{html.escape(video)}" controls muted playsinline preload="metadata"></video>' if video else "" for _ in [0])
        strip += "".join(f'<img src="{html.escape(u)}" alt="" loading="lazy">' for u in ([] if video else imgs))
        kind = "릴스(영상)" if video else f"사진 {len(imgs)}장"
        ai = '<div class="ai">AI 이미지 포함 → AI 레이블 켜기</div>' if d.get("format") == "scene_story" else ""
        parts.append(
            f'<section class="post" data-id="{slug}" data-files=\'{html.escape(json.dumps(files))}\'>'
            f'<div class="head"><span><span class="acct">{html.escape(label)}</span> · {t.strftime("%m/%d %H:%M")}</span><span>{kind}</span></div>'
            f'<div class="strip">{strip}</div>{ai}'
            f'<textarea readonly>{html.escape(caption(d, pname))}</textarea>'
            f'<div class="btns"><button class="save">{"영상 저장" if video else "사진 한꺼번에 저장"}</button><button class="copy alt">글 복사</button></div>'
            f'<label class="chk"><input type="checkbox"> 올렸어요</label></section>')
    if not parts:
        parts.append('<p class="sub">최근 7일 게시물이 아직 없어요.</p>')
    out = (PAGE.replace("__BODY__", "\n".join(parts)).replace("__SHOPS__", "<br>".join(shops))
           .replace("__UPDATED__", (rows[0][0] if rows else dt.datetime.now(KST)).strftime("%m/%d %H:%M")))
    dest = ROOT / "insta" / "index.html"
    dest.parent.mkdir(exist_ok=True)
    if not dest.exists() or dest.read_text() != out:
        dest.write_text(out)
    return len(rows)


if __name__ == "__main__":
    print("insta/index.html", build(), "posts")
