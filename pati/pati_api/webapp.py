"""PATI web dashboard: server-rendered pages + installable PWA.

Design rules (inherited from docs/FREE_FIRST_POLICY.md):
- No build step, no npm, no framework: one vanilla-JS page served by FastAPI.
- No third-party requests at runtime (no CDNs, no analytics beacons).
- Pages are public shells; all personal data requires a bearer token.
- Every page: unique title, meta description, canonical URL, OG image, alt text.

Pages: / (dashboard), /faq, /privacy, /thank-you, /offline, custom 404.
Extras: /robots.txt, /sitemap.xml, /llms.txt, /manifest.webmanifest, /sw.js.
"""
from __future__ import annotations

import html
import json
import time

from . import __version__, config, db

THEME = {
    "bg": "#0b0f14", "panel": "#13202b", "panel2": "#0e1620",
    "border": "#1f3547", "teal": "#66d9c2", "blue": "#8ab4f8",
    "text": "#d7e2ee", "muted": "#8c9baa", "ok": "#7ee787",
    "warn": "#f0c674", "err": "#ff7b72",
}

PROMISE = ("Jobs are accepted instantly and dispatched to a free worker within "
           "seconds. Local jobs finish in minutes; free-GPU jobs usually in "
           "2-15 minutes. When no free worker is available your job waits "
           "(WAITING_FOR_RESOURCE) - PATI never pays to skip the line.")

# --------------------------------------------------------------------------
# CSS (shared design system; mobile-first, no external fonts/CDNs)
# --------------------------------------------------------------------------
CSS = """
:root{--bg:#0b0f14;--panel:#13202b;--panel2:#0e1620;--border:#1f3547;
--teal:#66d9c2;--blue:#8ab4f8;--text:#d7e2ee;--muted:#8c9baa;
--ok:#7ee787;--warn:#f0c674;--err:#ff7b72;--radius:14px}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{background:var(--bg);color:var(--text);
font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
line-height:1.55;min-height:100vh}
a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}
code{font-family:ui-monospace,Consolas,monospace;font-size:.92em;
background:var(--panel2);border:1px solid var(--border);border-radius:6px;
padding:1px 6px;color:var(--teal)}
img,svg,video{max-width:100%;display:block}
/* ---------- header ---------- */
header{position:sticky;top:0;z-index:50;background:rgba(11,15,20,.92);
backdrop-filter:blur(8px);border-bottom:1px solid var(--border)}
.hwrap{max-width:1080px;margin:0 auto;padding:.65rem 1rem;display:flex;
align-items:center;gap:.8rem;flex-wrap:wrap}
.logo{display:flex;align-items:center;gap:.55rem;font-weight:800;
font-size:1.12rem;color:var(--text)}
.logo img{width:30px;height:30px;border-radius:8px}
.logo .v{font-size:.68rem;color:var(--muted);font-weight:600}
nav{margin-left:auto;display:flex;gap:1rem;align-items:center;font-size:.95rem}
nav a{color:var(--muted);padding:.4rem .2rem}
nav a[aria-current="page"]{color:var(--teal);font-weight:700}
nav a:hover{color:var(--text)}
/* ---------- layout ---------- */
main{max-width:1080px;margin:0 auto;padding:1rem 1rem 5.5rem}
.crumb{font-size:.85rem;color:var(--muted);margin:.6rem 0 .2rem}
.crumb a{color:var(--muted)}
h1{font-size:1.55rem;margin:.4rem 0 .8rem}
h2{font-size:1.15rem;margin:1.6rem 0 .7rem;color:var(--teal)}
h3{font-size:1rem;margin:1rem 0 .4rem}
p{margin:.5rem 0}
.muted{color:var(--muted);font-size:.9rem}
.badge{display:inline-block;background:var(--panel);border:1px solid var(--border);
border-radius:999px;padding:.15rem .7rem;font-size:.78rem;font-weight:700;
color:var(--teal);margin:.15rem .25rem .15rem 0}
.card{background:var(--panel);border:1px solid var(--border);
border-radius:var(--radius);padding:1rem;margin:.7rem 0}
.grid{display:grid;gap:.7rem;grid-template-columns:1fr}
@media(min-width:720px){.grid{grid-template-columns:repeat(3,1fr)}}
.stat .n{font-size:1.5rem;font-weight:800;color:var(--teal)}
.stat .l{font-size:.8rem;color:var(--muted)}
/* ---------- hero CTA (above the fold) ---------- */
.hero{background:linear-gradient(180deg,var(--panel),var(--panel2));
border:1px solid var(--border);border-radius:var(--radius);
padding:1.1rem;margin:.8rem 0 1rem}
.hero label{font-weight:800;font-size:1.05rem;display:block;margin-bottom:.5rem}
.hero .row{display:flex;gap:.6rem;flex-wrap:wrap}
.hero input[type=text]{flex:1 1 240px;min-height:48px;background:var(--panel2);
border:1px solid var(--border);border-radius:10px;color:var(--text);
padding:.7rem .9rem;font-size:1rem}
.hero input[type=text]:focus{outline:2px solid var(--teal);border-color:var(--teal)}
button{cursor:pointer;border:none;border-radius:10px;font-size:1rem;
min-height:48px;padding:.7rem 1.3rem;font-weight:700}
.btn-primary{background:var(--teal);color:#06251f}
.btn-primary:disabled{opacity:.55;cursor:wait}
.btn-ghost{background:transparent;color:var(--blue);
border:1px solid var(--border)}
.chips{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.7rem}
.chip{background:var(--panel2);border:1px solid var(--border);color:var(--text);
border-radius:999px;padding:.45rem .9rem;min-height:0;font-size:.88rem;
font-weight:600}
.chip:hover{border-color:var(--teal);color:var(--teal)}
/* ---------- promise strip ---------- */
.promise{border-left:4px solid var(--teal);background:var(--panel2);
padding:.7rem .9rem;border-radius:0 var(--radius) var(--radius) 0;
font-size:.9rem;margin:.8rem 0}
.promise b{color:var(--teal)}
/* ---------- connect ---------- */
.connect{display:flex;gap:.6rem;flex-wrap:wrap;align-items:center}
.connect input{flex:1 1 220px;min-height:44px;background:var(--panel2);
border:1px solid var(--border);border-radius:10px;color:var(--text);
padding:.5rem .8rem;font-size:.95rem}
.dot{width:9px;height:9px;border-radius:50%;background:var(--muted);
display:inline-block;margin-right:.4rem}
.dot.on{background:var(--ok)}.dot.off{background:var(--err)}
/* ---------- jobs ---------- */
.job{display:flex;gap:.8rem;align-items:flex-start;padding:.8rem;
border:1px solid var(--border);border-radius:12px;background:var(--panel2);
margin:.5rem 0}
.job .t{flex:1;min-width:0}
.job .title{font-weight:700;overflow-wrap:anywhere}
.job .meta{font-size:.8rem;color:var(--muted);margin-top:.15rem}
.pill{font-size:.72rem;font-weight:800;border-radius:999px;padding:.2rem .65rem;
white-space:nowrap;letter-spacing:.02em}
.pill.completed{background:rgba(126,231,135,.12);color:var(--ok)}
.pill.running{background:rgba(138,180,248,.14);color:var(--blue)}
.pill.failed{background:rgba(255,123,114,.14);color:var(--err)}
.pill.waiting{background:rgba(240,198,116,.14);color:var(--warn)}
.pill.queued{background:rgba(140,155,170,.14);color:var(--muted)}
.bar{height:6px;background:var(--panel);border:1px solid var(--border);
border-radius:99px;margin-top:.45rem;overflow:hidden}
.bar i{display:block;height:100%;background:var(--blue);border-radius:99px;
transition:width .5s}
.cancel{background:transparent;border:1px solid var(--border);color:var(--err);
min-height:0;padding:.35rem .7rem;font-size:.8rem;border-radius:8px}
/* ---------- gallery ---------- */
.gal{display:grid;gap:.6rem;grid-template-columns:repeat(2,1fr)}
@media(min-width:720px){.gal{grid-template-columns:repeat(4,1fr)}}
.gal .item{background:var(--panel2);border:1px solid var(--border);
border-radius:12px;overflow:hidden;position:relative;min-height:110px;
display:flex;align-items:center;justify-content:center}
.gal img,.gal video{width:100%;height:150px;object-fit:cover;background:#000}
.gal .file{padding:.6rem;font-size:.8rem;color:var(--muted);
text-align:center;overflow-wrap:anywhere}
.gal .cap{position:absolute;left:0;right:0;bottom:0;font-size:.68rem;
background:rgba(11,15,20,.85);padding:.2rem .45rem;color:var(--muted);
white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
/* ---------- flows ---------- */
.flow .tags{margin-top:.5rem}
/* ---------- owner ---------- */
.owner{display:flex;gap:1rem;align-items:center}
.owner img{width:76px;height:76px;border-radius:50%;
border:2px solid var(--border);object-fit:cover;background:var(--panel2)}
.owner .init{width:76px;height:76px;border-radius:50%;background:var(--panel2);
border:2px solid var(--border);display:flex;align-items:center;
justify-content:center;font-size:1.6rem;font-weight:800;color:var(--teal)}
/* ---------- footer ---------- */
footer{border-top:1px solid var(--border);margin-top:2.5rem;
padding:1.2rem 1rem 6rem;font-size:.85rem;color:var(--muted)}
footer .fwrap{max-width:1080px;margin:0 auto;display:flex;gap:1.2rem;
flex-wrap:wrap}
footer a{color:var(--muted)}
/* ---------- sticky mobile CTA ---------- */
.sticky{position:fixed;left:0;right:0;bottom:0;z-index:60;display:flex;
gap:.7rem;padding:.7rem 1rem calc(.7rem + env(safe-area-inset-bottom));
background:rgba(11,15,20,.95);backdrop-filter:blur(8px);
border-top:1px solid var(--border)}
.sticky button{flex:1}
@media(min-width:768px){.sticky{display:none}}
main{padding-bottom:2rem}
@media(max-width:767px){footer{padding-bottom:7rem}}
/* ---------- misc ---------- */
.center{text-align:center;padding:3.5rem 1rem}
.big{font-size:3rem}
.install{display:none}
.install.show{display:inline-block}
"""

# --------------------------------------------------------------------------
# shared page shell: unique titles, meta description, canonical, OG, JSON-LD
# --------------------------------------------------------------------------

def _nav(page: str) -> str:
    def cur(p):
        return ' aria-current="page"' if page == p else ""
    return f"""<header><div class="hwrap">
  <a class="logo" href="/" aria-label="PATI home">
    <img src="/assets/favicon-64.png" alt="PATI logo" width="30" height="30">
    PATI <span class="v">v{__version__}</span></a>
  <nav aria-label="Main">
    <a href="/"{cur("home")}>Dashboard</a>
    <a href="/faq"{cur("faq")}>FAQ</a>
    <a href="/privacy"{cur("privacy")}>Privacy</a>
  </nav></div></header>"""


def page_shell(*, page: str, base: str, title: str, description: str,
               body: str, json_ld: dict | None = None,
               crumbs: list[tuple[str, str]] | None = None,
               scripts: str = "") -> str:
    canonical = f"{base}/{'' if page == 'home' else page.strip('/')}"
    og_image = f"{base}/assets/og-image.png"
    ld = json_ld or {"@context": "https://schema.org",
                     "@type": "WebPage", "name": title, "url": canonical}
    crumb_html = ""
    if crumbs:
        bits = " / ".join(
            f'<a href="{html.escape(u)}">{html.escape(t)}</a>' if u
            else f"<span>{html.escape(t)}</span>" for t, u in crumbs)
        crumb_html = f'<nav class="crumb" aria-label="Breadcrumb">{bits}</nav>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="canonical" href="{html.escape(canonical)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="PATI">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:url" content="{html.escape(canonical)}">
<meta property="og:image" content="{html.escape(og_image)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="PATI - your personal AI, free forever">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(title)}">
<meta name="twitter:description" content="{html.escape(description)}">
<meta name="twitter:image" content="{html.escape(og_image)}">
<meta name="theme-color" content="{THEME['bg']}">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/assets/favicon-64.png" sizes="64x64">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="PATI">
<script type="application/ld+json">{json.dumps(ld)}</script>
<style>{CSS}</style>
</head>
<body>
{_nav(page)}
<main>
{crumb_html}
{body}
</main>
<footer><div class="fwrap">
  <a href="/">Dashboard</a><a href="/faq">FAQ</a><a href="/privacy">Privacy</a>
  <a href="/docs" rel="nofollow">API docs</a>
  <a href="/llms.txt" rel="nofollow">llms.txt</a>
  <span>Local, zero-cost infrastructure. No trackers.</span>
</div></footer>
{scripts}
</body>
</html>"""


# --------------------------------------------------------------------------
# dashboard
# --------------------------------------------------------------------------
DASHBOARD_JS = """
<script>
"use strict";
var $ = function(s){ return document.querySelector(s); };
var token = "";
try { token = localStorage.getItem("pati_token") || ""; } catch(e) {}

function esc(s){ var d = document.createElement("div");
  d.textContent = s == null ? "" : String(s); return d.innerHTML; }

function setDot(ok, label){
  var d = $("#connDot"); if(!d) return;
  d.className = "dot " + (ok ? "on" : "off");
  $("#connLabel").textContent = label;
}

function api(path, opts){
  opts = opts || {};
  opts.headers = Object.assign({}, opts.headers || {},
    token ? { "Authorization": "Bearer " + token } : {});
  if (opts.json){ opts.method = opts.method || "POST";
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(opts.json); delete opts.json; }
  return fetch(path, opts);
}

function connect(){
  var v = $("#tokenInput").value.trim();
  if (!v){ $("#connMsg").textContent = "Paste your token first."; return; }
  token = v;
  try { localStorage.setItem("pati_token", token); } catch(e) {}
  $("#tokenInput").value = "";
  refresh();
}

function disconnect(){
  token = "";
  try { localStorage.removeItem("pati_token"); } catch(e) {}
  setDot(false, "Not connected");
  $("#connMsg").textContent = "Disconnected on this device.";
  $("#jobsList").innerHTML = "";
  $("#galGrid").innerHTML = "";
}

var STATUS_PILL = { COMPLETED:"completed", RUNNING:"running", FAILED:"failed",
  CANCELLED:"queued", WAITING_FOR_RESOURCE:"waiting", PLANNED:"queued",
  QUEUED:"queued", DISPATCHED:"running" };

function pill(status){
  var cls = STATUS_PILL[status] || "queued";
  return '<span class="pill ' + cls + '">' + esc(status) + "</span>";
}

function renderJobs(tasks){
  var box = $("#jobsList");
  if (!tasks.length){ box.innerHTML =
    '<p class="muted">No jobs yet. Try the quick actions above.</p>'; return; }
  box.innerHTML = tasks.map(function(t){
    var prog = "";
    if (t._done != null && t._total)
      prog = '<div class="bar"><i style="width:' +
        Math.round(100 * t._done / t._total) + '%"></i></div>' +
        '<div class="meta">' + t._done + "/" + t._total + " stages</div>";
    var cancel = (t.status === "RUNNING" || t.status === "WAITING_FOR_RESOURCE")
      ? ' <button class="cancel" data-cancel="' + esc(t.id) +
        '" aria-label="Cancel job">Cancel</button>' : "";
    return '<div class="job"><div class="t">' +
      '<div class="title">' + esc(t.title || t.objective || "(untitled)") + "</div>" +
      '<div class="meta">' + esc(t.type) + " - " + esc(t.created_at || "") +
      " - " + esc(t.id.slice(0, 12)) + "</div>" + prog + "</div>" +
      "<div>" + pill(t.status) + cancel + "</div></div>";
  }).join("");
  box.querySelectorAll("[data-cancel]").forEach(function(b){
    b.addEventListener("click", function(){
      b.disabled = true;
      api("/api/v1/tasks/" + b.getAttribute("data-cancel") + "/cancel",
          { method: "POST" }).then(refresh).catch(function(){ b.disabled = false; });
    });
  });
}

function renderGallery(arts){
  var grid = $("#galGrid");
  var media = arts.filter(function(a){
    return (a.mime_type || "").indexOf("image/") === 0 ||
           (a.mime_type || "").indexOf("video/") === 0; }).slice(0, 12);
  var files = arts.filter(function(a){
    return (a.mime_type || "").indexOf("image/") !== 0 &&
           (a.mime_type || "").indexOf("video/") !== 0; }).slice(0, 6);
  grid.innerHTML = "";
  if (!media.length && !files.length){
    grid.innerHTML = '<p class="muted">Nothing yet. Finished videos and images ' +
      "will appear here.</p>"; return;
  }
  media.forEach(function(a){
    var item = document.createElement("div");
    item.className = "item";
    var cap = document.createElement("div");
    cap.className = "cap"; cap.textContent = a.name || a.id;
    var url = "/api/v1/artifacts/" + encodeURIComponent(a.id) + "/content";
    api(url).then(function(r){ if(!r.ok) throw 0; return r.blob(); })
      .then(function(b){
        var u = URL.createObjectURL(b);
        if ((a.mime_type || "").indexOf("video/") === 0){
          var v = document.createElement("video");
          v.controls = true; v.preload = "metadata"; v.src = u;
          v.setAttribute("aria-label", a.name || "video artifact");
          item.appendChild(v);
        } else {
          var im = document.createElement("img");
          im.loading = "lazy"; im.src = u; im.alt = a.name || "image artifact";
          item.appendChild(im);
        }
        item.appendChild(cap);
      }).catch(function(){
        item.innerHTML = '<div class="file">' + esc(a.name || a.id) + "</div>";
        item.appendChild(cap);
      });
    grid.appendChild(item);
  });
  files.forEach(function(a){
    var item = document.createElement("div");
    item.className = "item";
    item.innerHTML = '<div class="file">' + esc(a.name || a.id) +
      "<br>" + esc(a.type || "") + "</div>";
    grid.appendChild(item);
  });
}

function loadDetails(tasks){
  var active = tasks.filter(function(t){
    return ["COMPLETED","FAILED","CANCELLED"].indexOf(t.status) === -1; });
  var chain = Promise.resolve();
  active.slice(0, 8).forEach(function(t){
    chain = chain.then(function(){
      return api("/api/v1/tasks/" + encodeURIComponent(t.id))
        .then(function(r){ return r.ok ? r.json() : null; })
        .then(function(d){
          if (d && d.stages && d.stages.length){
            t._total = d.stages.length;
            t._done = d.stages.filter(function(s){
              return s.status === "COMPLETED"; }).length;
          }
        }).catch(function(){});
    });
  });
  return chain;
}

function refresh(){
  if (!token){ setDot(false, "Not connected"); return; }
  api("/api/v1/system/status").then(function(r){
    if (r.status === 401 || r.status === 403){
      setDot(false, "Token rejected"); return null; }
    return r.json();
  }).then(function(s){
    if (!s) return;
    setDot(true, "Connected");
    $("#stWorkers").textContent =
      (s.workers && (s.workers.online || s.workers.available)) || 0;
    $("#stTasks").textContent =
      Object.values(s.tasks || {}).reduce(function(a, b){ return a + b; }, 0);
  }).catch(function(){ setDot(false, "Offline"); });

  api("/api/v1/quotas").then(function(r){ return r.ok ? r.json() : null; })
    .then(function(q){
      if (!q) return;
      var g = q.gpu || q.GPU || {};
      var left = (g.remaining_minutes != null) ? g.remaining_minutes :
                 (g.remaining != null ? g.remaining : null);
      if (left != null) $("#stGpu").textContent = left + " min";
    }).catch(function(){});

  api("/api/v1/tasks?limit=10").then(function(r){
    if (!r.ok) return []; return r.json();
  }).then(function(d){ return d.tasks || []; })
    .then(function(tasks){ return loadDetails(tasks).then(function(){ return tasks; }); })
    .then(renderJobs).catch(function(){});

  api("/api/v1/artifacts").then(function(r){
    if (!r.ok) return { artifacts: [] }; return r.json();
  }).then(function(d){ renderGallery(d.artifacts || []); }).catch(function(){});
}

function submitJob(ev){
  ev.preventDefault();
  var obj = $("#objective").value.trim();
  var kind = $("#jobKind").value || "auto";
  if (!obj){ $("#objective").focus(); return; }
  if (!token){
    $("#connMsg").textContent =
      "Connect with your token first (box below the quick actions).";
    $("#tokenInput").focus(); return;
  }
  var btn = $("#runBtn");
  btn.disabled = true; btn.textContent = "Submitting...";
  var payload = { objective: obj, type: "auto" };
  if (kind === "video_workflow"){
    payload.type = "video_workflow"; payload.params = { scenes: 3 };
  }
  api("/api/v1/tasks", { json: payload }).then(function(r){
    btn.disabled = false; btn.textContent = "Run it";
    if (r.status === 401 || r.status === 403){
      $("#connMsg").textContent = "Token missing or rejected - connect first.";
      return null;
    }
    if (r.status === 429){
      $("#connMsg").textContent =
        "Daily free quota used up. The job parked - try again tomorrow.";
      return null;
    }
    if (!r.ok){ $("#connMsg").textContent = "Could not submit (HTTP " +
      r.status + ")."; return null; }
    return r.json();
  }).then(function(t){
    if (!t) return;
    $("#objective").value = "";
    window.location.href = "/thank-you?job=" + encodeURIComponent(t.id);
  }).catch(function(){
    btn.disabled = false; btn.textContent = "Run it";
    $("#connMsg").textContent = "Network error - is PATI running?";
  });
}

var chips = {
  video:  "Create a 60-second animated story",
  image:  "Generate an image of ",
  organize: null,
  research: "Research "
};
document.addEventListener("DOMContentLoaded", function(){
  document.querySelectorAll("[data-chip]").forEach(function(c){
    c.addEventListener("click", function(){
      var k = c.getAttribute("data-chip");
      $("#jobKind").value = (k === "video") ? "video_workflow" : "auto";
      if (k === "organize"){
        var p = window.prompt("Which folder should PATI organize? " +
          "(full path inside your authorized directories, e.g. " +
          "C:\\\\Users\\\\you\\\\Videos)");
        if (!p) return;
        $("#objective").value = "Organize my folder at " + p;
        $("#jobKind").value = "filesystem_organize";
      } else {
        $("#objective").value = chips[k] || "";
        $("#objective").focus();
      }
    });
  });
  $("#jobForm").addEventListener("submit", submitJob);
  $("#connectBtn").addEventListener("click", connect);
  $("#forgetBtn").addEventListener("click", disconnect);
  $("#newJobBtn").addEventListener("click", function(){
    window.scrollTo({ top: 0, behavior: "smooth" });
    setTimeout(function(){ $("#objective").focus(); }, 350);
  });
  setDot(!!token, token ? "Saved on this device" : "Not connected");
  var ip = null;
  window.addEventListener("beforeinstallprompt", function(e){
    e.preventDefault(); ip = e;
    var b = $("#installBtn"); b.classList.add("show");
    b.addEventListener("click", function(){
      b.classList.remove("show");
      ip.prompt(); ip = null;
    });
  });
  if ("serviceWorker" in navigator){
    navigator.serviceWorker.register("/sw.js").catch(function(){});
  }
  refresh();
  setInterval(refresh, 5000);
});
</script>"""


def _snapshot() -> dict:
    try:
        workers = db.query("SELECT status, COUNT(*) c FROM workers GROUP BY status")
        tasks = db.query("SELECT status, COUNT(*) c FROM tasks GROUP BY status")
        return {
            "workers": {r["status"]: r["c"] for r in workers},
            "tasks": {r["status"]: r["c"] for r in tasks},
            "ok": True,
        }
    except Exception:
        return {"workers": {}, "tasks": {}, "ok": False}


def _bump_visits() -> int:
    try:
        db.execute("INSERT INTO kv(key, value) VALUES('dashboard_visits','1') "
                   "ON CONFLICT(key) DO NOTHING")
        db.execute("UPDATE kv SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) "
                   "WHERE key='dashboard_visits'")
        row = db.query_one("SELECT value FROM kv WHERE key='dashboard_visits'")
        return int(row["value"]) if row else 0
    except Exception:
        return 0


def render_dashboard(base: str) -> str:
    snap = _snapshot()
    visits = _bump_visits()
    workers_total = sum(snap["workers"].values())
    tasks_total = sum(snap["tasks"].values())
    body = f"""
<section class="hero" aria-label="New job">
  <label for="objective">What should PATI do?</label>
  <form id="jobForm" class="row">
    <input type="text" id="objective" name="objective" autocomplete="off"
      placeholder="e.g. Make a 3-scene video about mountain hiking"
      aria-label="Describe the job for PATI">
    <input type="hidden" id="jobKind" value="auto">
    <button type="submit" id="runBtn" class="btn-primary">Run it</button>
  </form>
  <div class="chips" role="group" aria-label="Quick actions">
    <button type="button" class="chip" data-chip="video">Make a video</button>
    <button type="button" class="chip" data-chip="image">Generate an image</button>
    <button type="button" class="chip" data-chip="organize">Organize a folder</button>
    <button type="button" class="chip" data-chip="research">Research a topic</button>
    <button type="button" class="chip" id="installBtn">Install as app</button>
  </div>
  <p id="connMsg" class="muted" role="status"></p>
</section>

<div class="promise"><b>Our response-time promise:</b> {PROMISE}</div>

<div class="card connect" aria-label="Connect this device">
  <span><span class="dot" id="connDot"></span><span id="connLabel">Not connected</span></span>
  <input type="password" id="tokenInput" placeholder="Paste your PATI token"
    aria-label="PATI access token">
  <button type="button" class="btn-primary" id="connectBtn">Connect</button>
  <button type="button" class="btn-ghost" id="forgetBtn">Forget</button>
  <span id="connMsg2" class="muted">Your token stays in this browser only.
  Find it in your install wizard output.</span>
</div>

<h2>System</h2>
<div class="grid">
  <div class="card stat"><div class="n" id="stWorkers">{workers_total}</div>
    <div class="l">Workers registered</div></div>
  <div class="card stat"><div class="n" id="stTasks">{tasks_total}</div>
    <div class="l">Jobs total</div></div>
  <div class="card stat"><div class="n" id="stGpu">connect</div>
    <div class="l">Free GPU minutes left today</div></div>
</div>
<p class="muted">FREE_ONLY = true - MAX_SPEND = 0 - paid fallbacks impossible.
<a href="/privacy">See exactly what data stays on your PC.</a></p>

<h2 id="jobs">Your jobs</h2>
<div id="jobsList"><p class="muted">Connect to load live jobs.</p></div>

<h2 id="gallery">Gallery</h2>
<div id="galGrid" class="gal"><p class="muted">Connect to load your images,
videos and files.</p></div>

<h2>What PATI can do - proven, not promised</h2>
<div class="grid">
  <div class="card flow">
    <h3>Flow 1 - Tidy my disk</h3>
    <p class="muted">"Create a folder called YouTube Project 01 and organize
    today's files" - planned into sequential stages, executed on your own PC
    by the local agent, with a hash-chained audit trail.</p>
    <div class="tags"><span class="badge">runs on your PC</span>
    <span class="badge">path-guarded</span><span class="badge">audited</span></div>
  </div>
  <div class="card flow">
    <h3>Flow 2 - Free-GPU video</h3>
    <p class="muted">Story, script, character bible, storyboard, three scenes
    generated in parallel, then assembly - executed on Kaggle's free GPUs,
    budgeted at 240 GPU-minutes per day.</p>
    <div class="tags"><span class="badge">15 stages</span>
    <span class="badge">Kaggle free GPU</span><span class="badge">never pays</span></div>
  </div>
  <div class="card flow">
    <h3>Everything else</h3>
    <p class="muted">Images, voice, music, research reports, code, file
    operations - 94 registered capabilities, every single one priced at $0,
    with honest WAITING_FOR_RESOURCE instead of paid shortcuts.</p>
    <div class="tags"><span class="badge">94 capabilities</span>
    <span class="badge">$0 forever</span></div>
  </div>
</div>

<div class="card owner" aria-label="Owner">
  <img src="/owner-photo.png" alt="Portrait of the PATI owner" id="ownerPhoto"
    width="76" height="76">
  <div>
    <h3 style="margin:0">The owner (that's you)</h3>
    <p class="muted">PATI is single-owner infrastructure: one household, one
    PC, one mission. Want your own photo here? Drop an image named
    <code>owner-photo.png</code> into PATI's data folder - it never leaves
    your machine.</p>
  </div>
</div>

<p class="muted">This dashboard has served <strong>{visits}</strong> page
views - counted locally in PATI's own database. No Google Analytics, no
third-party pixels, nothing phones home. <a href="/faq">Questions? Read the FAQ.</a></p>

<div class="sticky" aria-label="Quick new job">
  <button type="button" class="btn-primary" id="newJobBtn">+ New job</button>
</div>
"""
    scripts = DASHBOARD_JS
    return page_shell(
        page="home", base=base,
        title="PATI Dashboard - Your Personal AI, Free Forever",
        description=("Control your personal AI from any device: make videos, "
                     "images, voice and music, organize folders, research and "
                     "code. 100% local, zero cost, installable as an app on "
                     "iOS and Android."),
        body=body,
        json_ld={
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": "PATI",
            "applicationCategory": "MultimediaApplication",
            "operatingSystem": "Windows, macOS, Linux (self-hosted personal server)",
            "softwareVersion": __version__,
            "description": "Personal AI Tool Infrastructure: a zero-cost, "
                           "local-first control plane that plans and executes "
                           "text, image, video, audio, research and file jobs "
                           "on free compute.",
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            "isAccessibleForFree": True,
        },
        scripts=scripts)

FAQS = [
    ("What is PATI, in one sentence?",
     "PATI is your own private AI system: it lives on your PC, plans and "
     "executes jobs (videos, images, voice, music, research, code, file "
     "organization) on free compute, and never spends money."),
    ("Is it really $0? Where's the catch?",
     "There is no catch and no card on file. Everything runs on free tiers: "
     "your own PC, plus Kaggle's free GPUs for heavy jobs (budgeted at 240 "
     "GPU-minutes per day by PATI itself). If no free worker is available, "
     "jobs wait - the system is hard-wired so it cannot fall back to paid "
     "services (FREE_ONLY = true, MAX_SPEND = 0)."),
    ("How do I install it as an app on my phone?",
     "Open this dashboard in your phone's browser (through your Cloudflare "
     "tunnel address), then: on Android tap the 'Install as app' button or "
     "the browser menu's 'Add to Home screen'; on iPhone tap the Share "
     "button, then 'Add to Home Screen'. It launches full-screen like a "
     "native app - no app store, no fees."),
    ("Where do I find my token?",
     "Your install wizard printed it when you set PATI up (and it is stored "
     "in PATI's data folder). Paste it once into the Connect box; it is kept "
     "only in that browser's local storage. Never share it in chats or "
     "emails."),
    ("How long does a video take?",
     "A 3-scene video usually completes within a few minutes of free-GPU "
     "time. Each job shows a live stage progress bar (story, script, "
     "storyboard, scenes, assembly). If the daily GPU budget is used up, the "
     "job waits until tomorrow rather than paying."),
    ("What does WAITING_FOR_RESOURCE mean?",
     "It means your job is parked safely because no free worker is free "
     "right now. It is the honest alternative to spending money: the moment "
     "a free worker appears, your job runs automatically."),
    ("Who can see my files and jobs?",
     "Only you. The dashboard pages are public shells, but every piece of "
     "personal data requires your bearer token. The local agent is "
     "path-guarded: it can only touch folders you explicitly authorized "
     "during setup, and every action is written to a tamper-evident audit "
     "log."),
    ("Does PATI use Google Analytics or trackers?",
     "No. Page views are counted locally in PATI's own database. Nothing "
     "phones home, no cookies are set, no third-party scripts are loaded - "
     "see the Privacy page."),
    ("How do I update PATI?",
     "Run the updater from the installer folder, or re-run install.ps1 - it "
     "upgrades in place and keeps your data. The dashboard shows the running "
     "version in the header."),
    ("Something broke - where do I start?",
     "Run `python -m pati_agent doctor` on the PC; it checks the server, "
     "workers, tokens and folders and tells you the fix. The full "
     "troubleshooting tables live in docs/TROUBLESHOOTING.md inside your "
     "PATI folder."),
]


def render_faq(base: str) -> str:
    items = "".join(
        f"<div class='card'><h3>{html.escape(q)}</h3><p>{html.escape(a)}</p></div>"
        for q, a in FAQS)
    body = f"""
<h1>Frequently asked questions</h1>
<p class=muted>Plain-English answers about installing, tokens, free GPU and
what PATI will never do.</p>
{items}
<p class=muted>More detail lives in the docs folder of your PATI install
(INSTALL.md, TROUBLESHOOTING.md, FREE_FIRST_POLICY.md).</p>
"""
    ld = {"@context": "https://schema.org", "@type": "FAQPage",
          "mainEntity": [
              {"@type": "Question", "name": q,
               "acceptedAnswer": {"@type": "Answer", "text": a}}
              for q, a in FAQS]}
    crumb = [("Dashboard", "/"), ("FAQ", "")]
    return page_shell(
        page="faq", base=base,
        title="PATI FAQ - Install, Tokens, Free GPU, Jobs",
        description=("Plain-English answers: is PATI really free, how to "
                     "install it as an app on iOS and Android, where your "
                     "token lives, how long videos take, and why jobs wait "
                     "instead of paying."),
        body=body, json_ld=ld, crumbs=crumb)


def render_privacy(base: str) -> str:
    body = """
<h1>Privacy</h1>
<p>PATI is built on a simple promise: <strong>your data stays on your
hardware.</strong> This page states exactly what that means - no legalese,
no dark patterns, because there is nothing to hide.</p>

<div class="card"><h3>What stays on your PC</h3>
<p>Every job, every generated video, image or document, every log line, the
audit trail, your token hashes and even this dashboard's visit counter live
in one folder on your own machine. Disconnect from the internet and PATI
still works for local jobs.</p></div>

<div class="card"><h3>What leaves your PC (and where it goes)</h3>
<p>Only what you ask for: heavy GPU jobs are sent to <a
href="https://www.kaggle.com" rel="noopener" target="_blank">Kaggle</a>'s
free compute using your own account and token. Those jobs contain your
prompt and generated files - nothing else. Remote access through Cloudflare
Tunnel is encrypted and requires your PATI token. That is the entire list.</p></div>

<div class="card"><h3>Trackers: none, on purpose</h3>
<p>There is no Google Analytics, no ads, no cookies, no fingerprinting, no
third-party fonts or CDNs. The visit count shown on the dashboard is a
single number stored in PATI's own database. You can verify all of it: the
whole system is source code on your disk.</p></div>

<div class="card"><h3>Your token</h3>
<p>Tokens are stored only as SHA-256 hashes on the server side; the plain
token lives where you put it. Each token is scoped (read/write per area),
rate-limited and revocable. Lost or leaked? Expire it from the admin CLI
and mint a new one in seconds.</p></div>

<div class="card"><h3>Delete everything</h3>
<p>Delete PATI's data folder and every byte of your data is gone. No cloud
copies exist because no cloud was ever involved. Uninstalling removes the
service, the tunnel config and the workspace.</p></div>

<p class=muted>Questions? The <a href="/faq">FAQ</a> covers the practical
follow-ups.</p>
"""
    crumb = [("Dashboard", "/"), ("Privacy", "")]
    return page_shell(
        page="privacy", base=base,
        title="PATI Privacy - Your Data Never Leaves Your PC",
        description=("No trackers, no Google Analytics, no cookies, no cloud. "
                     "PATI keeps every job, file and log on your own hardware; "
                     "only the jobs you choose go to Kaggle's free GPUs under "
                     "your own account."),
        body=body, crumbs=crumb)


def render_thanks(base: str, job_id: str) -> str:
    body = f"""
<div class="center">
  <div class="big" aria-hidden="true">\U0001F39C</div>
  <h1>Job submitted</h1>
  <p>PATI accepted your job and it is already in the queue.</p>
  <p class="muted">Job id: <code>{html.escape(job_id or '(see dashboard)')}</code></p>
  <div class="promise" style="text-align:left"><b>What happens now:</b> {PROMISE}</div>
  <p><a class="btn-primary" style="display:inline-block;text-decoration:none"
        href="/#jobs">Track it on the dashboard</a></p>
  <p class="muted">Tip: install PATI as an app (see the <a href="/faq">FAQ</a>)
  so finished videos ping you right on your home screen.</p>
</div>
"""
    crumb = [("Dashboard", "/"), ("Thank you", "")]
    return page_shell(
        page="thank-you", base=base,
        title="Job Submitted - PATI",
        description=("Your job is queued. PATI dispatches it to a free worker "
                     "within seconds and never pays to skip the line."),
        body=body, crumbs=crumb)


def render_404(base: str, path: str) -> str:
    body = f"""
<div class="center">
  <div class="big" aria-hidden="true">\U0001F50D</div>
  <h1>Page not found</h1>
  <p class="muted"><code>{html.escape(path[:120])}</code> does not exist on
  this PATI. It may have moved, or you followed an old link.</p>
  <p><a href="/" style="display:inline-block">Back to the dashboard</a>
     &nbsp;-&nbsp; <a href="/faq">Read the FAQ</a></p>
</div>
"""
    return page_shell(
        page="404", base=base,
        title="Page Not Found - PATI",
        description="That page does not exist. Head back to the PATI dashboard.",
        body=body)


def render_offline() -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Offline - PATI</title>
<meta name="description" content="PATI is temporarily unreachable. Check that the PC running PATI is awake, then retry the dashboard.">
<meta name="robots" content="noindex">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<style>body{{background:{THEME['bg']};color:{THEME['text']};
font-family:system-ui,sans-serif;display:flex;min-height:100vh;
align-items:center;justify-content:center;text-align:center}}
code{{background:{THEME['panel']};padding:2px 8px;border-radius:6px}}
</style></head><body><div>
<div style="font-size:3rem">\U0001F4E1</div>
<h1>You are offline</h1>
<p>PATI runs on your PC - check that it is awake and your connection works.</p>
<p><a href="/" style="color:{THEME['teal']}">Retry the dashboard</a></p>
</div></body></html>"""


# --------------------------------------------------------------------------
# robots.txt / sitemap.xml / llms.txt / manifest / service worker
# --------------------------------------------------------------------------
def robots_txt() -> str:
    return ("# PATI is a private, personal dashboard.\n"
            "# It is not a public website and does not want search traffic.\n"
            "User-agent: *\nDisallow: /\n")


def sitemap_xml(base: str) -> str:
    today = time.strftime("%Y-%m-%d")
    urls = "".join(
        f"<url><loc>{base}{path}</loc><lastmod>{today}</lastmod></url>"
        for path in ("/", "/faq", "/privacy"))
    return ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
            f"{urls}</urlset>\n")


def llms_txt(base: str) -> str:
    return f"""# PATI

> Personal AI Tool Infrastructure: a local-first, strictly $0 personal AI
> system. The owner's PC is the control plane; heavy jobs run on free
> compute (Kaggle free GPUs, budgeted 240 GPU-minutes/day). FREE_ONLY=true,
> MAX_SPEND=0: paid fallbacks are impossible by construction - when no free
> worker exists, jobs park in WAITING_FOR_RESOURCE.

This is a PRIVATE single-owner dashboard, not a public web service.
Search crawlers are disallowed in robots.txt; all personal API data needs a
scoped bearer token.

## Pages
- [{base}/]({base}/): live dashboard - submit jobs, watch stage progress,
  browse finished artifacts.
- [{base}/faq]({base}/faq): plain-English FAQ (install, tokens, timing).
- [{base}/privacy]({base}/privacy): what data stays local, what goes to Kaggle.
- [{base}/docs]({base}/docs): OpenAPI docs for the control plane API.

## Capabilities (all $0)
text generation, image generation/editing, text-to-video, video editing,
text-to-speech, music generation, research, coding, filesystem organization
(local, path-guarded, audit-logged).

## API conventions
- POST /api/v1/tasks {{objective, type, params}} creates a job (202).
- GET /api/v1/tasks, /api/v1/tasks/{{id}} for status and stages.
- GET /api/v1/artifacts, /api/v1/artifacts/{{id}}/content for outputs.
- Auth: Authorization: Bearer <token>. Errors use RESOURCE_UNAVAILABLE,
  QUOTA_EXCEEDED semantics - never a paid alternative.
"""


def manifest_json() -> str:
    return json.dumps({
        "id": "/",
        "name": "PATI - Personal AI",
        "short_name": "PATI",
        "description": "Your personal AI: videos, images, voice, music, "
                       "research and files - free forever.",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait-primary",
        "background_color": THEME["bg"],
        "theme_color": THEME["bg"],
        "categories": ["productivity", "utilities", "multimedia"],
        "icons": [
            {"src": "/assets/icon-192.png", "sizes": "192x192",
             "type": "image/png", "purpose": "any"},
            {"src": "/assets/icon-512.png", "sizes": "512x512",
             "type": "image/png", "purpose": "any"},
            {"src": "/assets/icon-maskable-512.png", "sizes": "512x512",
             "type": "image/png", "purpose": "maskable"},
        ],
        "shortcuts": [
            {"name": "New job", "url": "/#jobs"},
            {"name": "Gallery", "url": "/#gallery"},
        ],
    }, indent=2)


def sw_js() -> str:
    return """/* PATI service worker: offline shell, zero third-party. */
"use strict";
var CACHE = "pati-v1";
var SHELL = ["/", "/offline", "/assets/favicon-64.png",
  "/assets/icon-192.png", "/manifest.webmanifest"];
self.addEventListener("install", function(e){
  e.waitUntil(caches.open(CACHE).then(function(c){
    return c.addAll(SHELL).catch(function(){});
  }).then(function(){ return self.skipWaiting(); }));
});
self.addEventListener("activate", function(e){
  e.waitUntil(caches.keys().then(function(keys){
    return Promise.all(keys.filter(function(k){ return k !== CACHE; })
      .map(function(k){ return caches.delete(k); }));
  }).then(function(){ return self.clients.claim(); }));
});
self.addEventListener("fetch", function(e){
  var req = e.request;
  if (req.method !== "GET") return;               // never touch APIs/POSTs
  var url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // no third-party handling
  if (url.pathname.indexOf("/api/") === 0) return; // API: network only
  if (req.mode === "navigate"){
    e.respondWith(
      fetch(req).catch(function(){
        return caches.match("/").then(function(hit){
          return hit || caches.match("/offline"); });
      }));
    return;
  }
  if (url.pathname.indexOf("/assets/") === 0){
    e.respondWith(
      caches.match(req).then(function(hit){
        return hit || fetch(req).then(function(r){
          var copy = r.clone();
          caches.open(CACHE).then(function(c){ c.put(req, copy); });
          return r;
        });
      }));
  }
});
"""
