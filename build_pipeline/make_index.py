#!/usr/bin/env python3
import json, os
PKG='/home/claude/zone5pkg/Amaravati_Twins'
man=json.load(open(PKG+'/manifest.json'))
LOGO=open('/home/claude/logo_b64.txt').read().strip()
T={'pipes':sum(m['pipes'] for m in man),'mh':sum(m['manholes'] for m in man),'km':round(sum(m['length_km'] for m in man),1)}
import re as _re
def _zkey(z):
    m=_re.match(r'(\d+)(.*)',str(z));return (int(m.group(1)),m.group(2)) if m else (999,str(z))
zones=sorted(set(m['zone'] for m in man))
zlabel=' · '.join('Zone '+z for z in zones)

def side():
    s=''
    for z in zones:
        s+=f'<div class="zhead">ZONE {z}</div>'
        for i,m in enumerate(man):
            if m['zone']!=z: continue
            s+=(f'<button class="blk" data-i="{i}" data-file="{m["file"]}">'
                f'<div class="bc">{m["zone"]} · {m["block"]}</div>'
                f'<div class="bs">{m["pipes"]:,} pipes · {m["manholes"]:,} MH · {m["length_km"]} km</div>'
                f'<a class="ext" href="{m["file"]}" target="_blank" title="open in new tab">&#8599;</a></button>')
    return s

HTML=f'''<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Amaravati Zone 5 — Utility Digital Twins</title>
<style>
:root{{--bg:#060f1c;--pan:#0a1a2e;--pan2:#0c2138;--line:#1d3a57;--ink:#eaf2f9;--dim:#9bb1c6;--teal:#5fe0d2;--cy:#19C6F0;--mono:'JetBrains Mono',ui-monospace,monospace}}
*{{box-sizing:border-box}}html,body{{margin:0;height:100%}}
body{{background:var(--bg);color:var(--ink);font-family:'Inter',system-ui,Arial,sans-serif;display:flex;flex-direction:column;height:100vh;overflow:hidden}}
header{{display:flex;align-items:center;gap:18px;padding:12px 20px;border-bottom:1px solid var(--line);
  background:linear-gradient(180deg,#081b30,#07162a);position:relative}}
header::before{{content:"";position:absolute;left:0;top:0;width:100%;height:4px;background:linear-gradient(90deg,#19C6F0,#5fe0d2,#19C6F0);opacity:.6}}
.logo{{height:42px}}
.htxt b{{font-size:16px;font-weight:800;letter-spacing:.01em;color:#fff;display:block;text-shadow:0 1px 0 #c4cdd6,0 2px 3px rgba(0,0,0,.5)}}
.htxt span{{font-size:11px;color:var(--teal);letter-spacing:.14em;text-transform:uppercase}}
.sum{{margin-left:auto;display:flex;gap:10px}}
.kpi{{background:var(--pan2);border:1px solid var(--line);border-radius:8px;padding:6px 14px;text-align:center;min-width:84px}}
.kpi b{{font-family:var(--mono);font-size:17px;color:var(--cy);display:block;line-height:1.1}}
.kpi span{{font-size:9.5px;color:var(--dim);letter-spacing:.1em;text-transform:uppercase}}
.wrap{{flex:1;display:flex;min-height:0}}
.side{{width:248px;background:var(--pan);border-right:1px solid var(--line);overflow-y:auto;padding:12px 10px;flex-shrink:0}}
.zhead{{font-family:var(--mono);font-size:11px;color:var(--teal);letter-spacing:.18em;margin:12px 8px 8px}}
.blk{{position:relative;display:block;width:100%;text-align:left;background:var(--pan2);border:1px solid var(--line);
  border-radius:10px;padding:11px 13px;margin-bottom:8px;color:var(--ink);cursor:pointer;transition:.15s}}
.blk:hover{{border-color:var(--cy);transform:translateX(2px)}}
.blk.act{{border-color:var(--teal);background:#0e2c44;box-shadow:0 0 0 1px var(--teal) inset}}
.bc{{font-weight:700;font-size:14px}}
.bs{{font-size:11px;color:var(--dim);margin-top:3px;font-family:var(--mono)}}
.ext{{position:absolute;right:10px;top:10px;color:var(--dim);text-decoration:none;font-size:14px;padding:2px 5px;border-radius:5px}}
.ext:hover{{color:var(--cy);background:rgba(25,198,240,.12)}}
main{{flex:1;position:relative;min-width:0;background:#05101d}}
iframe{{width:100%;height:100%;border:0;display:block}}
.ph{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--dim);gap:10px;text-align:center;padding:20px}}
.ph svg{{width:48px;height:48px;opacity:.5}}
.foot{{font-size:10.5px;color:#6f879d;padding:6px 10px;border-top:1px solid var(--line);font-family:var(--mono)}}
</style></head>
<body>
<header>
  <img class="logo" src="data:image/png;base64,{LOGO}" alt="Kreayotoo">
  <div class="htxt"><b>Amaravati Utility Digital Twin</b><span>{zlabel} · Capital City</span></div>
  <div class="sum">
    <div class="kpi"><b>{len(man)}</b><span>Blocks</span></div>
    <div class="kpi"><b>{T['pipes']:,}</b><span>Pipes</span></div>
    <div class="kpi"><b>{T['mh']:,}</b><span>Manholes</span></div>
    <div class="kpi"><b>{T['km']}</b><span>km Network</span></div>
  </div>
</header>
<div class="wrap">
  <aside class="side">{side()}
    <div class="foot">Kreayotoo Solutions · click a block to load its twin</div>
  </aside>
  <main>
    <iframe id="fr" title="block twin"></iframe>
    <div class="ph" id="ph">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2l9 5v10l-9 5-9-5V7zM12 12l9-5M12 12v10M12 12L3 7"/></svg>
      <div>Select a block from the left to open its 3D utility twin</div>
    </div>
  </main>
</div>
<script>
const fr=document.getElementById('fr'), ph=document.getElementById('ph');
document.querySelectorAll('.blk').forEach(b=>{{
  b.addEventListener('click',e=>{{
    if(e.target.classList.contains('ext')) return;        // let the new-tab link work
    document.querySelectorAll('.blk').forEach(x=>x.classList.remove('act'));
    b.classList.add('act'); ph.style.display='none'; fr.src=b.dataset.file;
  }});
}});
// auto-open first block
const first=document.querySelector('.blk'); if(first) first.click();
</script>
</body></html>'''
open(PKG+'/index.html','w').write(HTML)
print('index.html written:', os.path.getsize(PKG+'/index.html'),'bytes ·', len(man),'blocks ·', T)
