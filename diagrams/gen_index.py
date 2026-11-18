#!/usr/bin/env python3
"""Builds diagrams/index.html: a small PDF-reader-style viewer for the ECRT block diagram and schematic sheets.

Run: python3 gen_index.py   (re-runs gen_diagrams.py's drawings, then writes index.html next to this script)

The page inlines the three SVGs and gets its data (parts, pins, nets, blocks) from the registry that gen_diagrams.py fills while
drawing, so the viewer cannot drift from the schematics. Left: pages, parts and nets lists and an info pane. Hover and click highlight
parts, pins and nets; the block diagram links into the sheets; wheel zooms, drag pans.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_diagrams as g  # noqa: E402

SHEETS = [
    ("block", "Block diagram", "ecrt_block_diagram",
     "How the parts fit together. Click a block to open it on a sheet."),
    ("control", "Control sheet", "ecrt_schematic_control",
     "Arduino Uno with the PZEM TTL side, LCD, keypad, relay-module inputs, the Raspberry Pi USB link and the 12 V / 5 V supply."),
    ("mains", "Mains sheet", "ecrt_schematic_mains",
     "Supply, PZEM voltage and CT, relay contacts, four contactors and the load connectors."),
]

# block key -> (sheet, ref) targets. Blocks without a target are software or not drawn as parts.
BLOCK_TARGETS = {
    "supply": [("mains", "J1")],
    "pzem": [("control", "U2"), ("mains", "U2"), ("mains", "CT1")],
    "contactors": [("mains", f"KM{i}") for i in range(1, 5)],
    "loads": [("mains", f"J{i}") for i in range(3, 7)],
    "uno": [("control", "U1")],
    "hmi": [("control", "U3"), ("control", "KP1")],
    "relay": [("control", "U5"), ("mains", "U5")],
    "pi": [("control", "U8")],
    "dashboard": [],
    "psu12": [("control", "J2")],
    "k7805": [("control", "U6")],
}
BLOCK_TITLES = {
    "supply": "230 V AC supply", "pzem": "PZEM-004T + CT", "contactors": "Contactors KM1-KM4",
    "loads": "Appliance channels", "uno": "Arduino Uno", "hmi": "LCD + keypad", "relay": "Relay module", "pi": "Raspberry Pi",
    "dashboard": "Dashboard", "psu12": "12 V supply", "k7805": "K7805 SMPS",
}
BLOCK_NOTES = {"dashboard": "Software only: the web dashboard is served by the Raspberry Pi and opened in a browser over Wi-Fi."}


def prep_svg(sid, text):
    """Strip the XML prolog, drop width/height so it scales, remove the global <style>, and prefix non-gid ids so the three SVGs
    can live in one document without clashing."""
    text = text[text.index("<svg"):]
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S)
    ids = set(re.findall(r'\bid="([^"]+)"', text))
    own = re.compile(r"^(part|pin|net|blk)--")
    rename = {i: f"{sid}_{i}" for i in ids if not own.match(i)}

    def sub_id(m):
        return f'id="{rename.get(m.group(1), m.group(1))}"'

    def sub_ref(m):
        return f'{m.group(1)}#{rename.get(m.group(2), m.group(2))}{m.group(3)}'

    text = re.sub(r'\bid="([^"]+)"', sub_id, text)
    text = re.sub(r'(url\()#([^)\s]+)(\))', sub_ref, text)
    text = re.sub(r'(href=")#([^"]+)(")', sub_ref, text)
    head_end = text.index(">")
    head = re.sub(r'\s(width|height)="[^"]*"', "", text[:head_end])
    head = head.replace("<svg", f'<svg class="sheet" id="svg-{sid}" preserveAspectRatio="xMidYMid meet"', 1)
    return head + text[head_end:]


def build():
    g.block_diagram()
    g.schematic_control()
    g.schematic_mains()

    parts, nets, pins = {}, {}, {}
    for sid, reg in g.SHEETS.items():
        for ref, info in reg["parts"].items():
            parts.setdefault(ref, {"sheets": {}})["sheets"][sid] = info
        pins[sid] = reg["pins"]
        for p in reg["pins"]:
            if not p["net"]:
                continue
            n = nets.setdefault(p["netkey"], {"name": p["net"], "kind": p["kind"], "sheets": {}})
            n["sheets"].setdefault(sid, []).append({"ref": p["ref"], "pin": p["pin"], "pinkey": p["pinkey"]})

    blocks = {}
    for k, label in g.BLOCKS.items():
        targets = [{"sheet": s, "ref": r} for s, r in BLOCK_TARGETS.get(k, [])]
        for t in targets:
            assert t["ref"] in g.SHEETS[t["sheet"]]["parts"], f"block {k}: {t['ref']} is not drawn on the {t['sheet']} sheet"
        blocks[k] = {"title": BLOCK_TITLES[k], "label": label, "targets": targets, "note": BLOCK_NOTES.get(k, "")}
    assert set(g.BLOCKS) == set(BLOCK_TARGETS) == set(BLOCK_TITLES), "block keys out of step between the drawing, BLOCK_TARGETS and BLOCK_TITLES"

    data = {
        "sheets": [{"id": s, "title": t, "desc": d, "png": f"{f}.png"} for s, t, f, d in SHEETS],
        "parts": parts, "nets": nets, "pins": pins, "blocks": blocks,
    }
    wraps = []
    for sid, _t, f, _d in SHEETS:
        svg = prep_svg(sid, (HERE / f"{f}.svg").read_text())
        wraps.append(f'<div class="sheetwrap" id="wrap-{sid}">{svg}</div>')

    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    html = TEMPLATE.replace("/*__DATA__*/", f"const DATA = {payload};").replace("<!--__SHEETS__-->", "\n".join(wraps))
    (HERE / "index.html").write_text(html)
    print(f"wrote {HERE / 'index.html'} ({len(html) // 1024} KB): {len(parts)} parts, {len(nets)} nets, {len(blocks)} blocks")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ECRT schematics</title>
<style>
html,body{height:100%;margin:0}
body{font:13px/1.4 sans-serif;color:#000;background:#fff;display:flex;flex-direction:column}
a{color:#00e;cursor:pointer}
[hidden]{display:none!important}
button,input{font:inherit}
#bar{display:flex;gap:6px;align-items:center;padding:3px 6px;border-bottom:1px solid #888;background:#eee;flex:none}
#bar .sp{flex:1}
#searchwrap{position:relative}
#q{width:220px}
#results{position:absolute;right:0;top:24px;width:320px;background:#fff;border:1px solid #888;display:none;max-height:300px;overflow:auto;z-index:9}
#results div{padding:2px 6px;cursor:pointer}
#results div.sel,#results div:hover{background:#cde}
#results small{color:#666;margin-left:6px}
#main{flex:1;min-height:0;display:flex}
#side{width:270px;flex:none;border-right:1px solid #888;display:flex;flex-direction:column;min-height:0}
#tabs{display:flex;border-bottom:1px solid #888;background:#eee;flex:none}
#tabs a{padding:3px 10px;color:#000;text-decoration:none;border-right:1px solid #aaa}
#tabs a.on{background:#fff;font-weight:bold}
#lists{flex:1;min-height:0;overflow:auto}
.flt{display:block;box-sizing:border-box;width:100%;border:0;border-bottom:1px solid #ccc;padding:3px 6px}
.row{padding:1px 6px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row:hover{background:#cde}
.row.on{background:#ddd}
.row small{color:#666}
.page{padding:6px;cursor:pointer;border-bottom:1px solid #ddd}
.page.on{background:#ddd}
.page img{display:block;width:100%;border:1px solid #bbb;margin-bottom:2px}
#info{flex:none;max-height:45%;overflow:auto;border-top:1px solid #888;padding:6px;background:#fafafa}
#info h2{font-size:13px;margin:0}
#info .sub{color:#555;margin-bottom:4px}
#info h4{margin:8px 0 2px;font-size:12px;color:#555}
#info table{border-collapse:collapse}
#info td{padding:0 8px 0 0;vertical-align:top}
#stage{flex:1;min-width:0;position:relative;background:#fff}
.sheetwrap{position:absolute;inset:0;display:none;touch-action:none;cursor:grab;user-select:none}
.sheetwrap.on{display:block}
.sheetwrap.drag{cursor:grabbing}
svg.sheet{width:100%;height:100%;display:block}
svg.sheet *{stroke-linejoin:round;stroke-linecap:butt}
svg.sheet g[id*="--"]{cursor:pointer}
svg.sheet [id$="axes_1"]>g{transition:opacity .12s}
svg.sheet .dim{opacity:.12}
button[aria-pressed="true"]{background:#ccc}
.hl{fill:rgba(255,122,0,.16);stroke:#ff7a00;stroke-width:2;vector-effect:non-scaling-stroke;pointer-events:none}
.hl-hov{fill:rgba(31,122,255,.12);stroke:#1f7aff;stroke-width:1.5;stroke-dasharray:5 3}
#status{flex:none;border-top:1px solid #888;background:#eee;padding:2px 6px;min-height:1.4em;color:#333}
</style>
</head>
<body>
<div id="bar">
  <button id="btn-side" title="Show or hide the sidebar (S)">Sidebar</button>
  <b id="page-title"></b>
  <span class="sp"></span>
  <button id="btn-out" title="Zoom out (-)">&minus;</button><button id="btn-in" title="Zoom in (+)">+</button><button id="btn-focus" title="Dim everything except the selected net or part (D)" aria-pressed="true">Dim others</button><button id="btn-fit" title="Fit page (F)">Fit</button><span id="zoom"></span>
  <span class="sp"></span>
  <span id="searchwrap"><input id="q" placeholder="Find part or net (/)" autocomplete="off" aria-label="Find part or net"><div id="results"></div></span>
</div>
<div id="main">
  <div id="side">
    <div id="tabs"><a data-tab="pages">Pages</a><a data-tab="parts">Parts</a><a data-tab="nets">Nets</a></div>
    <div id="lists">
      <div id="tab-pages"></div>
      <div id="tab-parts" hidden><input class="flt" data-filter="parts" placeholder="filter" aria-label="Filter parts"><div id="list-parts"></div></div>
      <div id="tab-nets" hidden><input class="flt" data-filter="nets" placeholder="filter" aria-label="Filter nets"><div id="list-nets"></div></div>
    </div>
    <div id="info"></div>
  </div>
  <div id="stage">
<!--__SHEETS__-->
  </div>
</div>
<div id="status"></div>
<script>
/*__DATA__*/
(function(){
"use strict";
const $=(s,r=document)=>r.querySelector(s);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const SHEET_IDS=DATA.sheets.map(s=>s.id), SHEET={}; DATA.sheets.forEach(s=>SHEET[s.id]=s);
let current=SHEET_IDS[0];

/* ---------- lookups built from DATA ---------- */
const pinNet={}, netPins={};
for(const sid of Object.keys(DATA.pins)){
  pinNet[sid]={}; netPins[sid]={};
  for(const p of DATA.pins[sid]){
    pinNet[sid][p.ref+"|"+p.pinkey]=p;
    if(p.netkey)(netPins[sid][p.netkey]||(netPins[sid][p.netkey]=[])).push(p);
  }
}
const partBlock={};
for(const [k,b] of Object.entries(DATA.blocks)) for(const t of b.targets) partBlock[t.sheet+"|"+t.ref]=k;
const partInfo=(ref,sid)=>{const p=DATA.parts[ref];return p.sheets[sid]||Object.values(p.sheets)[0];};
const partName=(ref,sid)=>partInfo(ref,sid).name;
const partSub=(ref,sid)=>partInfo(ref,sid).sub||"";

/* ---------- per-sheet runtime ---------- */
const S={};
function parseId(id){
  const p=id.split("--"), kind=p[0];
  if(kind==="pin")return{kind,ref:p[1],pin:p[2],key:p[1]+"|"+p[2]};
  if(kind==="part"||kind==="net"||kind==="blk")return{kind,key:p[1]};
  return null;
}
function initSheet(sid){
  const wrap=$("#wrap-"+sid), svg=wrap.querySelector("svg");
  const b=svg.viewBox.baseVal, orig={x:b.x,y:b.y,w:b.width,h:b.height};
  const idx={part:{},pin:{},net:{},blk:{}};
  svg.querySelectorAll('g[id*="--"]').forEach(g=>{const m=parseId(g.id);if(m)(idx[m.kind][m.key]||(idx[m.kind][m.key]=[])).push(g);});
  const ns="http://www.w3.org/2000/svg", ov=document.createElementNS(ns,"g");
  ov.innerHTML='<g id="ov-sel-'+sid+'"></g><g id="ov-hov-'+sid+'"></g>'; ov.setAttribute("pointer-events","none"); svg.appendChild(ov);
  S[sid]={sid,wrap,svg,orig,idx,axes:svg.querySelector('g[id$="axes_1"]'),vb:{...orig},bb:new Map(),sel:null,hovKey:"",moved:false,anim:0,ns,fitted:false};
  bind(S[sid]);
}
function bbox(s,el){
  let r=s.bb.get(el); if(r)return r;
  const b=el.getBBox(), m=s.svg.getScreenCTM().inverse().multiply(el.getScreenCTM());
  const pts=[[b.x,b.y],[b.x+b.width,b.y],[b.x,b.y+b.height],[b.x+b.width,b.y+b.height]].map(([x,y])=>{const p=new DOMPoint(x,y).matrixTransform(m);return[p.x,p.y];});
  const xs=pts.map(p=>p[0]), ys=pts.map(p=>p[1]);
  r={x:Math.min(...xs),y:Math.min(...ys),w:Math.max(...xs)-Math.min(...xs),h:Math.max(...ys)-Math.min(...ys)};
  s.bb.set(el,r); return r;
}
const union=(a,b)=>{const x=Math.min(a.x,b.x),y=Math.min(a.y,b.y);return{x,y,w:Math.max(a.x+a.w,b.x+b.w)-x,h:Math.max(a.y+a.h,b.y+b.h)-y};};
const touch=(a,b,p)=>a.x-p<=b.x+b.w&&b.x-p<=a.x+a.w&&a.y-p<=b.y+b.h&&b.y-p<=a.y+a.h;
function merge(rs,p){
  rs=rs.slice(); let again=true;
  while(again){again=false;outer:for(let i=0;i<rs.length;i++)for(let j=i+1;j<rs.length;j++)if(touch(rs[i],rs[j],p)){rs[i]=union(rs[i],rs[j]);rs.splice(j,1);again=true;break outer;}}
  return rs;
}
function rectsFor(s,item){
  if(!item)return[];
  if(item.type==="parts")return item.refs.flatMap(ref=>rectsFor(s,{type:"part",ref}));
  const els=[];
  if(item.type==="part")els.push(...(s.idx.part[item.ref]||[]));
  else if(item.type==="blk")els.push(...(s.idx.blk[item.key]||[]));
  else if(item.type==="net"){
    els.push(...(s.idx.net[item.key]||[]));
    for(const p of (netPins[s.sid]||{})[item.key]||[])els.push(...(s.idx.pin[p.ref+"|"+p.pinkey]||[]));
  }
  return merge(els.map(e=>bbox(s,e)),item.type==="net"?1.2:0).map(r=>({x:r.x-1.5,y:r.y-1.5,w:r.w+3,h:r.h+3}));
}
function draw(s,which,item){
  const g=$("#ov-"+which+"-"+s.sid); g.textContent="";
  for(const r of rectsFor(s,item)){
    const e=document.createElementNS(s.ns,"rect");
    e.setAttribute("x",r.x);e.setAttribute("y",r.y);e.setAttribute("width",r.w);e.setAttribute("height",r.h);e.setAttribute("rx",2.5);
    e.setAttribute("class","hl "+(which==="hov"?"hl-hov":"hl-sel")); g.appendChild(e);
  }
}

/* ---------- view box: pan / zoom ---------- */
const ratio=s=>(s.wrap.clientHeight||1)/(s.wrap.clientWidth||1);
function fitRect(s,r,pad){
  const k=ratio(s); let w=r.w*pad, h=r.h*pad;
  if(h/w>k)w=h/k; else h=w*k;
  return{x:r.x+r.w/2-w/2,y:r.y+r.h/2-h/2,w,h};
}
function setVB(s,vb){
  s.vb=vb; s.svg.setAttribute("viewBox",`${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
  if(s.sid===current)$("#zoom").textContent=Math.round(s.orig.w/vb.w*100)+"%";
}
function animTo(s,target){
  const from={...s.vb}, t0=performance.now(), id=++s.anim;
  (function step(t){
    if(id!==s.anim)return;
    const u=Math.min(1,(t-t0)/220), e=u<.5?2*u*u:1-Math.pow(-2*u+2,2)/2;
    setVB(s,{x:from.x+(target.x-from.x)*e,y:from.y+(target.y-from.y)*e,w:from.w+(target.w-from.w)*e,h:from.h+(target.h-from.h)*e});
    if(u<1)requestAnimationFrame(step);
  })(t0);
}
const fit=(s,animate)=>{const v=fitRect(s,s.orig,1.04);animate?animTo(s,v):setVB(s,v);};
function zoomAt(s,f,cx,cy){
  s.anim++;
  const p=new DOMPoint(cx,cy).matrixTransform(s.svg.getScreenCTM().inverse());
  const w=Math.min(s.orig.w*4,Math.max(s.orig.w/60,s.vb.w/f)), k=w/s.vb.w;
  setVB(s,{x:p.x-(p.x-s.vb.x)*k,y:p.y-(p.y-s.vb.y)*k,w,h:s.vb.h*k});
}
function zoomToRects(s,rs){
  if(!rs.length)return;
  let u=rs[0]; for(const r of rs)u=union(u,r);
  const v=fitRect(s,u,Math.max(2.6,Math.min(4,s.orig.w/Math.max(u.w,1)/2)));
  animTo(s,v.w>s.orig.w*1.04?fitRect(s,s.orig,1.04):v);
}
const scale=s=>{const r=s.svg.getBoundingClientRect();return Math.min(r.width/s.vb.w,r.height/s.vb.h);};

/* ---------- status line ---------- */
const HINT="Hover to highlight, click to select. Wheel zooms, drag pans. F fits, Esc clears, S sidebar, D dim others, PgUp/PgDn change page.";
const status=t=>{const s=S[current];$("#status").textContent=t||(s&&s.sel?"Selected: "+describe(s,s.sel):HINT);};

/* ---------- item from an event target ---------- */
function itemFrom(s,target){
  const g=target.closest&&target.closest('g[id*="--"]'); if(!g)return null;
  const m=parseId(g.id); if(!m)return null;
  if(m.kind==="part")return{type:"part",ref:m.key};
  if(m.kind==="blk")return{type:"blk",key:m.key};
  if(m.kind==="net")return{type:"net",key:m.key};
  const p=pinNet[s.sid][m.key];
  return p&&p.netkey?{type:"net",key:p.netkey,viaPin:m}:{type:"pin",ref:m.ref,pin:m.pin};
}
function describe(s,item){
  if(item.type==="parts")return item.refs.join(", ")+(item.blk?"  "+DATA.blocks[item.blk].title:"");
  if(item.type==="part")return item.ref+"  "+partName(item.ref,s.sid);
  if(item.type==="blk"){const b=DATA.blocks[item.key];return b.title+(b.targets.length?"  (click to open)":"");}
  if(item.type==="net"){const n=DATA.nets[item.key];return n.name+"  "+(netPins[s.sid][item.key]||[]).length+" pin(s)"+(item.viaPin?"  via "+item.viaPin.ref+"."+item.viaPin.pin:"");}
  return item.ref+"."+item.pin+"  not connected";
}
const sameItem=(a,b)=>!!(a&&b&&a.type===b.type&&(a.ref||a.key||a.refs.join())===(b.ref||b.key||b.refs.join()));

/* ---------- interaction on a sheet ---------- */
function bind(s){
  const {wrap}=s; let down=null;
  wrap.addEventListener("pointerdown",e=>{if(e.button!==0)return;down={x:e.clientX,y:e.clientY,vb:{...s.vb},k:scale(s)};s.moved=false;s.anim++;});
  window.addEventListener("pointermove",e=>{
    if(current!==s.sid)return;
    if(down){
      const dx=e.clientX-down.x, dy=e.clientY-down.y;
      if(!s.moved&&Math.hypot(dx,dy)>4){s.moved=true;wrap.classList.add("drag");setHover(s,null);}
      if(s.moved)setVB(s,{x:down.vb.x-dx/down.k,y:down.vb.y-dy/down.k,w:down.vb.w,h:down.vb.h});
      return;
    }
    if(!wrap.contains(e.target)){setHover(s,null);return;}
    setHover(s,itemFrom(s,e.target));
  });
  window.addEventListener("pointerup",()=>{if(down){down=null;wrap.classList.remove("drag");}});
  wrap.addEventListener("pointerleave",()=>setHover(s,null));
  wrap.addEventListener("wheel",e=>{e.preventDefault();zoomAt(s,e.deltaY<0?1.18:1/1.18,e.clientX,e.clientY);},{passive:false});
  wrap.addEventListener("click",e=>{
    if(s.moved){s.moved=false;return;}
    const it=itemFrom(s,e.target);
    if(!it){select(s.sid,null,false);return;}
    if(it.type==="blk"){
      const b=DATA.blocks[it.key];
      if(b.targets.length){                       // open the first target's sheet and highlight the block's parts on it
        const sheet=b.targets[0].sheet, refs=b.targets.filter(t=>t.sheet===sheet).map(t=>t.ref);
        nav(sheet,refs.length>1?{parts:refs.join(","),blk:it.key}:{part:refs[0],blk:it.key});
        return;
      }
    }
    select(s.sid,it,false);
  });
}
function setHover(s,it){
  const k=it?JSON.stringify(it):"";
  if(s.hovKey===k)return; s.hovKey=k;
  draw(s,"hov",it&&!sameItem(it,s.sel)?it:null);
  status(it?describe(s,it):"");
}

/* ---------- focus: dim everything except the active nets ---------- */
let focusOn=true;
try{focusOn=localStorage.getItem("ecrt.focus")!=="0";}catch(e){}
function applyFocus(s){
  const it=s.sel, kids=[...s.axes.children];
  const on=focusOn&&it&&s.sid!=="block"&&(it.type==="net"||it.type==="part"||it.type==="parts");
  if(!on){kids.forEach(c=>c.classList.remove("dim"));return;}
  const act=new Set(), add=a=>(a||[]).forEach(e=>act.add(e));
  const addNet=key=>{add(s.idx.net[key]);for(const p of netPins[s.sid][key]||[]){add(s.idx.pin[p.ref+"|"+p.pinkey]);add(s.idx.part[p.ref]);}};
  const addPart=ref=>{add(s.idx.part[ref]);for(const p of DATA.pins[s.sid])if(p.ref===ref){add(s.idx.pin[p.ref+"|"+p.pinkey]);if(p.netkey)addNet(p.netkey);}};
  if(it.type==="net")addNet(it.key); else if(it.type==="part")addPart(it.ref); else it.refs.forEach(addPart);
  kids.forEach(c=>c.classList.toggle("dim",!act.has(c)));
}
function setFocus(on){
  focusOn=on; $("#btn-focus").setAttribute("aria-pressed",String(on));
  try{localStorage.setItem("ecrt.focus",on?"1":"0");}catch(e){}
  SHEET_IDS.forEach(id=>applyFocus(S[id]));
}

/* ---------- selection + info pane ---------- */
function select(sid,item,fitWhenCleared){
  const s=S[sid]; s.sel=item; draw(s,"sel",item); draw(s,"hov",null); s.hovKey="";
  renderInfo(s); markRows(); status(""); applyFocus(s);
  const p=new URLSearchParams();
  if(item&&item.type==="part")p.set("part",item.ref); if(item&&item.type==="parts")p.set("parts",item.refs.join(",")); if(item&&item.type==="net")p.set("net",item.key); if(item&&item.type==="blk")p.set("blk",item.key);
  if(item&&item.blk&&item.type!=="blk")p.set("blk",item.blk);
  const h="#/"+sid+(p.toString()?"?"+p:""); if(location.hash!==h)history.replaceState(null,"",h);
  if(!item&&fitWhenCleared)fit(s,true);
}
const link=(txt,sid,params)=>`<a data-go="${sid}" data-params='${esc(JSON.stringify(params||{}))}'>${txt}</a>`;
function renderInfo(s){
  const sid=s.sid, it=s.sel; let h="";
  if(!it){
    h=`<h2>${esc(SHEET[sid].title)}</h2><div class="sub">${esc(SHEET[sid].desc)}</div>`;
  }else if(it.type==="blk"){
    const b=DATA.blocks[it.key];
    h+=`<h2>${esc(b.title)}</h2><div class="sub">${esc(b.label)}</div>`;
    if(b.note)h+=`<div>${esc(b.note)}</div>`;
    if(b.targets.length)h+=`<h4>Open</h4>`+b.targets.map(t=>`<div>${link(esc(t.ref),t.sheet,{part:t.ref})} on ${esc(SHEET[t.sheet].title)}</div>`).join("");
  }else if(it.type==="parts"){
    const b=it.blk?DATA.blocks[it.blk]:null;
    h+=`<h2>${esc(b?b.title:it.refs.join(", "))}</h2><div class="sub">${esc(b?b.label:"")}</div>`;
    h+=`<h4>Parts</h4>`+it.refs.map(r=>`<div>${link(esc(r),sid,{part:r})} ${esc(partName(r,sid))}</div>`).join("");
    if(b){const o=b.targets.filter(t=>t.sheet!==sid);if(o.length)h+=`<h4>Also</h4>`+o.map(t=>`<div>${link(esc(t.ref),t.sheet,{part:t.ref})} on ${esc(SHEET[t.sheet].title)}</div>`).join("");
      h+=`<div>${link("Back to the block diagram","block",{blk:it.blk})}</div>`;}
  }else if(it.type==="part"){
    const ref=it.ref;
    h+=`<h2>${esc(ref)}  ${esc(partName(ref,sid))}</h2><div class="sub">${esc(partSub(ref,sid))}</div>`;
    const os=Object.keys(DATA.parts[ref].sheets).filter(x=>x!==sid), bk=partBlock[sid+"|"+ref];
    if(os.length||bk){h+=`<div>`+os.map(o=>`Also on ${link(esc(SHEET[o].title),o,{part:ref})}. `).join("")+(bk?`In the ${link("block diagram","block",{blk:bk})}.`:"")+`</div>`;}
    const pins=DATA.pins[sid].filter(p=>p.ref===ref);
    h+=`<h4>Pins</h4><table>`+pins.map(p=>`<tr><td>${esc(p.pin)}</td><td>${p.net?link(esc(p.net),sid,{net:p.netkey}):"–"}</td></tr>`).join("")+`</table>`;
    const nb={}; for(const p of pins){if(p.kind!=="signal")continue;for(const q of netPins[sid][p.netkey]||[])if(q.ref!==ref)(nb[q.ref]||(nb[q.ref]=new Set())).add(p.net);}
    const nbk=Object.keys(nb);
    if(nbk.length)h+=`<h4>Connected to</h4>`+nbk.map(r=>`<div>${link(esc(r),sid,{part:r})} <small>${[...nb[r]].map(esc).join(", ")}</small></div>`).join("");
  }else if(it.type==="net"){
    const n=DATA.nets[it.key]; h+=`<h2>${esc(n.name)}</h2><div class="sub">${n.kind==="power"?"power rail":"signal net"}</div>`;
    for(const [ssid,list] of Object.entries(n.sheets)){
      h+=`<h4>${esc(SHEET[ssid].title)}${ssid===sid?"":" ("+link("open",ssid,{net:it.key})+")"}</h4><table>`+
        list.map(p=>`<tr><td>${link(esc(p.ref),ssid,{part:p.ref})}</td><td>${esc(p.pin)}</td><td>${esc(partName(p.ref,ssid))}</td></tr>`).join("")+`</table>`;
    }
  }else{h+=`<h2>${esc(it.ref)}.${esc(it.pin)}</h2><div class="sub">not connected</div>`;}
  $("#info").innerHTML=h;
}
$("#info").addEventListener("click",e=>{const a=e.target.closest("[data-go]");if(a)nav(a.dataset.go,JSON.parse(a.dataset.params||"{}"));});

/* ---------- routing ---------- */
function nav(view,params){
  const q=new URLSearchParams(params||{}).toString(), h="#/"+view+(q?"?"+q:"");
  if(location.hash===h)route(); else location.hash=h;
}
function show(view){
  current=view;
  for(const sid of SHEET_IDS)S[sid].wrap.classList.toggle("on",sid===view);
  $("#page-title").textContent=SHEET[view].title+"  ("+(SHEET_IDS.indexOf(view)+1)+"/"+SHEET_IDS.length+")";
  document.querySelectorAll(".page").forEach(p=>p.classList.toggle("on",p.dataset.go===view));
  status("");
}
function route(){
  const raw=location.hash.replace(/^#\/?/,""), [pth,q=""]=raw.split("?"), view=SHEET[pth]?pth:SHEET_IDS[0], params=new URLSearchParams(q);
  show(view); const s=S[view];
  requestAnimationFrame(()=>{
    if(!s.fitted){fit(s,false);s.fitted=true;}else setVB(s,s.vb);
    let item=null;
    const part=params.get("part"), parts=(params.get("parts")||"").split(",").filter(r=>r&&s.idx.part[r]), net=params.get("net"), blk=params.get("blk");
    if(parts.length>1)item={type:"parts",refs:parts,blk:DATA.blocks[blk]?blk:null};
    else if(parts.length===1||part&&s.idx.part[part])item={type:"part",ref:parts[0]||part,blk:DATA.blocks[blk]&&current!=="block"?blk:null};
    else if(net&&(s.idx.net[net]||netPins[view][net]))item={type:"net",key:net};
    else if(blk&&s.idx.blk[blk]&&view==="block")item={type:"blk",key:blk};
    s.sel=item; draw(s,"sel",item); draw(s,"hov",null); s.hovKey=""; renderInfo(s); markRows(); status(""); applyFocus(s);
    if(item)zoomToRects(s,rectsFor(s,item)); else if(params.toString()===""&&s.vb.w!==fitRect(s,s.orig,1.04).w)fit(s,true);
  });
}
window.addEventListener("hashchange",route);
const page=d=>{const i=SHEET_IDS.indexOf(current)+d;if(i>=0&&i<SHEET_IDS.length)nav(SHEET_IDS[i]);};
window.addEventListener("keydown",e=>{
  if(e.target.tagName==="INPUT")return;
  const s=S[current];
  if(e.key==="Escape")select(current,null,true);
  else if(e.key==="f"||e.key==="F")fit(s,true);
  else if(e.key==="PageDown"){page(1);e.preventDefault();}
  else if(e.key==="PageUp"){page(-1);e.preventDefault();}
  else if(e.key==="+"||e.key==="="){const r=s.wrap.getBoundingClientRect();zoomAt(s,1.25,r.left+r.width/2,r.top+r.height/2);}
  else if(e.key==="-"){const r=s.wrap.getBoundingClientRect();zoomAt(s,1/1.25,r.left+r.width/2,r.top+r.height/2);}
  else if(e.key==="s"||e.key==="S")toggleSide();
  else if(e.key==="d"||e.key==="D")setFocus(!focusOn);
  else if(e.key==="/"){e.preventDefault();$("#q").focus();}
});
window.addEventListener("resize",()=>{const s=S[current];setVB(s,fitRect(s,s.vb,1));});
function setSide(open,save){
  $("#side").hidden=!open;
  if(save){try{localStorage.setItem("ecrt.side",open?"1":"0");}catch(e){}}
  requestAnimationFrame(()=>{const s=S[current];setVB(s,fitRect(s,s.vb,1));});
}
function toggleSide(){setSide($("#side").hidden,true);}
$("#btn-side").onclick=toggleSide;
$("#btn-focus").onclick=()=>setFocus(!focusOn);
$("#btn-fit").onclick=()=>fit(S[current],true);
$("#btn-in").onclick=()=>{const s=S[current],r=s.wrap.getBoundingClientRect();zoomAt(s,1.25,r.left+r.width/2,r.top+r.height/2);};
$("#btn-out").onclick=()=>{const s=S[current],r=s.wrap.getBoundingClientRect();zoomAt(s,1/1.25,r.left+r.width/2,r.top+r.height/2);};

/* ---------- sidebar: pages, parts, nets ---------- */
$("#tab-pages").innerHTML=DATA.sheets.map((s,i)=>`<div class="page" data-go="${s.id}"><img src="${esc(s.png)}" alt=""><div>${i+1}. ${esc(s.title)}</div></div>`).join("");
$("#tab-pages").addEventListener("click",e=>{const p=e.target.closest(".page");if(p)nav(p.dataset.go);});
function setTab(t){
  document.querySelectorAll("#tabs a").forEach(a=>a.classList.toggle("on",a.dataset.tab===t));
  for(const x of ["pages","parts","nets"])$("#tab-"+x).hidden=x!==t;
}
$("#tabs").addEventListener("click",e=>{const a=e.target.closest("a[data-tab]");if(a)setTab(a.dataset.tab);});
const partRefs=Object.keys(DATA.parts).sort((a,b)=>a.localeCompare(b,undefined,{numeric:true}));
const netKeys=Object.keys(DATA.nets).sort((a,b)=>DATA.nets[a].name.localeCompare(DATA.nets[b].name,undefined,{numeric:true}));
const sheetFor=(sheets)=>sheets[current]?current:Object.keys(sheets)[0];
function renderLists(){
  const fp=($('[data-filter="parts"]').value||"").toLowerCase(), fn=($('[data-filter="nets"]').value||"").toLowerCase();
  $("#list-parts").innerHTML=partRefs.filter(r=>(r+" "+partName(r,Object.keys(DATA.parts[r].sheets)[0])).toLowerCase().includes(fp))
    .map(r=>`<div class="row" data-part="${esc(r)}"><b>${esc(r)}</b> <small>${esc(partName(r,Object.keys(DATA.parts[r].sheets)[0]))}</small></div>`).join("");
  $("#list-nets").innerHTML=netKeys.filter(k=>DATA.nets[k].name.toLowerCase().includes(fn))
    .map(k=>`<div class="row" data-net="${esc(k)}"><b>${esc(DATA.nets[k].name)}</b> <small>${DATA.nets[k].kind==="power"?"power":"signal"}</small></div>`).join("");
  markRows();
}
function markRows(){
  const s=S[current], sel=s&&s.sel;
  document.querySelectorAll("#list-parts .row").forEach(r=>r.classList.toggle("on",!!sel&&sel.type==="part"&&sel.ref===r.dataset.part));
  document.querySelectorAll("#list-nets .row").forEach(r=>r.classList.toggle("on",!!sel&&sel.type==="net"&&sel.key===r.dataset.net));
}
document.querySelectorAll("[data-filter]").forEach(i=>i.addEventListener("input",renderLists));
$("#list-parts").addEventListener("click",e=>{const r=e.target.closest(".row");if(r)nav(sheetFor(DATA.parts[r.dataset.part].sheets),{part:r.dataset.part});});
$("#list-nets").addEventListener("click",e=>{const r=e.target.closest(".row");if(r)nav(sheetFor(DATA.nets[r.dataset.net].sheets),{net:r.dataset.net});});

/* ---------- find box ---------- */
const q=$("#q"), results=$("#results"); let hits=[], hi=0;
function search(t){
  t=t.trim().toLowerCase(); if(!t)return[];
  const out=[];
  for(const r of partRefs){const n=partName(r,Object.keys(DATA.parts[r].sheets)[0]), sc=r.toLowerCase()===t?0:r.toLowerCase().startsWith(t)?1:(r+" "+n).toLowerCase().includes(t)?2:9;
    if(sc<9)out.push({sc,label:r,sub:n,go:sheetFor(DATA.parts[r].sheets),params:{part:r}});}
  for(const k of netKeys){const n=DATA.nets[k], l=n.name.toLowerCase(), sc=l===t?0:l.startsWith(t)?1:l.includes(t)?2:9;
    if(sc<9)out.push({sc:sc+.5,label:n.name,sub:n.kind+" net",go:sheetFor(n.sheets),params:{net:k}});}
  for(const [k,b] of Object.entries(DATA.blocks)){if((b.title+" "+b.label).toLowerCase().includes(t))out.push({sc:3,label:b.title,sub:"block",go:"block",params:{blk:k}});}
  return out.sort((a,b)=>a.sc-b.sc).slice(0,12);
}
function paintResults(){results.innerHTML=hits.map((h,i)=>`<div class="${i===hi?"sel":""}" data-i="${i}">${esc(h.label)}<small>${esc(h.sub)}</small></div>`).join("");results.style.display=hits.length?"block":"none";}
const pick=h=>{q.value="";hits=[];paintResults();nav(h.go,h.params);};
q.addEventListener("input",()=>{hits=search(q.value);hi=0;paintResults();});
q.addEventListener("keydown",e=>{
  if(e.key==="ArrowDown"){hi=Math.min(hits.length-1,hi+1);paintResults();e.preventDefault();}
  else if(e.key==="ArrowUp"){hi=Math.max(0,hi-1);paintResults();e.preventDefault();}
  else if(e.key==="Enter"&&hits[hi]){pick(hits[hi]);q.blur();}
  else if(e.key==="Escape"){q.value="";hits=[];paintResults();q.blur();}
});
results.addEventListener("mousedown",e=>{const d=e.target.closest("[data-i]");if(d)pick(hits[+d.dataset.i]);});
q.addEventListener("blur",()=>setTimeout(()=>{results.style.display="none";},150));

/* ---------- start ---------- */
SHEET_IDS.forEach(initSheet);
$("#btn-focus").setAttribute("aria-pressed",String(focusOn));
setTab("pages"); renderLists(); status("");
try{if(localStorage.getItem("ecrt.side")==="0")$("#side").hidden=true;}catch(e){}
route();
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    build()
