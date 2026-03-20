"""dashboard.py — Self-contained HTML dashboard generator."""
from __future__ import annotations
import json
import os
import webbrowser
from datetime import datetime

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Strava Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0d0f1a;--card:#13162a;--border:#1e2235;
  --orange:#FC4C02;--green:#22c55e;--red:#ef4444;
  --yellow:#f59e0b;--blue:#60a5fa;--purple:#a78bfa;
  --text:#e2e8f0;--muted:#64748b;--dim:#475569;
}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:14px;line-height:1.5}
.hdr{background:linear-gradient(135deg,#FC4C02 0%,#c03800 100%);padding:18px 28px;display:flex;justify-content:space-between;align-items:center}
.hdr-l h1{font-size:1.25rem;font-weight:700;letter-spacing:-.01em}
.hdr-l p{font-size:.8rem;opacity:.85;margin-top:2px}
.hdr-r{font-size:.75rem;text-align:right;opacity:.8}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;padding:20px;max-width:1380px;margin:0 auto}
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;min-width:0}
.ct{font-size:.65rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}
.s1{grid-column:span 1}.s2{grid-column:span 2}.s3{grid-column:span 3}.s4{grid-column:span 4}
.sv{font-size:2.2rem;font-weight:700;color:var(--orange);line-height:1.1}
.sl{font-size:.75rem;color:var(--muted);margin-top:4px}
.ss{font-size:.8rem;color:var(--text);margin-top:2px;opacity:.7}
.badge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:.7rem;font-weight:700;letter-spacing:.05em;margin-bottom:10px}
.b-fresh{background:#14532d33;color:#4ade80;border:1px solid #166534}
.b-neutral{background:#78350f33;color:#fbbf24;border:1px solid #92400e}
.b-tired{background:#7c2d1233;color:#fb923c;border:1px solid #9a3412}
.b-overreached{background:#7f1d1d33;color:#f87171;border:1px solid #991b1b}
.mr{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--border);font-size:.82rem}
.mr:last-child{border-bottom:none}
.mk{color:var(--muted)}.mv{font-weight:600}
.ht{width:100%;border-collapse:collapse;font-size:.8rem}
.ht th{color:var(--muted);font-weight:600;text-align:left;padding:6px 8px;border-bottom:1px solid var(--border);font-size:.65rem;text-transform:uppercase;letter-spacing:.05em}
.ht td{padding:8px 8px;border-bottom:1px solid var(--border)}
.ht tr:last-child td{border-bottom:none}
.zr{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:.8rem}
.zn{width:86px;color:var(--muted);font-size:.75rem}
.zbg{flex:1;background:var(--border);border-radius:3px;height:12px;overflow:hidden}
.zfill{height:100%;border-radius:3px}
.zpct{width:34px;text-align:right;font-weight:600;font-size:.75rem}
.vi{display:flex;gap:10px;padding:10px 12px;border-radius:8px;margin-bottom:8px;align-items:flex-start;font-size:.85rem;line-height:1.5}
.vi:last-child{margin-bottom:0}
.vc{background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.25)}
.vw{background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.25)}
.vg{background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.25)}
.vico{font-size:1rem;flex-shrink:0;margin-top:1px}
.vc .vico{color:#ef4444}.vw .vico{color:#f59e0b}.vg .vico{color:#22c55e}
.hgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.hmt{font-size:.65rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:6px}
.rbar{display:flex;align-items:center;gap:10px;margin:5px 0;font-size:.82rem}
.rbar-bg{flex:1;background:var(--border);border-radius:3px;height:10px;overflow:hidden}
.rbar-fill{height:100%;border-radius:3px;transition:width .6s ease}
.green{color:#22c55e}.red{color:#ef4444}.yellow{color:#f59e0b}.orange{color:#FC4C02}.dim{color:var(--muted)}.bold{font-weight:700}
.nd{color:var(--muted);font-style:italic;font-size:.82rem}
code{background:#1e2235;padding:2px 6px;border-radius:4px;font-size:.8rem}
@media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}.s3,.s4{grid-column:span 2}}
</style>
</head>
<body>
<header class="hdr">
  <div class="hdr-l"><h1>&#9889; Strava Fitness Dashboard</h1><p id="hdr-name"></p></div>
  <div class="hdr-r" id="hdr-meta"></div>
</header>
<div class="grid">
  <div class="card s1"><div class="ct">Total Distance</div><div class="sv" id="sv-dist"></div><div class="sl">kilometers</div></div>
  <div class="card s1"><div class="ct">Moving Time</div><div class="sv" id="sv-time"></div><div class="sl">hours &amp; minutes</div></div>
  <div class="card s1"><div class="ct">Activities</div><div class="sv" id="sv-acts"></div><div class="ss" id="sv-sports"></div></div>
  <div class="card s1"><div class="ct">Weekly Average</div><div class="sv" id="sv-wkm"></div><div class="ss" id="sv-wh"></div></div>
  <div class="card s3"><div class="ct">Weekly Volume &middot; 16 weeks</div><div style="position:relative;height:185px"><canvas id="ch-weekly"></canvas></div></div>
  <div class="card s1" id="form-card">
    <div class="ct">Current Form</div>
    <div id="form-badge-el"></div>
    <div class="mr"><span class="mk">CTL &nbsp;fitness</span><span class="mv bold" id="fv-ctl"></span></div>
    <div class="mr"><span class="mk">ATL &nbsp;fatigue</span><span class="mv" id="fv-atl"></span></div>
    <div class="mr"><span class="mk">TSB &nbsp;form</span><span class="mv bold" id="fv-tsb"></span></div>
    <div class="mr"><span class="mk">CTL &Delta; 6&thinsp;wk</span><span class="mv" id="fv-delta"></span></div>
    <p id="form-msg" style="font-size:.75rem;color:var(--muted);margin-top:10px;line-height:1.4"></p>
  </div>
  <div class="card s4"><div class="ct">Training Load &middot; CTL / ATL / TSB &middot; last 90 days</div><div style="position:relative;height:200px"><canvas id="ch-load"></canvas></div></div>
  <div class="card s2"><div class="ct">Intensity Distribution</div><div id="zones-bars"></div><div id="zones-sum" style="margin-top:10px;font-size:.75rem;color:var(--muted)"></div><div id="zones-warn" style="margin-top:6px"></div></div>
  <div class="card s2"><div class="ct">Heart Rate Trends</div><div id="hr-cont"></div></div>
  <div class="card s1" id="card-run" style="display:none"><div class="ct">Running</div><div id="run-cont"></div></div>
  <div class="card s1" id="card-ride" style="display:none"><div class="ct">Cycling</div><div id="ride-cont"></div></div>
  <div class="card s1" id="card-swim" style="display:none"><div class="ct">Swimming</div><div id="swim-cont"></div></div>
  <div class="card s1"><div class="ct">Consistency</div><div id="cons-cont"></div></div>
  <div class="card s4" id="card-health"><div class="ct">Apple Health</div><div id="health-cont"></div></div>
  <div class="card s4" id="card-ha-corr"><div class="ct">Health &times; Training &mdash; Correlations</div><div id="ha-corr"></div></div>
  <div class="card s2" id="card-ha-sc"><div class="ct">Scatterplots</div><div id="ha-scatter" style="display:grid;grid-template-columns:1fr 1fr;gap:12px"></div></div>
  <div class="card s2" id="card-ha-out"><div class="ct">Outliers (last 90 days, IQR)</div><div id="ha-outliers"></div></div>
  <div class="card s4" id="card-ha-dist"><div class="ct">Metric Distributions (90 days)</div><div id="ha-dist" style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px"></div></div>
  <div class="card s4" id="card-ha-col"><div class="ct">Stress Collision Events</div><div id="ha-collide"></div></div>
  <div class="card s4" id="card-benchmarks"><div class="ct">Benchmarks &amp; Sport Readiness</div><div id="benchmarks-cont"></div></div>
  <div class="card s4"><div class="ct">Verdict</div><div id="verdict-cont"></div></div>
</div>

<script>
const D = __CHART_DATA__;

function fmtH(v){if(v==null)return '—';const h=Math.floor(v),m=Math.round((v-h)*60);return h+'h\u2009'+String(m).padStart(2,'0')+'m'}
function f1(v){return v==null?'—':v.toFixed(1)}
function sgn(v){return v>0?'+':''}
function mr(k,v){return `<div class="mr"><span class="mk">${k}</span><span class="mv">${v}</span></div>`}

document.getElementById('hdr-name').textContent=D.athlete_name;
document.getElementById('hdr-meta').innerHTML='Generated '+D.generated+'<br>Last 12 months';

const ov=D.overview;
document.getElementById('sv-dist').textContent=Math.round(ov.total_km).toLocaleString('en')+' km';
document.getElementById('sv-time').textContent=fmtH(ov.total_h);
document.getElementById('sv-acts').textContent=ov.total;
document.getElementById('sv-sports').innerHTML=`<span class="green">${ov.runs} runs</span> &middot; <span class="yellow">${ov.rides} rides</span> &middot; <span style="color:var(--blue)">${ov.swims} swims</span>`;
document.getElementById('sv-wkm').textContent=f1(ov.avg_km_week)+' km';
document.getElementById('sv-wh').textContent=f1(ov.avg_h_week)+' h / week';

const ld=D.load;
const bc={fresh:'b-fresh',neutral:'b-neutral',tired:'b-tired',overreached:'b-overreached'};
const badgeEl=document.createElement('div');
badgeEl.className='badge '+(bc[ld.form_status]||'b-neutral');
badgeEl.textContent=ld.form_label;
document.getElementById('form-badge-el').appendChild(badgeEl);
const tsbC=ld.tsb>10?'green':ld.tsb<-10?'red':'yellow';
document.getElementById('fv-ctl').textContent=ld.ctl.toFixed(1);
document.getElementById('fv-atl').textContent=ld.atl.toFixed(1);
document.getElementById('fv-tsb').innerHTML=`<span class="${tsbC}">${sgn(ld.tsb)}${ld.tsb.toFixed(1)}</span>`;
const dc=ld.ctl_delta>2?'green':ld.ctl_delta<-2?'yellow':'dim';
document.getElementById('fv-delta').innerHTML=`<span class="${dc}">${sgn(ld.ctl_delta)}${ld.ctl_delta.toFixed(1)}</span>`;
document.getElementById('form-msg').textContent=ld.form_msg;

Chart.defaults.color='#64748b';
Chart.defaults.borderColor='#1e2235';
Chart.defaults.font.family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif";
Chart.defaults.font.size=11;

(function(){
  const wk=D.weekly;
  new Chart(document.getElementById('ch-weekly'),{
    type:'bar',
    data:{
      labels:wk.labels,
      datasets:[
        {label:'km',data:wk.km,backgroundColor:wk.km.map((_,i)=>i===15?'#FC4C02':'#FC4C0255'),
         borderColor:wk.km.map((_,i)=>i===15?'#FC4C02':'#FC4C0299'),borderWidth:1,borderRadius:3,yAxisID:'y',order:2},
        {label:'hours',data:wk.hours,type:'line',borderColor:'#60a5fa',backgroundColor:'transparent',
         borderWidth:2,pointRadius:2,pointBackgroundColor:'#60a5fa',tension:.35,yAxisID:'y2',order:1},
      ]
    },
    options:{
      responsive:true,maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{
        legend:{position:'top',align:'end',labels:{boxWidth:12}},
        tooltip:{callbacks:{label:c=>c.datasetIndex===0?` ${c.raw.toFixed(1)} km`:` ${c.raw.toFixed(1)} h`}},
      },
      scales:{
        x:{grid:{color:'#1e223555'},ticks:{maxRotation:45,minRotation:45,font:{size:10}}},
        y:{grid:{color:'#1e223555'},title:{display:true,text:'km',color:'#FC4C02'},position:'left',beginAtZero:true},
        y2:{grid:{display:false},title:{display:true,text:'h',color:'#60a5fa'},position:'right',beginAtZero:true},
      }
    }
  });
})();

(function(){
  const ls=D.load_series;
  if(!ls||!ls.dates||!ls.dates.length)return;
  new Chart(document.getElementById('ch-load'),{
    type:'line',
    data:{
      labels:ls.dates,
      datasets:[
        {label:'CTL (fitness)',data:ls.ctl,borderColor:'#22c55e',backgroundColor:'transparent',borderWidth:2,pointRadius:0,tension:.3},
        {label:'ATL (fatigue)',data:ls.atl,borderColor:'#ef4444',backgroundColor:'transparent',borderWidth:2,pointRadius:0,tension:.3},
        {label:'TSB (form)',data:ls.tsb,borderColor:'#60a5fa',backgroundColor:'#60a5fa15',borderWidth:2,pointRadius:0,tension:.3,fill:'origin'},
      ]
    },
    options:{
      responsive:true,maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{
        legend:{position:'top',align:'end',labels:{boxWidth:12}},
        tooltip:{callbacks:{label:c=>` ${c.dataset.label}: ${c.raw!=null?c.raw.toFixed(1):'—'}`}},
      },
      scales:{
        x:{grid:{color:'#1e223555'},ticks:{maxTicksLimit:12,font:{size:10}}},
        y:{grid:{color:'#1e223555'},beginAtZero:false},
      }
    }
  });
})();

(function(){
  const zd=D.zones;
  const bc=document.getElementById('zones-bars');
  if(zd.no_data){bc.innerHTML='<p class="nd">No HR data for zone analysis.</p>';return;}
  const zc={Z1:'#3b82f6',Z2:'#22c55e',Z3:'#f59e0b',Z4:'#f97316',Z5:'#ef4444'};
  const zl={Z1:'Z1 Easy',Z2:'Z2 Aerobic',Z3:'Z3 Tempo',Z4:'Z4 Threshold',Z5:'Z5 VO2max'};
  ['Z1','Z2','Z3','Z4','Z5'].forEach(z=>{
    if(!zd.zone_counts[z])return;
    const pct=zd.zone_time[z]/zd.total_z_time*100;
    const d=document.createElement('div');d.className='zr';
    d.innerHTML=`<span class="zn">${zl[z]}</span><div class="zbg"><div class="zfill" style="width:${pct}%;background:${zc[z]}"></div></div><span class="zpct" style="color:${zc[z]}">${Math.round(pct)}%</span>`;
    bc.appendChild(d);
  });
  document.getElementById('zones-sum').innerHTML=
    `<span class="green">Easy ${Math.round(zd.z1z2_pct)}%</span> &middot; <span class="yellow">Tempo ${Math.round(zd.z3_pct)}%</span> &middot; <span class="red">Hard ${Math.round(zd.z4z5_pct)}%</span><br>Optimal: ~80% easy &middot; ~5% tempo &middot; ~15% hard`;
  const wc=document.getElementById('zones-warn');
  (zd.warnings||[]).forEach(([s,m])=>{
    const p=document.createElement('p');p.style.cssText='font-size:.75rem;margin-top:4px';
    p.style.color=s==='good'?'#22c55e':'#f59e0b';p.textContent=(s==='good'?'✓ ':'⚠ ')+m;wc.appendChild(p);
  });
})();

(function(){
  const cont=document.getElementById('hr-cont');
  if(!D.hr||!D.hr.length){cont.innerHTML='<p class="nd">No HR data.</p>';return;}
  const tbl=document.createElement('table');tbl.className='ht';
  tbl.innerHTML='<thead><tr><th>Sport</th><th>Early</th><th>Recent</th><th>&Delta;</th><th>Efficiency</th></tr></thead><tbody id="hr-body"></tbody>';
  cont.appendChild(tbl);
  const body=tbl.querySelector('tbody');
  D.hr.forEach(e=>{
    const tr=document.createElement('tr');
    if(e.insufficient){
      tr.innerHTML=`<td>${e.sport}</td><td colspan="4" class="dim">&lt; 5 activities with HR</td>`;
    }else{
      const d=e.avg_hr_late-e.avg_hr_early;const dc=d<-2?'green':d>2?'red':'dim';
      const em={improving:`<span class="green">&#10003; improving (${e.eff_change.toFixed(1)}%)</span>`,
                declining:`<span class="red">&#10007; declining (${(e.eff_change>0?'+':'')+e.eff_change.toFixed(1)}%)</span>`,
                flat:`<span class="dim">&#8594; flat</span>`};
      tr.innerHTML=`<td><strong>${e.sport}</strong></td><td>${e.avg_hr_early.toFixed(0)} bpm</td><td>${e.avg_hr_late.toFixed(0)} bpm</td><td><span class="${dc}">${d>0?'+':''}${d.toFixed(0)}</span></td><td>${em[e.eff_dir]||''}</td>`;
    }
    body.appendChild(tr);
  });
})();

if(D.running){
  document.getElementById('card-run').style.display='';
  const r=D.running;const pc=r.pace_change_pct;
  const pcc=pc>2?'green':pc<-2?'red':'dim';const pcl=pc>2?'faster &#10003;':pc<-2?'slower &#10007;':'flat';
  let h=mr('Total',`${Math.round(r.total_km)} km &middot; ${r.count} runs`)+mr('Avg run',`${r.avg_km.toFixed(1)} km`)+mr('Avg long',`${r.avg_long_km.toFixed(1)} km`)+mr('Pace',r.overall_pace||'&#8212;')+mr('Pace trend',`<span class="${pcc}">${pc>0?'+':''}${pc.toFixed(1)}% ${pcl}</span>`);
  if(r.cadence!=null){const cc=r.cadence>=85?'green':'yellow';h+=mr('Cadence',`<span class="${cc}">${Math.round(r.cadence)} spm</span>`);}
  document.getElementById('run-cont').innerHTML=h;
}
if(D.cycling){
  document.getElementById('card-ride').style.display='';
  const c=D.cycling;
  let h=mr('Total',`${Math.round(c.total_km)} km &middot; ${c.count} rides`)+mr('Avg ride',`${c.avg_km.toFixed(1)} km`);
  if(c.avg_speed!=null)h+=mr('Avg speed',`${c.avg_speed.toFixed(1)} km/h`);
  if(c.avg_watts!=null)h+=mr('Avg power',`${Math.round(c.avg_watts)} W`);
  document.getElementById('ride-cont').innerHTML=h;
}
if(D.swimming){
  document.getElementById('card-swim').style.display='';
  document.getElementById('swim-cont').innerHTML=mr('Total',`${D.swimming.total_km.toFixed(1)} km &middot; ${D.swimming.count} sessions`);
}

(function(){
  const con=D.consistency;
  const awc=con.active_weeks>=10?'green':con.active_weeks>=6?'yellow':'red';
  let h=mr('Active weeks (12)',`<span class="${awc}">${con.active_weeks}/12</span>`)+mr('Longest streak',`${con.max_streak} days`);
  if(con.avg_gap!=null)h+=mr('Avg gap',`${con.avg_gap.toFixed(1)} days`);
  if(con.max_gap!=null){const mc=con.max_gap>14?'yellow':'dim';h+=mr('Max gap',`<span class="${mc}">${con.max_gap} days</span>`);}
  if(con.monotony!=null){const mc=con.monotony>2?'yellow':'dim';h+=mr('Monotony',`<span class="${mc}">${con.monotony.toFixed(2)}</span>`);}
  document.getElementById('cons-cont').innerHTML=h;
})();

(function(){
  const ah=D.apple_health;const hc=document.getElementById('health-cont');
  if(!ah){
    hc.innerHTML='<p class="nd" style="line-height:1.8">No Apple Health data found.<br>To enable: <strong>iPhone Health app &rarr; profile &rarr; Export All Health Data</strong><br>Place <code>export.zip</code> in this folder or <code>~/Downloads/</code> and re-run.</p>';
    return;
  }
  let pills='<div style="display:flex;gap:20px;flex-wrap:wrap;margin-bottom:16px">';
  const pill=(title,val,unit,col)=>`<div><div class="hmt">${title}</div><div style="font-size:1.5rem;font-weight:700;color:${col}">${val} <small style="font-size:.7rem;font-weight:400;color:var(--muted)">${unit}</small></div></div>`;
  if(ah.rhr_recent!=null){const c=ah.rhr_prior&&ah.rhr_recent>ah.rhr_prior+3?'#f59e0b':'#22c55e';pills+=pill('Resting HR',Math.round(ah.rhr_recent),'bpm',c);}
  if(ah.hrv_recent!=null){const c=ah.hrv_prior&&ah.hrv_recent<ah.hrv_prior*.85?'#f59e0b':'#22c55e';pills+=pill('HRV (SDNN)',Math.round(ah.hrv_recent),'ms',c);}
  if(ah.vo2max!=null)pills+=pill('VO2max',ah.vo2max.toFixed(1),'mL/kg/min','#60a5fa');
  if(ah.sleep_avg_h!=null){const c=ah.sleep_avg_h>=7.5?'#22c55e':ah.sleep_avg_h>=6.5?'#f59e0b':'#ef4444';pills+=pill(`Sleep (${ah.sleep_nights}d avg)`,ah.sleep_avg_h.toFixed(1),'h/night',c);}
  if(ah.sleep_avg_score!=null){const sc=ah.sleep_avg_score;const c=sc>=75?'#22c55e':sc>=55?'#f59e0b':'#ef4444';pills+=pill('Sleep Score',Math.round(sc),'/100',c);}
  if(ah.sleep_avg_deep!=null&&ah.sleep_avg_deep>0){pills+=pill('Deep Sleep',ah.sleep_avg_deep.toFixed(0),'%','#a78bfa');}
  if(ah.sleep_avg_rem!=null&&ah.sleep_avg_rem>0){pills+=pill('REM Sleep',ah.sleep_avg_rem.toFixed(0),'%','#60a5fa');}
  if(ah.sleep_avg_eff!=null&&ah.sleep_avg_eff>0){const c=ah.sleep_avg_eff>=85?'#22c55e':'#f59e0b';pills+=pill('Sleep Efficiency',ah.sleep_avg_eff.toFixed(0),'%',c);}
  if(ah.weight_recent!=null)pills+=pill('Weight',ah.weight_recent.toFixed(1),'kg','#a78bfa');
  pills+='</div>';
  const ser=ah.series;let charts='';
  if(ser){
    charts='<div class="hgrid">';
    if(ser.rhr&&ser.rhr.some(v=>v!=null))charts+=`<div><div class="hmt">Resting HR (30 days)</div><div style="position:relative;height:90px"><canvas id="ch-rhr"></canvas></div></div>`;
    if(ser.hrv&&ser.hrv.some(v=>v!=null))charts+=`<div><div class="hmt">HRV SDNN (30 days)</div><div style="position:relative;height:90px"><canvas id="ch-hrv"></canvas></div></div>`;
    if(ser.sleep&&ser.sleep.some(v=>v!=null))charts+=`<div><div class="hmt">Sleep duration (30 nights)</div><div style="position:relative;height:90px"><canvas id="ch-sleep"></canvas></div></div>`;
    if(ser.sleep_score&&ser.sleep_score.some(v=>v!=null))charts+=`<div><div class="hmt">Sleep score 0–100 (30 nights)</div><div style="position:relative;height:90px"><canvas id="ch-sleepscore"></canvas></div></div>`;
    charts+='</div>';
  }
  hc.innerHTML=pills+charts;
  if(!ser)return;
  const mini=(id,data,color,type='line')=>{
    const el=document.getElementById(id);if(!el)return;
    new Chart(el,{type,data:{labels:ser.labels,datasets:[{data,borderColor:color,backgroundColor:color+'33',borderWidth:1.5,pointRadius:0,tension:.3,fill:type==='bar',borderRadius:type==='bar'?2:0}]},
      options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>` ${c.raw!=null?c.raw.toFixed(1):'—'}`}}},
        scales:{x:{grid:{display:false},ticks:{maxTicksLimit:6,font:{size:9}}},y:{grid:{color:'#1e223544'},ticks:{font:{size:9}}}}}});
  };
  mini('ch-rhr',ser.rhr,'#ef4444');
  mini('ch-hrv',ser.hrv,'#22c55e');
  mini('ch-sleep',ser.sleep,'#60a5fa','bar');
  mini('ch-sleepscore',ser.sleep_score,'#a78bfa','bar');
})();

(function(){
  const ha=D.health_analysis;
  const haCards=['card-ha-corr','card-ha-sc','card-ha-out','card-ha-dist','card-ha-col'];
  if(!ha){haCards.forEach(id=>{const el=document.getElementById(id);if(el)el.style.display='none';});return;}

  const corrEl=document.getElementById('ha-corr');
  if(ha.correlations&&ha.correlations.length){
    const tbl=document.createElement('table');tbl.className='ht';tbl.style.cssText='width:100%';
    tbl.innerHTML='<thead><tr><th>Metric A</th><th>Metric B</th><th style="text-align:center">r</th><th>Strength</th><th>Pattern</th><th>Note</th></tr></thead><tbody id="corr-body"></tbody>';
    corrEl.appendChild(tbl);
    const body=tbl.querySelector('tbody');
    ha.correlations.forEach(c=>{
      const absR=Math.abs(c.r);
      const col=absR>=0.5?(c.direction==='pos'?'#ef4444':'#60a5fa'):absR>=0.3?(c.direction==='pos'?'#f97316':'#93c5fd'):'#64748b';
      const badge=c.expected?`<span style="font-size:.65rem;padding:2px 6px;border-radius:999px;background:#14532d33;color:#4ade80;border:1px solid #166534">expected</span>`:
        `<span style="font-size:.65rem;padding:2px 6px;border-radius:999px;background:#7f1d1d33;color:#f87171;border:1px solid #991b1b">unexpected</span>`;
      const dir=c.direction==='pos'?'&#8599;':'&#8600;';
      const tr=document.createElement('tr');
      tr.innerHTML=`<td><strong>${c.x}</strong></td><td>${c.y}</td><td style="text-align:center"><span style="font-weight:700;color:${col}">${dir} ${c.r>0?'+':''}${c.r.toFixed(2)}</span></td><td><span style="color:${col}">${c.strength}</span></td><td>${badge}</td><td style="color:var(--muted);font-size:.78rem">${c.desc}</td>`;
      body.appendChild(tr);
    });
  }else{corrEl.innerHTML='<p class="nd">Insufficient paired data for correlation analysis.</p>';}

  const as=ha.aligned_series;const scCont=document.getElementById('ha-scatter');
  function makeScatter(cid,xKey,yKey,xLabel,yLabel,color){
    const wrap=document.createElement('div');
    wrap.innerHTML=`<div class="hmt">${yLabel} vs ${xLabel}</div><div style="position:relative;height:150px"><canvas id="${cid}"></canvas></div>`;
    scCont.appendChild(wrap);
    const pts=as.dates.map((_,i)=>({x:as[xKey][i],y:as[yKey][i],d:as.dates[i]})).filter(p=>p.x!=null&&p.y!=null);
    if(!pts.length)return;
    new Chart(document.getElementById(cid),{type:'scatter',data:{datasets:[{data:pts,backgroundColor:color+'55',borderColor:color,pointRadius:4,pointHoverRadius:6}]},
      options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:p=>`${p.raw.d}: (${p.raw.x}, ${p.raw.y})`}}},
        scales:{x:{grid:{color:'#1e223555'},title:{display:true,text:xLabel,color:'var(--muted)',font:{size:10}}},y:{grid:{color:'#1e223555'},title:{display:true,text:yLabel,color:'var(--muted)',font:{size:10}}}}}});
  }
  makeScatter('sc-rhr-atl','atl','rhr','ATL (fatigue)','Resting HR (bpm)','#ef4444');
  makeScatter('sc-hrv-tsb','tsb','hrv','TSB (form)','HRV SDNN (ms)','#22c55e');

  const outEl=document.getElementById('ha-outliers');
  const metaMap={rhr:{label:'Resting HR',unit:'bpm',hiGood:false},hrv:{label:'HRV',unit:'ms',hiGood:true},sleep:{label:'Sleep',unit:'h',hiGood:true},sleep_score:{label:'Sleep Score',unit:'/100',hiGood:true}};
  let outHtml='';
  Object.entries(ha.outliers).forEach(([key,items])=>{
    const meta=metaMap[key];if(!meta)return;
    if(!items.length){outHtml+=`<div class="mr"><span class="mk">${meta.label}</span><span class="dim" style="font-size:.75rem">no outliers</span></div>`;return;}
    outHtml+=`<div style="margin-bottom:10px"><div style="font-size:.72rem;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px">${meta.label}</div>`;
    items.slice(-8).forEach(o=>{
      const isHigh=o.direction==='high';const col=(isHigh===meta.hiGood)?'#22c55e':'#ef4444';const arrow=isHigh?'&#8593;':'&#8595;';
      outHtml+=`<div style="display:flex;justify-content:space-between;font-size:.78rem;padding:3px 0;border-bottom:1px solid var(--border)"><span style="color:var(--muted)">${o.date}</span><span style="color:${col};font-weight:600">${arrow} ${o.value} ${meta.unit}</span></div>`;
    });
    outHtml+='</div>';
  });
  outEl.innerHTML=outHtml||'<p class="nd">No outliers detected.</p>';

  const distCont=document.getElementById('ha-dist');
  [{key:'rhr',label:'Resting HR',unit:'bpm',color:'#ef4444'},{key:'hrv',label:'HRV (SDNN)',unit:'ms',color:'#22c55e'},{key:'sleep',label:'Sleep',unit:'h',color:'#60a5fa'},{key:'sleep_score',label:'Sleep Score',unit:'/100',color:'#a78bfa'}].forEach(({key,label,unit,color})=>{
    const dist=ha.distributions[key];const wrap=document.createElement('div');
    if(!dist){wrap.innerHTML=`<div class="hmt">${label}</div><p class="nd">No data</p>`;distCont.appendChild(wrap);return;}
    wrap.innerHTML=`<div class="hmt">${label} &mdash; <span style="color:${color}">${dist.n} days</span> &mdash; mean <span style="color:${color};font-weight:700">${dist.mean} ${unit}</span></div><div style="position:relative;height:130px"><canvas id="dist-${key}"></canvas></div>`;
    distCont.appendChild(wrap);
    const meanIdx=dist.labels.findIndex((l,i)=>{const v=parseFloat(l);return v<=dist.mean&&(i===dist.labels.length-1||parseFloat(dist.labels[i+1])>dist.mean);});
    const bgColors=dist.counts.map((_,i)=>i===meanIdx?color:color+'44');
    new Chart(document.getElementById(`dist-${key}`),{type:'bar',data:{labels:dist.labels,datasets:[{data:dist.counts,backgroundColor:bgColors,borderColor:color+'88',borderWidth:1,borderRadius:2}]},
      options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{title:([c])=>`${c.label} ${unit}`,label:c=>` ${c.raw} days`}}},
        scales:{x:{grid:{display:false},ticks:{maxTicksLimit:6,font:{size:9}}},y:{grid:{color:'#1e223544'},beginAtZero:true,ticks:{font:{size:9},precision:0}}}}});
  });

  const colEl=document.getElementById('ha-collide');
  if(!ha.collisions||!ha.collisions.length){
    colEl.innerHTML='<p class="nd">No stress collision events detected in the last 90 days.</p>';
  }else{
    let colHtml=`<p style="font-size:.75rem;color:var(--muted);margin-bottom:10px">Days where 3+ stress signals converge — high-risk for overtraining or illness.</p>`;
    ha.collisions.slice().reverse().forEach(ev=>{
      const cls=ev.severity==='critical'?'vc':'vw';const icon=ev.severity==='critical'?'&#9889;':'&#9888;';
      const sigHtml=ev.signals.map(s=>`<span style="display:inline-block;padding:2px 8px;border-radius:999px;background:#1e2235;font-size:.72rem;margin:2px">${s}</span>`).join('');
      colHtml+=`<div class="vi ${cls}" style="flex-direction:column;gap:6px"><div style="display:flex;gap:8px;align-items:center"><span class="vico">${icon}</span><strong>${ev.date}</strong><span style="font-size:.72rem;color:var(--muted)">${ev.signals.length} signals</span></div><div>${sigHtml}</div></div>`;
    });
    colEl.innerHTML=colHtml;
  }
})();

(function(){
  const bm=D.benchmarks;const sr=D.sport_recs;const cont=document.getElementById('benchmarks-cont');
  const ratingColor={Excellent:'#22c55e',Athlete:'#22c55e',Good:'#22c55e','Above Average':'#60a5fa',Average:'#f59e0b','Below Average':'#f59e0b',Poor:'#ef4444','Very Poor':'#ef4444',Fair:'#f59e0b'};
  let html='<div style="display:grid;grid-template-columns:1fr 2fr;gap:24px">';

  // Norms table
  html+='<div><div class="hmt">vs Population Norms</div>';
  if(bm&&Object.keys(bm).length){
    Object.values(bm).forEach(info=>{
      const col=ratingColor[info.rating]||'#64748b';
      html+=mr(info.label,`<span style="color:${col};font-weight:700">${info.value.toFixed(0)} ${info.unit}</span>&ensp;<span style="color:${col};font-size:.75rem">${info.rating}</span>`);
    });
  }else{html+='<p class="nd">No Apple Health data.</p>';}
  html+='</div>';

  // Sport readiness bars
  html+='<div><div class="hmt">Sport Readiness (top 5)</div>';
  if(sr&&sr.length){
    sr.forEach(rec=>{
      const r=rec.readiness;const col=r>=80?'#22c55e':r>=60?'#f59e0b':'#ef4444';
      html+=`<div class="rbar"><span style="width:160px;font-size:.8rem;color:var(--text)">${rec.label}</span><div class="rbar-bg"><div class="rbar-fill" style="width:${r}%;background:${col}"></div></div><span style="width:36px;text-align:right;font-weight:700;color:${col};font-size:.8rem">${r}%</span></div>`;
    });
    html+=`<p style="font-size:.72rem;color:var(--muted);margin-top:8px">Run <code>python analyze.py --chat</code> for detailed goal assessment</p>`;
  }else{html+='<p class="nd">No sport readiness data.</p>';}
  html+='</div></div>';
  cont.innerHTML=html;
})();

(function(){
  const vc=document.getElementById('verdict-cont');
  const ic={critical:'&#9889;',warning:'&#9888;',good:'&#10003;'};
  const cls={critical:'vi vc',warning:'vi vw',good:'vi vg'};
  D.verdict.forEach(([sev,msg])=>{
    const d=document.createElement('div');d.className=cls[sev]||'vi vg';
    d.innerHTML=`<span class="vico">${ic[sev]||'&#8226;'}</span><span>${msg}</span>`;vc.appendChild(d);
  });
})();
</script>
</body>
</html>"""


def generate_html(data: dict, athlete: dict, output_path: str = "dashboard.html") -> str:
    name = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()
    payload = {
        "athlete_name":    name,
        "generated":       datetime.now().strftime("%Y-%m-%d %H:%M"),
        "overview":        data["overview"],
        "weekly":          data["weekly"],
        "load":            data["load"],
        "load_series":     data.get("load_series", {}),
        "hr":              data["hr"],
        "zones":           data["zones"],
        "running":         data["running"],
        "cycling":         data["cycling"],
        "swimming":        data["swimming"],
        "consistency":     data["consistency"],
        "apple_health":    data["apple_health"],
        "health_analysis": data.get("health_analysis"),
        "benchmarks":      data.get("benchmarks", {}),
        "sport_recs":      data.get("sport_recs", []),
        "verdict":         data["verdict"],
    }
    html = _HTML.replace("__CHART_DATA__", json.dumps(payload, default=lambda x: None))
    with open(output_path, "w") as f:
        f.write(html)
    abs_path = os.path.abspath(output_path)
    webbrowser.open(f"file://{abs_path}")
    print(f"Dashboard → {abs_path}")
    return abs_path
