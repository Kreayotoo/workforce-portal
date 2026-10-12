#!/usr/bin/env python3
"""Build ONE self-contained HTML containing all block twins (no external files, works via file://)."""
import json, re, os
PKG='/home/claude/zone5pkg/Amaravati_Twins'
TEMPLATE=open('/home/claude/dashboard_template.html').read()
LOGO=open('/home/claude/logo_b64.txt').read().strip()
man=json.load(open(PKG+'/manifest.json'))

def extract_net(path):
    h=open(path).read()
    m=re.search(r'const NET\s*=\s*(\{.*?\});', h, re.S)
    return m.group(1)

def esc(s):                       # safe to embed inside a <script> as a JS string literal
    return json.dumps(s).replace('</','<\\/')

blocks=[]
for m in man:
    net=extract_net(os.path.join(PKG,m['file']))
    bn=m['block'][1:] if m['block'].startswith('B') else m['block']
    pill=f"ZONE {m['zone']} · BLOCK {bn}"
    blocks.append({'code':m['code'],'zone':m['zone'],'block':m['block'],'pill':pill,
                   'pipes':m['pipes'],'mh':m['manholes'],'km':m['length_km'],'net':net})

T={'pipes':sum(b['pipes'] for b in blocks),'mh':sum(b['mh'] for b in blocks),'km':round(sum(b['km'] for b in blocks),1)}
import re as _re
def _zkey(z):
    m=_re.match(r'(\d+)(.*)',str(z));return (int(m.group(1)),m.group(2)) if m else (999,str(z))
zones=sorted(set(b['zone'] for b in blocks),key=_zkey); zlabel=' · '.join('Zone '+z for z in zones)

# sidebar
side=''
for z in zones:
    side+=f'<div class="zhead">ZONE {z}</div>'
    for i,b in enumerate(blocks):
        if b['zone']!=z: continue
        side+=(f'<button class="blk" data-code="{b["code"]}">'
               f'<div class="bc">{b["zone"]} · {b["block"]}</div>'
               f'<div class="bs">{b["pipes"]:,} pipes · {b["mh"]:,} MH · {b["km"]} km</div></button>')

# embedded data
tpl_js=esc(TEMPLATE); logo_js=esc(LOGO)
blk_js='{'+','.join(f'{json.dumps(b["code"])}:{{net:{esc(b["net"])},pill:{json.dumps(b["pill"])}}}' for b in blocks)+'}'

HTML=f'''<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Amaravati Utility Digital Twin — Capital City</title>
<style>
:root{{--bg:#060f1c;--pan:#0a1a2e;--pan2:#0c2138;--line:#1d3a57;--ink:#eaf2f9;--dim:#9bb1c6;--teal:#5fe0d2;--cy:#19C6F0;--mono:'JetBrains Mono',ui-monospace,monospace}}
*{{box-sizing:border-box}}html,body{{margin:0;height:100%}}
body{{background:var(--bg);color:var(--ink);font-family:'Inter',system-ui,Arial,sans-serif;display:flex;flex-direction:column;height:100vh;overflow:hidden}}
header{{display:flex;align-items:center;gap:18px;padding:12px 20px;border-bottom:1px solid var(--line);background:linear-gradient(180deg,#081b30,#07162a);position:relative}}
header::before{{content:"";position:absolute;left:0;top:0;width:100%;height:4px;background:linear-gradient(90deg,#19C6F0,#5fe0d2,#19C6F0);opacity:.6}}
.logo{{height:42px}}
.htxt b{{font-size:16px;font-weight:800;color:#fff;display:block;text-shadow:0 1px 0 #c4cdd6,0 2px 3px rgba(0,0,0,.5)}}
.htxt span{{font-size:11px;color:var(--teal);letter-spacing:.13em;text-transform:uppercase}}
.sum{{margin-left:auto;display:flex;gap:10px}}
.kpi{{background:var(--pan2);border:1px solid var(--line);border-radius:8px;padding:6px 14px;text-align:center;min-width:84px}}
.kpi b{{font-family:var(--mono);font-size:17px;color:var(--cy);display:block;line-height:1.1}}
.kpi span{{font-size:9.5px;color:var(--dim);letter-spacing:.1em;text-transform:uppercase}}
.wrap{{flex:1;display:flex;min-height:0}}
.side{{width:248px;background:var(--pan);border-right:1px solid var(--line);overflow-y:auto;padding:12px 10px;flex-shrink:0}}
.zhead{{font-family:var(--mono);font-size:11px;color:var(--teal);letter-spacing:.18em;margin:12px 8px 8px}}
.blk{{display:block;width:100%;text-align:left;background:var(--pan2);border:1px solid var(--line);border-radius:10px;padding:11px 13px;margin-bottom:8px;color:var(--ink);cursor:pointer;transition:.15s}}
.blk:hover{{border-color:var(--cy);transform:translateX(2px)}}
.blk.act{{border-color:var(--teal);background:#0e2c44;box-shadow:0 0 0 1px var(--teal) inset}}
.bc{{font-weight:700;font-size:14px}}
.bs{{font-size:11px;color:var(--dim);margin-top:3px;font-family:var(--mono)}}
main{{flex:1;position:relative;min-width:0;background:#05101d}}
iframe{{width:100%;height:100%;border:0;display:block;background:#6c737b}}
.load{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--dim);font-family:var(--mono);font-size:13px;pointer-events:none;opacity:0;transition:.2s}}
.load.on{{opacity:1}}
.foot{{font-size:10.5px;color:#6f879d;padding:6px 10px;border-top:1px solid var(--line);font-family:var(--mono)}}
</style></head>
<body>
<header>
  <img class="logo" src="data:image/png;base64,{LOGO}" alt="Kreayotoo">
  <div class="htxt"><b>Amaravati Utility Digital Twin</b><span>{zlabel} · Capital City</span></div>
  <div class="sum">
    <div class="kpi"><b>{len(blocks)}</b><span>Blocks</span></div>
    <div class="kpi"><b>{T['pipes']:,}</b><span>Pipes</span></div>
    <div class="kpi"><b>{T['mh']:,}</b><span>Manholes</span></div>
    <div class="kpi"><b>{T['km']}</b><span>km Network</span></div>
  </div>
</header>
<div class="wrap">
  <aside class="side">{side}<div class="foot">Kreayotoo Solutions · all blocks embedded · one self-contained file</div></aside>
  <main><iframe id="fr" title="block twin"></iframe><div class="load" id="ld">building twin…</div></main>
</div>
<script>
const TPL={tpl_js};const LOGO={logo_js};const BLK={blk_js};
const fr=document.getElementById('fr'),ld=document.getElementById('ld');
function load(code){{
  const b=BLK[code]; if(!b) return;
  ld.classList.add('on');
  let html=TPL.split('__NETDATA__').join(b.net).split('__LOGO__').join('data:image/png;base64,'+LOGO);
  html=html.split('ZONE 1B · BLOCK 5 · GRID 44N').join(b.pill).split('Z1B-B5 (44N)').join(code+' (44N)');
  fr.onload=()=>ld.classList.remove('on');
  fr.srcdoc=html;
}}
document.querySelectorAll('.blk').forEach(btn=>btn.addEventListener('click',()=>{{
  document.querySelectorAll('.blk').forEach(x=>x.classList.remove('act'));
  btn.classList.add('act'); load(btn.dataset.code);
}}));
const first=document.querySelector('.blk'); if(first) first.click();
</script>
</body></html>'''

out='/mnt/user-data/outputs/Amaravati_Twins_AllInOne.html'
open(out,'w').write(HTML)
print('wrote',out,'·',round(os.path.getsize(out)/1024/1024,1),'MB ·',len(blocks),'blocks embedded')
print('totals:',T)
