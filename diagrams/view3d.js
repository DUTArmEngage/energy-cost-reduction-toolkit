/* ---------- 3D layout page: plain boxes for the modules, wires from the schematic netlist (no libraries) ---------- */
const V3={model:null,cv:null,ctx:null,yaw:12,pitch:42,dist:1,cx:0,cy:0,sel:null,hover:null,fitted:false,drawn:[],wireHits:[],showWires:true,labels:"ref",netNames:false};
function init3d(){
  V3.model=DATA.model3d; if(!V3.model)return;
  V3.cv=$("#cv3d"); V3.ctx=V3.cv.getContext("2d");
  const bd=V3.model.board; V3.cx=bd[0]/2; V3.cy=bd[1]/2;
  const wrap=$("#wrap-view3d"); let down=null;
  wrap.addEventListener("pointerdown",e=>{if(e.button!==0&&e.button!==2)return;down={x:e.clientX,y:e.clientY,yaw:V3.yaw,pitch:V3.pitch,cx:V3.cx,cy:V3.cy,pan:e.button===2||e.shiftKey};V3.moved=false;});
  window.addEventListener("pointermove",e=>{
    if(!is3d(current))return;
    if(down){
      const dx=e.clientX-down.x, dy=e.clientY-down.y;
      if(!V3.moved&&Math.hypot(dx,dy)>4){V3.moved=true;wrap.classList.add("drag");}
      if(V3.moved){
        if(down.pan){const k=1/V3.scale, c=Math.cos(V3.yaw*Math.PI/180), s=Math.sin(V3.yaw*Math.PI/180);
          V3.cx=down.cx-(dx*c)*k; V3.cy=down.cy+(dx*s)*k+(dy*k/Math.max(.2,Math.sin(V3.pitch*Math.PI/180)))*c*0; draw3d();}
        else{V3.yaw=down.yaw+dx*.4; V3.pitch=Math.max(5,Math.min(90,down.pitch+dy*.4)); draw3d();}
      }
      return;
    }
    if(!wrap.contains(e.target)){setHover3d(null);return;}
    const r=V3.cv.getBoundingClientRect(); setHover3d(hit3d(e.clientX-r.left,e.clientY-r.top));
  });
  window.addEventListener("pointerup",()=>{if(down){down=null;wrap.classList.remove("drag");}});
  wrap.addEventListener("contextmenu",e=>e.preventDefault());
  wrap.addEventListener("pointerleave",()=>setHover3d(null));
  wrap.addEventListener("wheel",e=>{e.preventDefault();zoom3d(e.deltaY<0?1.15:1/1.15);},{passive:false});
  wrap.addEventListener("click",e=>{
    if(V3.moved){V3.moved=false;return;}
    const r=V3.cv.getBoundingClientRect(); select3d(hit3d(e.clientX-r.left,e.clientY-r.top));
  });
  $("#btn-wires").onclick=()=>{V3.showWires=!V3.showWires;$("#btn-wires").setAttribute("aria-pressed",String(V3.showWires));draw3d();};
  $("#btn-wires").setAttribute("aria-pressed","true");
  try{V3.labels=localStorage.getItem("ecrt.labels3d")||"ref";V3.netNames=localStorage.getItem("ecrt.netnames3d")==="1";}catch(e){}
  const sl=$("#sel-labels"); sl.value=V3.labels; if(sl.value!==V3.labels){V3.labels="ref";sl.value="ref";}
  sl.onchange=()=>{V3.labels=sl.value;try{localStorage.setItem("ecrt.labels3d",V3.labels);}catch(e){}draw3d();};
  $("#btn-netnames").setAttribute("aria-pressed",String(V3.netNames));
  $("#btn-netnames").onclick=()=>{V3.netNames=!V3.netNames;$("#btn-netnames").setAttribute("aria-pressed",String(V3.netNames));try{localStorage.setItem("ecrt.netnames3d",V3.netNames?"1":"0");}catch(e){}draw3d();};
  const views={top:[0,90],front:[0,12],iso:[12,42]};
  document.querySelectorAll("[data-view3d]").forEach(b=>b.onclick=()=>{[V3.yaw,V3.pitch]=views[b.dataset.view3d];draw3d();});
}
function size3d(){
  const w=$("#wrap-view3d"), dpr=window.devicePixelRatio||1, cv=V3.cv;
  cv.width=Math.max(1,w.clientWidth*dpr); cv.height=Math.max(1,w.clientHeight*dpr); cv.style.width=w.clientWidth+"px"; cv.style.height=w.clientHeight+"px";
  V3.dpr=dpr; V3.w=w.clientWidth; V3.h=w.clientHeight;
}
function fit3d(){V3.yaw=12;V3.pitch=42;V3.cx=V3.model.board[0]/2;V3.cy=V3.model.board[1]/2;V3.zoom=1;draw3d();}
function zoom3d(f){V3.zoom=Math.max(.3,Math.min(8,(V3.zoom||1)*f));draw3d();}
function resize3d(){if(!V3.model)return;size3d();draw3d();}
function proj3(p){
  const r=Math.PI/180, cyaw=Math.cos(V3.yaw*r), syaw=Math.sin(V3.yaw*r), cp=Math.cos(V3.pitch*r), sp=Math.sin(V3.pitch*r);
  const dx=p[0]-V3.cx, dy=p[1]-V3.cy, dz=p[2]-20;
  const x1=dx*cyaw-dy*syaw, y1=dx*syaw+dy*cyaw;
  return{x:V3.w/2+x1*V3.scale, y:V3.h/2+V3.hoff-(y1*sp+dz*cp)*V3.scale, d:y1*cp-dz*sp};
}
const shade3=(hex,k)=>{const n=parseInt(hex.slice(1),16);return"rgb("+[n>>16&255,n>>8&255,n&255].map(c=>Math.min(255,Math.round(c*k))).join(",")+")";};
function faces3(x,y,z,l,w,h){
  return[[[0,0,1],[[x,y,z+h],[x+l,y,z+h],[x+l,y+w,z+h],[x,y+w,z+h]],1],
         [[0,-1,0],[[x,y,z],[x+l,y,z],[x+l,y,z+h],[x,y,z+h]],.8],
         [[0,1,0],[[x,y+w,z],[x+l,y+w,z],[x+l,y+w,z+h],[x,y+w,z+h]],.7],
         [[-1,0,0],[[x,y,z],[x,y+w,z],[x,y+w,z+h],[x,y,z+h]],.9],
         [[1,0,0],[[x+l,y,z],[x+l,y+w,z],[x+l,y+w,z+h],[x+l,y,z+h]],.6]];
}
function wireColor(w){return V3.model.classes[w.cls][0];}
function related3d(){      // refs and netkeys that stay bright for the current selection
  const s=V3.sel, m=V3.model, refs=new Set(), nets=new Set();
  if(!s)return null;
  if(s.type==="net"){nets.add(s.key);for(const w of m.wires)if(w.netkey===s.key)w.ends.forEach(e=>refs.add(e[0]));}
  else{const own=s.type==="parts"?s.refs:[s.ref];own.forEach(r=>refs.add(r));for(const w of m.wires)if(w.ends.some(e=>own.includes(e[0]))){nets.add(w.netkey);w.ends.forEach(e=>refs.add(e[0]));}}
  return{refs,nets};
}
function drawWires(c,rel){   // wires lie flat on the board: drawn right after the board, so the modules cover them where they should
  V3.wireHits=[];
  if(!V3.showWires)return;
  c.lineCap="round";
  for(const w of V3.model.wires){
    const lit=!rel||rel.nets.has(w.netkey), hov=V3.hover&&V3.hover.type==="net"&&V3.hover.key===w.netkey, sel=V3.sel&&V3.sel.type==="net"&&V3.sel.key===w.netkey;
    const pts=w.path.map(proj3), lw=Math.max(1.8,1.3*V3.scale);
    c.globalAlpha=lit?1:.15; c.strokeStyle=sel?"#ff7a00":hov?"#1f7aff":wireColor(w); c.lineWidth=sel||hov?lw*1.6:lw;
    c.beginPath(); pts.forEach((q,i)=>i?c.lineTo(q.x,q.y):c.moveTo(q.x,q.y)); c.stroke(); c.globalAlpha=1;
    if(lit)for(let i=1;i<pts.length;i++)V3.wireHits.push({netkey:w.netkey,a:pts[i-1],b:pts[i]});
  }
  c.lineCap="butt";
}
function draw3d(){
  if(!V3.model||!V3.w)return;
  const m=V3.model, c=V3.ctx, bd=m.board, r=Math.PI/180;
  // scale so the board plus the tallest part fits the stage
  const diag=Math.hypot(bd[0],bd[1]); V3.hoff=0; V3.scale=Math.min(V3.w,V3.h*1.3)/(diag*1.05)*(V3.zoom||1);
  c.setTransform(V3.dpr,0,0,V3.dpr,0,0); c.clearRect(0,0,V3.w,V3.h); c.lineJoin="round";
  const rel=focusOn?related3d():null, items=[], hit=[];
  const polys=(faces,col,ref,edge)=>faces.forEach(([n,quad,k])=>{
    const cyaw=Math.cos(V3.yaw*r), syaw=Math.sin(V3.yaw*r), cp=Math.cos(V3.pitch*r), sp=Math.sin(V3.pitch*r);
    const ny1=n[0]*syaw+n[1]*cyaw; if(-ny1*cp+n[2]*sp<=1e-9)return;
    items.push({quad:quad.map(proj3),col:shade3(col,k),ref,edge});
  });
  const draws=[];
  draws.push({depth:1e9,faces:faces3(0,0,-bd[2],bd[0],bd[1],bd[2]),col:"#c8b98a",ref:null});
  for(const p of m.parts){const [l,w,h]=p.size,[x,y]=p.at; draws.push({depth:proj3([x+l/2,y+w/2,h/2]).d,faces:faces3(x,y,0,l,w,h),col:p.color,ref:p.ref});}
  draws.sort((a,b)=>b.depth-a.depth);
  V3.drawn=[];
  for(const d of draws){
    const dim=rel&&d.ref&&!rel.refs.has(d.ref); items.length=0; polys(d.faces,d.col,d.ref);
    c.globalAlpha=dim?.25:1;
    for(const it of items){
      c.beginPath(); it.quad.forEach((q,i)=>i?c.lineTo(q.x,q.y):c.moveTo(q.x,q.y)); c.closePath();
      c.fillStyle=it.col; c.fill(); c.strokeStyle="#222"; c.lineWidth=.6; c.stroke();
      if(d.ref)V3.drawn.push({ref:d.ref,quad:it.quad});
    }
    c.globalAlpha=1;
    if(!d.ref)drawWires(c,rel);
    const isSel=!!(d.ref&&V3.sel&&((V3.sel.type==="part"&&V3.sel.ref===d.ref)||(V3.sel.type==="parts"&&V3.sel.refs.includes(d.ref))));
    const act=d.ref&&(isSel||(V3.hover&&V3.hover.type==="part"&&V3.hover.ref===d.ref));
    if(act){const sel=isSel; c.strokeStyle=sel?"#ff7a00":"#1f7aff"; c.lineWidth=2.4;
      for(const it of items){c.beginPath();it.quad.forEach((q,i)=>i?c.lineTo(q.x,q.y):c.moveTo(q.x,q.y));c.closePath();c.stroke();}}
  }
  c.font="bold 11px sans-serif"; c.textAlign="center"; c.textBaseline="bottom";
  const tag=(q,text,bg,fg)=>{const tw=c.measureText(text).width; c.fillStyle=bg; c.fillRect(q.x-tw/2-2,q.y-14,tw+4,14); c.fillStyle=fg; c.fillText(text,q.x,q.y-1);};
  if(V3.labels!=="none")for(const p of m.parts){
    if(rel&&!rel.refs.has(p.ref))continue;
    const [l,w,h]=p.size,[x,y]=p.at, q=proj3([x+l/2,y+w/2,h+3]);
    const text={ref:p.ref,short:p.short,both:p.ref+" "+p.short,name:p.name,size:p.size.join("x")+" mm"}[V3.labels];
    tag(q,text,"rgba(255,255,255,.8)","#000");
  }
  if(V3.netNames&&V3.showWires){
    c.font="10px sans-serif"; const done=new Set();
    for(const w of m.wires){
      if(rel&&!rel.nets.has(w.netkey))continue;
      let best=null,bl=0; const pts=w.path.map(proj3);
      for(let i=1;i<pts.length;i++){const d=Math.hypot(pts[i].x-pts[i-1].x,pts[i].y-pts[i-1].y);if(d>bl){bl=d;best=[pts[i-1],pts[i]];}}
      if(!best||bl<28)continue;
      const k=w.netkey+"|"+Math.round(best[0].x/40)+"|"+Math.round(best[0].y/40); if(done.has(k))continue; done.add(k);
      tag({x:(best[0].x+best[1].x)/2,y:(best[0].y+best[1].y)/2+7},w.net,"rgba(255,255,230,.9)",wireColor(w));
    }
  }
  if(V3.showWires){   // legend: only the wire classes that exist
    const used=new Set(m.wires.map(w=>w.cls)), cl=Object.entries(m.classes).filter(([k])=>used.has(k));
    c.font="11px sans-serif"; c.textAlign="left"; c.textBaseline="middle";
    let y=V3.h-12-(cl.length-1)*16;
    for(const [,[col,txt]] of cl){c.fillStyle=col;c.fillRect(12,y-2,22,4);c.fillStyle="#000";c.fillText(txt,40,y);y+=16;}
  }
  $("#zoom").textContent=Math.round((V3.zoom||1)*100)+"%";
}
function inPoly(px,py,q){let ins=false;for(let i=0,j=q.length-1;i<q.length;j=i++)if((q[i].y>py)!==(q[j].y>py)&&px<(q[j].x-q[i].x)*(py-q[i].y)/(q[j].y-q[i].y)+q[i].x)ins=!ins;return ins;}
function segDist(px,py,a,b){const dx=b.x-a.x,dy=b.y-a.y,l=dx*dx+dy*dy,t=l?Math.max(0,Math.min(1,((px-a.x)*dx+(py-a.y)*dy)/l)):0;return Math.hypot(px-(a.x+t*dx),py-(a.y+t*dy));}
function hit3d(px,py){
  for(let i=V3.drawn.length-1;i>=0;i--)if(inPoly(px,py,V3.drawn[i].quad))return{type:"part",ref:V3.drawn[i].ref};
  if(V3.showWires){let best=null,bd=6;for(const s of V3.wireHits){const d=segDist(px,py,s.a,s.b);if(d<bd){bd=d;best=s;}}if(best)return{type:"net",key:best.netkey};}
  return null;
}
const part3=ref=>V3.model.parts.find(p=>p.ref===ref);
function describe3d(it){
  if(it.type==="parts")return it.refs.join(", ")+(it.blk?"  "+DATA.blocks[it.blk].title:"");
  if(it.type==="part"){const p=part3(it.ref),s=p.size;return it.ref+"  "+p.name+"  "+s[0]+" x "+s[1]+" x "+s[2]+" mm";}
  const n=DATA.nets[it.key]; return n?n.name+"  net":it.key;
}
function setHover3d(it){
  const k=it?JSON.stringify(it):""; if(V3.hoverKey===k)return; V3.hoverKey=k; V3.hover=it; draw3d();
  $("#wrap-view3d").style.cursor=it?"pointer":""; status(it?describe3d(it):"");
}
function select3d(it){
  V3.sel=it; ACTIVE=it; draw3d(); renderInfo3d(); markRows(); status("");
  const p=new URLSearchParams(); if(it&&it.type==="part")p.set("part",it.ref); if(it&&it.type==="net")p.set("net",it.key);
  const h="#/view3d"+(p.toString()?"?"+p:""); if(location.hash!==h)history.replaceState(null,"",h);
}
function renderInfo3d(){
  const it=V3.sel; let h="";
  if(it&&it.type==="parts"){
    const b=it.blk?DATA.blocks[it.blk]:null;
    h=`<h2>${esc(b?b.title:it.refs.join(", "))}</h2><div class="sub">${esc(b?b.label:"")}</div><h4>Parts</h4>`+it.refs.map(r=>`<div>${link(esc(r),"view3d",{part:r})} ${esc(part3(r).name)}</div>`).join("");
  }else if(!it){
    h=`<h2>${esc(SHEET.view3d.title)}</h2><div class="sub">${esc(SHEET.view3d.desc)}</div>
       <h4>Parts (mm, L x W x H)</h4><table>`+V3.model.parts.map(p=>`<tr><td>${link(esc(p.ref),"view3d",{part:p.ref})}</td><td>${p.size.join(" x ")}</td><td>${p.src==="listing"?"listed":"typical"}</td></tr>`).join("")+`</table>
       <div class="sub">Listed = size taken from a seller or datasheet page. Typical = common size for that kind of part: check it against your unit.</div>`+activeNote();
  }else if(it.type==="part"){
    const p=part3(it.ref), os=Object.keys(DATA.parts[it.ref].sheets);
    h=`<h2>${esc(p.ref)}  ${esc(p.name)}</h2><div class="sub">${p.size.join(" x ")} mm (L x W x H), at x ${p.at[0]}, y ${p.at[1]} on the board</div>`;
    h+=`<div>Size: ${p.src==="listing"?"from a listing":"typical, not checked"}${p.url?` (<a href="${esc(p.url)}" target="_blank" rel="noopener">source</a>)`:""}</div>`;
    h+=`<div>On the schematic: `+os.map(o=>link(esc(SHEET[o].title),o,{part:p.ref})).join(", ")+`</div>`;
    const nets={}; for(const w of V3.model.wires)if(w.ends.some(e=>e[0]===p.ref))nets[w.netkey]=w.net;
    h+=`<h4>Nets</h4>`+Object.entries(nets).map(([k,n])=>`<div>${link(esc(n),"view3d",{net:k})}</div>`).join("");
  }else{
    const n=DATA.nets[it.key]; h=`<h2>${esc(n.name)}</h2><div class="sub">${n.kind==="power"?"power rail":"signal net"}</div><h4>Connects</h4><table>`;
    const seen=new Set(); for(const w of V3.model.wires)if(w.netkey===it.key)for(const e of w.ends){const k=e.join("|");if(!seen.has(k)){seen.add(k);h+=`<tr><td>${link(esc(e[0]),"view3d",{part:e[0]})}</td><td>${esc(e[1])}</td></tr>`;}}
    h+="</table>";
  }
  $("#info").innerHTML=h;
}
function route3d(params){
  if(!V3.model)return;
  requestAnimationFrame(()=>{
    size3d(); if(!V3.fitted){V3.zoom=1;V3.fitted=true;}
    const part=params.get("part"), net=params.get("net");
    V3.sel=part&&part3(part)?{type:"part",ref:part}:net&&DATA.nets[net]?{type:"net",key:net}:null;
    if(V3.sel)ACTIVE=V3.sel; else if(!part&&!net)V3.sel=resolve(ACTIVE,"view3d");
    draw3d(); renderInfo3d(); markRows(); status("");
  });
}
