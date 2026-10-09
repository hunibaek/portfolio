#!/usr/bin/env python3
"""Static portfolio builder: content/ (images + text files) -> docs/ (plain HTML).

Layout: left = index list, center = images/videos, right = text column.
Bottom of every page: archive grid of all works.
Only dependency: Pillow  (pip install pillow)
"""
import datetime, html, json
import re
import shutil
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
OUT = ROOT / "docs"
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}
SIZES = (800, 1600, 2400)   # 800: grid + phone, 1600: normal screens, 2400: retina screens (browser picks via srcset)
QUALITY = 86                 # JPEG quality; 4:4:4 chroma (no colour smearing)
THUMB_MAX = 800
PDF_LANGS = [("en", "English"), ("de", "Deutsch"), ("ko", "한국어")]
# filter above the work list. info.txt: "category: performance, installation" (one or more, comma separated)
CATEGORIES = [("performance", "Performance"), ("installation", "Installation"), ("wall", "Wall works"), ("video", "Video")]


def cat_keys(value):
    out = []
    for c in value.split(","):
        c = c.strip().lower().replace(" ", "")
        c = {"wallworks": "wall", "wallwork": "wall", "2dworks": "wall", "2dwork": "wall", "2d": "wall", "performances": "performance", "installations": "installation", "videos": "video"}.get(c, c)
        if c and c not in out:
            out.append(c)
    return out


# ---------- text helpers ----------
def parse_txt(path):
    """'key: value' header lines, a line with only '---', then free text.
    A file without '---' is treated as free text only."""
    if not path.exists():
        return {}, "", []
    lines = path.read_text(encoding="utf-8").splitlines()
    stripped = [l.strip() for l in lines]
    meta, multi, body = {}, [], lines
    if "---" in stripped:
        i = stripped.index("---")
        head, body = lines[:i], lines[i + 1:]
        for l in head:
            if ":" in l:
                k, v = l.split(":", 1)
                k, v = k.strip().lower(), v.strip()
                multi.append((k, v))
                meta[k] = v
    return meta, "\n".join(body).strip(), multi


def inline(s):
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+|mailto:[^)\s]+)\)",
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    s = re.sub(r'(?<![="\w>])(https?://[^\s<]+)', r'<a href="\1" target="_blank" rel="noopener">\1</a>', s)
    s = re.sub(r'(?<![:\w/"])([\w.+-]+@[\w-]+\.[\w.-]+\w)', r'<a href="mailto:\1">\1</a>', s)
    return s


def para(body):
    """Blank line = new paragraph. '# Heading' line = section heading."""
    out = []
    for block in re.split(r"\n\s*\n", body):
        lines = [l for l in block.strip().splitlines()]
        if not lines:
            continue
        buf = []
        for l in lines:
            if l.startswith("# "):
                if buf:
                    out.append("<p>" + "<br>".join(inline(x) for x in buf) + "</p>")
                    buf = []
                out.append(f"<h2>{inline(l[2:].strip())}</h2>")
            else:
                buf.append(l)
        if buf:
            out.append("<p>" + "<br>".join(inline(x) for x in buf) + "</p>")
    return "\n".join(out)


def slugify(name):
    return re.sub(r"[^\w-]+", "-", name.strip().lower()).strip("-") or "work"


def embed(url):
    m = re.search(r"vimeo\.com/(?:video/)?(\d+)", url)
    if m:
        src = f"https://player.vimeo.com/video/{m.group(1)}"
    else:
        m = re.search(r"(?:youtu\.be/|[?&]v=|/embed/|/shorts/|/live/)([\w-]{11})", url)
        if not m:
            print(f"  ! video link not recognised: {url}")
            return ""
        src = f"https://www.youtube-nocookie.com/embed/{m.group(1)}?rel=0"
    return (f'<div class="video"><iframe src="{src}" loading="lazy" title="video" '
            f'allow="fullscreen; picture-in-picture" allowfullscreen></iframe></div>')


# ---------- images ----------
def resize(src, dst, longest):
    """Write one JPEG no larger than `longest` px (never upscaled). Returns its pixel width."""
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((longest, longest), Image.LANCZOS)
        dst.parent.mkdir(parents=True, exist_ok=True)
        im.save(dst, "JPEG", quality=QUALITY, optimize=True, progressive=True, subsampling=0)
        return im.width


def variants(src, odir, stem):
    """800 / 1600 / 2400 px copies + the untouched original (opened when a photo is clicked).
    Returns (srcset, default_src, big_src, original_src)."""
    got, seen = [], set()
    for sz in SIZES:
        w = resize(src, odir / f"{stem}-{sz}.jpg", sz)
        if w in seen:                       # source smaller than this size: same pixels, drop duplicate
            (odir / f"{stem}-{sz}.jpg").unlink()
            continue
        seen.add(w); got.append((f"{stem}-{sz}.jpg", w))
    (odir / "orig").mkdir(exist_ok=True)
    shutil.copy2(src, odir / "orig" / src.name)
    mid = next((f for f, w in got if f.endswith("-1600.jpg")), got[-1][0])
    return ", ".join(f"{f} {w}w" for f, w in got), mid, got[-1][0], f"orig/{src.name}"


# ---------- page shell ----------
# Values measured on nonotak.com (Cargo site), Oct 2026:
#   type: system sans-serif (Helvetica on Mac, Arial on Windows), 400, no letter-spacing
#   menu 11px / 19.8px · body & captions 11px / 17.6px · thumbnail titles 12px / 18px
#   colours: text #9E9E9E · top menu #999 · work list #767676 · current item #333 on white
#   media column 910px (photos 3:2, videos ~16:9), thumbnails 200x134 (3:2), gap 35px
CSS = """
:root{
 --bg:#000; --text:#9e9e9e; --menu:#999; --list:#767676; --hover:#fff;
 --cur-bg:#fff; --cur-fg:#333; --line:#2a2a2a;
 --font:"Helvetica Neue",Helvetica,Arial,"Apple SD Gothic Neo","Noto Sans KR","Malgun Gothic",sans-serif;
 --size:11px; --menu-lh:1.8; --text-lh:1.6; --thumb-size:12px;
 --media:910px; --gap:20px;
}
*{box-sizing:border-box}
html{background:var(--bg)}
body{margin:0;background:var(--bg);color:var(--text);font:400 var(--size)/var(--text-lh) var(--font);
 -webkit-font-smoothing:antialiased;-webkit-text-size-adjust:100%;
 word-break:keep-all;overflow-wrap:break-word}
a{color:inherit;transition:color .15s}
a:hover{color:var(--hover)}
.wrap{display:grid;grid-template-columns:215px minmax(0,var(--media)) 360px;column-gap:35px;
 padding:40px 35px 90px}
nav{position:sticky;top:40px;align-self:start;max-height:calc(100vh - 60px);overflow-y:auto;
 scrollbar-width:none;line-height:var(--menu-lh)}
nav::-webkit-scrollbar{display:none}
nav ul{list-style:none;margin:0;padding:0}
nav a{text-decoration:none;text-transform:uppercase;color:var(--menu)}
nav .links a{text-decoration:underline}
nav .works a{color:var(--list)}
.copy{margin:34px 0 0;font-size:10px;color:#555;line-height:1.5}
nav .about{margin-top:4px}
.filter{white-space:nowrap;margin:10px 0;line-height:var(--menu-lh);text-transform:uppercase;color:#444}
.filter a{text-decoration:none;color:var(--list);cursor:pointer}
.filter a:hover,.filter a.on{color:#fff}
.foot{margin:34px 0 0;font-size:10px;color:#555;line-height:1.7}
.foot a{text-decoration:none;text-transform:uppercase;color:var(--menu)}
html[data-f="performance"] [data-cat]:not([data-cat~="performance"]),
html[data-f="installation"] [data-cat]:not([data-cat~="installation"]),
html[data-f="wall"] [data-cat]:not([data-cat~="wall"]),
html[data-f="video"] [data-cat]:not([data-cat~="video"]){display:none}
nav .works a::before{content:"_"}
nav a.cur,nav .works a.cur{background:var(--cur-bg);color:var(--cur-fg);padding:1px 4px;margin-left:-4px}
main{min-width:0}
main img{display:block;width:100%;height:auto;margin:0 0 var(--gap);background:#080808}
.video{position:relative;aspect-ratio:16/9;margin:0 0 var(--gap);background:#080808}
.video iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px 20px}
.grid a{text-decoration:none;display:block}
.grid .th{aspect-ratio:3/2;overflow:hidden;background:#080808}
.grid img{height:100%;object-fit:cover;margin:0;transition:opacity .2s}
.grid a:hover img{opacity:.6}
.grid span{display:block;margin-top:6px;font-size:var(--thumb-size);line-height:1.5;
 text-transform:uppercase;text-align:center}
.archive{margin-top:70px}
aside{position:sticky;top:40px;align-self:start;max-height:calc(100vh - 60px);overflow-y:auto;
 overscroll-behavior:contain;padding-right:12px;scrollbar-width:thin;scrollbar-color:#333 transparent}
aside::-webkit-scrollbar{width:4px}
aside::-webkit-scrollbar-thumb{background:#333;border-radius:2px}
aside .head{margin:0 0 1.6em}
aside .head em{font-style:italic}
aside p,.text p{margin:0 0 1.1em}
aside h2,.text h2{font-size:var(--size);font-weight:400;text-transform:uppercase;color:#fff;
 margin:2.2em 0 .5em}
aside h2:first-child,.text h2:first-child{margin-top:0}
.text{max-width:640px}
.pdf{margin-top:2em}
.pdf h2{margin-top:0}
.pdf a{display:inline-block;margin-right:14px}
@media(max-width:1300px){.wrap{grid-template-columns:215px minmax(0,1fr) 300px;column-gap:30px}
 .grid{grid-template-columns:repeat(3,1fr)}}
/* phone-only pieces: hidden on tablets/desktops */
#mbar,#menu,#cbar,#dots,#sheet{display:none}
html.lock{overflow:hidden}
/* ---------- PHONE LAYOUT (<= 860px) ----------
   Home / About : slim top bar (name + Menu), 2-column thumbnails, text below.
   Work page    : photos fill the screen and swipe left/right; description opens from an "Info" button. */
@media(max-width:860px){
 :root{--size:12px}
 #mbar{position:fixed;top:0;left:0;right:0;height:44px;z-index:50;background:#000;display:flex;
  justify-content:space-between;align-items:center;padding:0 14px;border-bottom:1px solid #1c1c1c;
  text-transform:uppercase;font-size:12px}
 #mbar a{text-decoration:none;color:var(--menu)}
 #mbar button{background:none;border:0;color:var(--menu);font:inherit;text-transform:uppercase;
  padding:14px 0 14px 18px;cursor:pointer}
 #menu.on{display:block;position:fixed;inset:44px 0 0 0;z-index:49;background:#000;
  padding:22px 16px 48px;overflow:auto;overscroll-behavior:contain}
 #menu ul{list-style:none;margin:0 0 20px;padding:0;line-height:2.3;font-size:14px}
 #menu a{text-decoration:none;text-transform:uppercase;color:var(--menu)}
 #menu .links a{text-decoration:underline}
 #menu .works a{color:var(--list)}
 #menu .works a::before{content:"_"}
 #menu a.cur{background:#fff;color:var(--cur-fg);padding:2px 5px;margin-left:-5px}
 #menu .filter{font-size:14px;line-height:2.3;margin:16px 0}
 #menu .foot{font-size:12px}
 .wrap{display:block;padding:52px 0 44px}
 nav{display:none}
 aside{position:static;max-height:none;overflow:visible;padding:28px 14px 0}
 .grid{grid-template-columns:repeat(2,1fr);gap:14px 6px;padding:0 6px}
 .grid span{text-align:center;font-size:10px;margin-top:4px}
 .archive{display:none}
 .archive.all{display:grid;margin-top:46px}
 .text{padding:0 14px;margin-top:6px}
 main>img{margin-bottom:12px}
 /* work page: photos scroll down; bar + Info sheet stay fixed at the bottom; archive grid after the last photo */
 body.work .wrap{padding:44px 0 62px}
 body.work aside{display:none}
 body.work main>img{display:block;width:100%;height:auto;margin:0 0 6px;cursor:default}
 body.work main>.video{margin:0 0 6px}
 body.work .archive{display:grid;margin-top:46px}
 body.work #cbar{display:flex;position:fixed;bottom:0;left:0;right:0;height:62px;z-index:55;background:#000;
  border-top:1px solid #1c1c1c;align-items:center;justify-content:space-between;padding:0 14px;
  font-size:12px;color:var(--text)}
 #cbar span{min-width:0;margin-right:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
 #cbar em{color:#fff;font-style:italic}
 #cbar button{background:none;border:1px solid #444;color:#ddd;font:inherit;text-transform:uppercase;
  padding:9px 14px;border-radius:2px;white-space:nowrap;cursor:pointer}
 body.work #sheet.on{display:block;position:fixed;left:0;right:0;bottom:62px;max-height:56%;
  background:#0b0b0b;border-top:1px solid #2a2a2a;padding:20px 16px 24px;overflow:auto;z-index:54;
  line-height:1.7;overscroll-behavior:contain}
 #sheet p{margin:0 0 1em}
 #sheet .head{margin:0 0 1.2em}
 #sheet h2{margin:1.8em 0 .5em}}
main>img{cursor:zoom-in}
#lb{position:fixed;inset:0;z-index:100;background:#000;display:none;align-items:center;
 justify-content:center;user-select:none;-webkit-user-select:none;touch-action:pan-y}
#lb.on{display:flex}
#lb img{max-width:calc(100vw - 80px);max-height:calc(100vh - 80px);object-fit:contain;display:block}
#lb .zone{position:absolute;top:0;bottom:0;width:50%}
#lb .prev{left:0;cursor:w-resize}
#lb .next{right:0;cursor:e-resize}
#lb .bar{position:absolute;left:0;right:0;top:0;display:flex;justify-content:space-between;
 padding:14px 20px;font-size:var(--size);color:var(--text);pointer-events:none}
#lb .close{pointer-events:auto;cursor:pointer;background:none;border:0;color:var(--text);
 font:inherit;text-transform:uppercase;padding:0}
#lb .close:hover{color:#fff}
@media(max-width:860px){#lb img{max-width:100vw;max-height:calc(100vh - 60px)}}
"""

# Fullscreen viewer for the photos of a page (not the archive thumbnails).
# Click right half / right arrow key / right-click = next · left half / left arrow = previous
# Esc or "Close" = exit · swipe left/right on phones.
LIGHTBOX = """<div id="lb" aria-hidden="true"><img alt="">
<div class="zone prev" title="Previous"></div><div class="zone next" title="Next"></div>
<div class="bar"><span class="count"></span><button class="close" type="button">Close ×</button></div></div>
<script>
(function(){            /* category filter: All / Performance / Installation / 2D works */
  var root=document.documentElement,f='all';
  try{f=localStorage.getItem('workfilter')||'all';}catch(e){}
  function set(v){
    if(!document.querySelector('.filter a[data-f="'+v+'"]'))v='all';
    if(v==='all')root.removeAttribute('data-f');else root.setAttribute('data-f',v);
    [].forEach.call(document.querySelectorAll('.filter a'),function(a){a.classList.toggle('on',a.dataset.f===v);});
    try{localStorage.setItem('workfilter',v);}catch(e){}
  }
  [].forEach.call(document.querySelectorAll('.filter a'),function(a){
    a.addEventListener('click',function(e){set(a.dataset.f);
      if(a.parentNode.dataset.home){e.preventDefault();      /* home: close the phone menu, show the grid */
        var m=document.getElementById('menu'),b=document.getElementById('mbtn');
        if(m&&m.classList.contains('on')){m.classList.remove('on');if(b)b.textContent='Menu';
          root.classList.remove('lock');window.scrollTo(0,0);}}});});   /* other pages: go to the home grid */
  set(f);
  [].forEach.call(document.querySelectorAll('a.home'),function(a){      /* name = whole archive */
    a.addEventListener('click',function(){try{localStorage.setItem('workfilter','all');}catch(e){} set('all');});});
})();
(function(){            /* phone: Menu button, Info sheet */
  var menu=document.getElementById('menu'),mb=document.getElementById('mbtn');
  if(mb)mb.addEventListener('click',function(){
    var on=menu.classList.toggle('on');mb.textContent=on?'Close':'Menu';
    document.documentElement.classList.toggle('lock',on);});
  var sheet=document.getElementById('sheet'),ib=document.getElementById('ibtn'),main=document.querySelector('main');
  function info(on){sheet.classList.toggle('on',on);ib.textContent=on?'Info –':'Info +';}
  if(ib){ib.addEventListener('click',function(){info(!sheet.classList.contains('on'));});
    main.addEventListener('click',function(){if(sheet.classList.contains('on'))info(false);});}
})();
(function(){            /* desktop: fullscreen viewer */
  var phone=window.matchMedia('(max-width:860px)');
  var pics=[].slice.call(document.querySelectorAll('main>img'));
  if(!pics.length)return;
  var lb=document.getElementById('lb'),big=lb.querySelector('img'),count=lb.querySelector('.count'),i=0,sx=null;
  function show(n){i=(n+pics.length)%pics.length;var p=pics[i],k=i;big.src=p.dataset.big?new URL(p.dataset.big,p.src).href:(p.currentSrc||p.src);
    if(p.dataset.full){var o=new Image();o.onload=function(){if(k===i)big.src=o.src;};o.src=new URL(p.dataset.full,p.src).href;}
    count.textContent=(i+1)+' / '+pics.length;
    }
  function open(n){show(n);lb.classList.add('on');lb.setAttribute('aria-hidden','false');
    document.documentElement.style.overflow='hidden';}
  function close(){lb.classList.remove('on');lb.setAttribute('aria-hidden','true');
    document.documentElement.style.overflow='';}
  pics.forEach(function(p,n){p.addEventListener('click',function(){if(!phone.matches)open(n);});});
  lb.querySelector('.next').addEventListener('click',function(){show(i+1);});
  lb.querySelector('.prev').addEventListener('click',function(){show(i-1);});
  lb.querySelector('.close').addEventListener('click',close);
  lb.addEventListener('contextmenu',function(e){e.preventDefault();show(i+1);});
  document.addEventListener('keydown',function(e){
    if(!lb.classList.contains('on'))return;
    if(e.key==='ArrowRight'||e.key===' '){e.preventDefault();show(i+1);}
    else if(e.key==='ArrowLeft'){e.preventDefault();show(i-1);}
    else if(e.key==='Escape'){close();}
  });
  lb.addEventListener('touchstart',function(e){sx=e.touches[0].clientX;},{passive:true});
  lb.addEventListener('touchend',function(e){if(sx===null)return;var dx=e.changedTouches[0].clientX-sx;
    if(Math.abs(dx)>40){e.preventDefault();show(dx<0?i+1:i-1);}sx=null;});
})();
</script>"""


SHARE = {"url": "", "desc": "", "img": False, "name": "", "icon": False}
ANALYTICS = {"goatcounter": ""}   # site.txt "goatcounter: CODE" -> visitor statistics (no cookies)
PAGES = []   # every page path, for sitemap.xml (Google search)


def head_extra(title, base, path="", desc="", jsonld=""):
    """Description, canonical URL, link-preview (Open Graph), favicon and Google (JSON-LD) tags."""
    if not SHARE["url"]:
        return ""
    PAGES.append(path)
    t, d = html.escape(title, quote=True), html.escape(desc or SHARE["desc"], quote=True)
    out = [f'<meta name="description" content="{d}">',
           f'<link rel="canonical" href="{SHARE["url"]}/{path}">',
           f'<meta property="og:site_name" content="{html.escape(SHARE["name"], quote=True)}">',
           f'<meta property="og:type" content="website"><meta property="og:title" content="{t}">',
           f'<meta property="og:description" content="{d}">',
           f'<meta property="og:url" content="{SHARE["url"]}/{path}">']
    if jsonld:
        out.append(f'<script type="application/ld+json">{jsonld}</script>')
    if SHARE["img"]:
        out += [f'<meta property="og:image" content="{SHARE["url"]}/share.jpg">',
                '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">',
                '<meta name="twitter:card" content="summary_large_image">']
    if SHARE["icon"]:   # small picture next to the site name in Google results and browser tabs
        out += [f'<link rel="icon" href="{base}favicon.ico" sizes="48x48">',
                f'<link rel="icon" type="image/png" sizes="192x192" href="{base}favicon.png">',
                f'<link rel="apple-touch-icon" href="{base}apple-touch-icon.png">']
    return "\n".join(out)


def analytics():
    code = ANALYTICS["goatcounter"]
    if not code:
        return ""
    return (f'<script data-goatcounter="https://{html.escape(code)}.goatcounter.com/count" '
            'async src="//gc.zgo.at/count.js"></script>')


def page(title, nav_html, main_html, aside_html, base="", name="", work_head="", lang="en", path="", desc="", jsonld=""):
    """work_head (work pages only) = title line for the phone's bottom bar; it also switches on the swipe layout."""
    bar = (f'<header id="mbar"><a href="{base}index.html" class="home">{html.escape(name)}</a>'
           f'<button type="button" id="mbtn">Menu</button></header><div id="menu">{nav_html}</div>')
    work = ""
    if work_head:
        work = (f'<div id="cbar"><span>{work_head}</span><button type="button" id="ibtn">Info +</button></div>'
                f'<div id="sheet">{aside_html}</div>')
    cls = ' class="work"' if work_head else ""
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
{head_extra(title, base, path, desc, jsonld)}
<style>{CSS}</style>{analytics()}</head>
<body{cls}>{bar}<div class="wrap">
<nav>{nav_html}</nav>
<main>{main_html}</main>
<aside>{aside_html}</aside>
</div>{work}{LIGHTBOX}</body></html>"""


def build_nav(base, site, works, current):
    """Left column: name / About-Contact / filter / works A-Z / Instagram-YouTube / ©"""
    def a(href, label, key, cls_li=""):
        cls = ' class="cur"' if key == current else ""
        li = f' class="{cls_li}"' if cls_li else ""
        return f'<li{li}><a href="{base}{href}"{cls}>{html.escape(label)}</a></li>'

    top = (f'<li><a href="{base}index.html" class="home" data-f="all">{html.escape(site["name"])}</a></li>'
           + a("about/index.html", "About / Contact", "_about", "about"))
    used = {c for w in works for c in w["cats"]}
    opts = [("all", "All")] + [(k, l) for k, l in CATEGORIES if k in used]
    sl = ' <span class="sl">/</span> '
    home = ' data-home="1"' if current == "_portfolio" else ""
    filt = ""
    for i, (k, l) in enumerate(opts):                 # second line starts after "Performance /"
        filt += f'<a href="{base}index.html" data-f="{k}">{html.escape(l).replace(" ", "&nbsp;")}</a>'
        if i < len(opts) - 1:
            filt += ' <span class="sl">/</span><br>' if k == "performance" else sl
    items = "".join(                                   # left list: A-Z (the home grid stays newest-first)
        f'<li data-cat="{" ".join(w["cats"])}">'
        + a(f"works/{w['slug']}/index.html", w["title"], w["slug"])[4:]
        for w in sorted(works, key=lambda w: w["title"].casefold()))
    links = sl.join(
        f'<a href="{html.escape(u)}" target="_blank" rel="noopener">{html.escape(l)}</a>'
        for l, u in site["links"])
    return (f'<ul>{top}</ul><p class="filter"{home}>{filt}</p>'
            f'<ul class="works">{items}</ul>'
            f'<p class="foot">{links}<br>{html.escape(site["copyright"])}</p>')


# ---------- main ----------
def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    smeta, _, smulti = parse_txt(CONTENT / "site.txt")
    ANALYTICS["goatcounter"] = re.sub(r"[^a-z0-9-]", "", smeta.get("goatcounter", "").lower())
    site = {
        "name": smeta.get("name", "Artist Name"),
        "copyright": smeta.get("copyright") or f"© {datetime.date.today().year} {smeta.get('name', 'Artist Name')}",
        "links": [tuple(p.strip() for p in v.split("|", 1))
                  for k, v in smulti if k == "link" and "|" in v],
    }

    # ---- link preview / description / favicon (content/share.jpg = the picture shown when the link is shared)
    SHARE["url"] = (smeta.get("url") or "https://seunghoonbaek.com").rstrip("/")
    SHARE["name"] = site["name"]
    name_ko = smeta.get("name_ko", "")
    home_title = smeta.get("title") or " ".join(x for x in (site["name"], name_ko) if x) + " — Artist"
    person = {   # tells Google which "Seunghoon Baek" this site is about
        "@context": "https://schema.org", "@type": "Person",
        "name": site["name"], "url": SHARE["url"] + "/",
        "jobTitle": smeta.get("job", "Visual artist"),
        "sameAs": [u for _, u in site["links"] if "playlist" not in u],
    }
    if name_ko:
        person["alternateName"] = name_ko
    if smeta.get("born"):
        person["birthDate"] = smeta["born"]
    if smeta.get("based"):
        person["homeLocation"] = smeta["based"]
    if smeta.get("email"):
        person["email"] = "mailto:" + smeta["email"]
    person_ld = json.dumps(person, ensure_ascii=False).replace("</", "<\\/")
    _, hb0, _ = parse_txt(CONTENT / "home.txt")
    first = next((p.strip() for p in re.split(r"\n\s*\n", hb0) if p.strip() and not p.strip().startswith("(")), "")
    SHARE["desc"] = smeta.get("description") or (first[:200] if first else f'{site["name"]} — portfolio')
    share_src = next((CONTENT / n for n in ("share.jpg", "share.jpeg", "share.png") if (CONTENT / n).exists()), None)
    if share_src:
        im = ImageOps.exif_transpose(Image.open(share_src)).convert("RGB")
        og = ImageOps.fit(im, (1200, 630), Image.LANCZOS, centering=(0.5, 0.5))
        og.save(OUT / "share.jpg", quality=88, optimize=True, progressive=True)
        SHARE["img"] = True
    else:
        print("  ! no content/share.jpg — link previews will have no picture")
    # site icon: content/favicon.png (square picture); falls back to share.jpg
    icon_src = next((CONTENT / n for n in ("favicon.png", "favicon.jpg", "favicon.jpeg") if (CONTENT / n).exists()), share_src)
    if icon_src:
        ic = ImageOps.exif_transpose(Image.open(icon_src)).convert("RGBA")
        sq = lambda n: ImageOps.fit(ic, (n, n), Image.LANCZOS, centering=(0.5, 0.5))
        sq(192).save(OUT / "favicon.png", optimize=True)            # Google wants a multiple of 48px
        sq(180).convert("RGB").save(OUT / "apple-touch-icon.png")   # iPhone home screen
        sq(48).save(OUT / "favicon.ico", sizes=[(48, 48), (32, 32), (16, 16)])
        SHARE["icon"] = True
    else:
        print("  ! no content/favicon.png — Google shows a grey globe instead of an icon")

    works = []
    wdir = CONTENT / "works"
    for d in sorted((p for p in wdir.iterdir() if p.is_dir()), reverse=True) if wdir.exists() else []:
        meta, body, multi = parse_txt(d / "info.txt")
        imgs = sorted((p for p in d.iterdir() if p.suffix.lower() in IMG_EXT), key=lambda p: ([int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.stem)], p.name))
        if not imgs:
            print(f"  ! skipped {d.name}: no images")
            continue
        cover = next((p for p in imgs if p.stem.lower() == "cover"), imgs[0])
        works.append({
            "slug": slugify(d.name),
            "title": meta.get("title", d.name),
            "year": meta.get("year", ""),
            "medium": meta.get("medium", ""),
            "cats": cat_keys(meta.get("category", "")),
            "videos": [v for k, v in multi if k == "video"],
            "body": body,
            "imgs": [p for p in imgs if p != cover or p.stem.lower() != "cover"],
            "cover": cover,
        })

    def archive(base, extra_cls="", filtered=True):   # filtered=False: always the whole archive
        cells = "".join(
            f'<a href="{base}works/{w["slug"]}/index.html"'
            + (f' data-cat="{" ".join(w["cats"])}"' if filtered else '') + '><div class="th">'
            f'<img src="{base}works/{w["slug"]}/_thumb.jpg" loading="lazy" alt="{html.escape(w["title"])}"></div>'
            f'<span>{html.escape(w["title"])}</span></a>' for w in works)
        return f'<div class="grid {extra_cls}">{cells}</div>'

    # ---- work pages: all photos in order, then videos last (NONOTAK order)
    for w in works:
        odir = OUT / "works" / w["slug"]
        imgs = []
        for im in w["imgs"]:
            srcset, mid, big, orig = variants(im, odir, im.stem)
            alt = f'{w["title"]}{", " + w["year"] if w["year"] else ""} — {site["name"]}'
            imgs.append(f'<img src="{html.escape(mid)}" srcset="{html.escape(srcset)}" '
                        f'sizes="(max-width:860px) 100vw, 910px" data-big="{html.escape(big)}" '
                        f'data-full="{html.escape(orig)}" loading="lazy" alt="{html.escape(alt, quote=True)}">')
        resize(w["cover"], odir / "_thumb.jpg", THUMB_MAX)
        media = imgs + [embed(v) for v in w["videos"]]
        head = ", ".join(x for x in (w["medium"], w["year"]) if x)
        plain = re.sub(r"[*#\[\]]|\(https?://[^)]*\)", "", w["body"]).split("\n\n")[0].replace("\n", " ").strip()
        wdesc = f'{w["title"]}{" (" + w["year"] + ")" if w["year"] else ""} by {site["name"]}' + (f'. {head}' if head else '') + (f'. {plain}' if plain else '')
        wdesc = wdesc[:200].rsplit(" ", 1)[0] + "…" if len(wdesc) > 200 else wdesc
        aside = (f'<div class="head"><em>{html.escape(w["title"])}</em>'
                 f'{", " + html.escape(head) if head else ""}.</div>{para(w["body"])}')
        (odir / "index.html").write_text(
            page(f'{w["title"]} – {site["name"]}', build_nav("../../", site, works, w["slug"]),
                 "\n".join(media) + archive("../../", "archive"), aside,
                 base="../../", name=site["name"], path=f'works/{w["slug"]}/', desc=wdesc,
                 work_head=(f'<em>{html.escape(w["title"])}</em>' + (f' · {html.escape(w["year"])}' if w["year"] else ""))),
            encoding="utf-8")

    # ---- portfolio PDFs (content/pdf/portfolio_en.pdf, _de, _ko)
    pdf_links = []
    pdir = CONTENT / "pdf"
    for code, label in PDF_LANGS:
        src = next(iter(sorted(pdir.glob(f"*_{code}.pdf"))), None) if pdir.exists() else None
        if src:
            dst = OUT / "pdf" / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            mb = src.stat().st_size / 1e6
            if mb > 25:
                print(f"  ! {src.name} is {mb:.0f} MB — keep portfolio PDFs under ~20 MB")
            pdf_links.append(f'<a href="pdf/{html.escape(src.name)}" download>{label} (PDF)</a>')
    pdf_html = (f'<div class="pdf"><h2>Portfolio</h2>{"".join(pdf_links)}</div>'
                if pdf_links else "")

    # ---- home: archive grid + intro text + PDF downloads in the right column
    _, hbody, _ = parse_txt(CONTENT / "home.txt")
    (OUT / "index.html").write_text(
        page(home_title, build_nav("", site, works, "_portfolio"),
             archive(""), para(hbody) + pdf_html, base="", name=site["name"], jsonld=person_ld), encoding="utf-8")

    # ---- about: about.txt in the centre, contact.txt in the right column
    ameta, abody, _ = parse_txt(CONTENT / "about.txt")
    _, cbody, _ = parse_txt(CONTENT / "contact.txt")
    portrait = CONTENT / ameta["image"] if ameta.get("image") else None
    main_html = ""
    if portrait and portrait.exists():
        srcset, mid, _, _ = variants(portrait, OUT / "about", "portrait")
        main_html = f'<img src="{mid}" srcset="{srcset}" sizes="(max-width:860px) 100vw, 910px" alt="">'
    main_html += f'<div class="text">{para(abody)}</div>'
    (OUT / "about").mkdir(parents=True, exist_ok=True)
    (OUT / "about" / "index.html").write_text(
        page(f'About – {site["name"]}', build_nav("../", site, works, "_about"),
             main_html + archive("../", "archive all", filtered=False), para(cbody), base="../", name=site["name"], path="about/",
             jsonld=person_ld),
        encoding="utf-8")

    today = datetime.date.today().isoformat()
    urls = "".join(f"<url><loc>{SHARE['url']}/{p}</loc><lastmod>{today}</lastmod></url>" for p in PAGES)
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n', encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SHARE['url']}/sitemap.xml\n")
    (OUT / ".nojekyll").write_text("")
    print(f"built {len(works)} works, {len(pdf_links)} PDFs -> {OUT}")


if __name__ == "__main__":
    main()
