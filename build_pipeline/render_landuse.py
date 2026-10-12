import shapefile, json, numpy as np, os, time
from pyproj import Transformer
from PIL import Image, ImageDraw
from collections import Counter
Image.MAX_IMAGE_PIXELS=None
val2rgb={k:tuple(v) for k,v in json.load(open('landuse_colors_v2.json')).items()}
HATCH={'R1-Village planning zone':(0,0,0)}          # QML LinePatternFill, black 0.5, spacing 6
DEF=(214,214,210)
sf=shapefile.Reader('/mnt/user-data/uploads/Masterplan_Mosaic_01082025.shp')
zi=[i for i,f in enumerate([f[0] for f in sf.fields[1:]]) if f.lower()=='zoning'][0]
polys=[];allx=[];ally=[];present=Counter();miss=Counter()
for i in range(len(sf)):
    sh=sf.shape(i)
    if not sh.points: continue
    z=str(sf.record(i)[zi]).strip()
    if z and z not in val2rgb: miss[z]+=1
    col=val2rgb.get(z,DEF); present[z]+=1
    pts=sh.points; parts=list(sh.parts)+[len(pts)]; rings=[]
    for k in range(len(parts)-1):
        s,e=parts[k],parts[k+1]; base=len(allx)
        allx.extend(p[0] for p in pts[s:e]); ally.extend(p[1] for p in pts[s:e])
        rings.append((base,len(allx)))
    polys.append((rings,col,z))
print("polygons",len(polys),"| zoning without colour:",dict(miss) or "none")
allx=np.array(allx);ally=np.array(ally)
tr=Transformer.from_crs("EPSG:32644","EPSG:4326",always_xy=True)
lon,lat=tr.transform(allx,ally)
lo0,lo1,la0,la1=lon.min(),lon.max(),lat.min(),lat.max()
W=7200; H=int(round(W*(la1-la0)/(lo1-lo0)))
PX=((lon-lo0)/(lo1-lo0)*W); PY=((la1-lat)/(la1-la0)*H)
img=Image.new('RGBA',(W,H),(0,0,0,0)); dr=ImageDraw.Draw(img)
mask=Image.new('L',(W,H),0); mdr=ImageDraw.Draw(mask)
for rings,col,z in polys:
    hatch=z in HATCH
    for s,e in rings:
        if e-s<3: continue
        xy=list(zip(PX[s:e].tolist(),PY[s:e].tolist()))
        dr.polygon(xy,fill=col+(255,))
        if hatch: mdr.polygon(xy,fill=255)
# diagonal hatch, clipped to R1 plots — reproduces the QML LinePatternFill
if mask.getbbox():
    hl=Image.new('L',(W,H),0); hd=ImageDraw.Draw(hl)
    step=12
    for k in range(-H,W+H,step): hd.line([(k,0),(k+H,H)],fill=255,width=2)
    hl=Image.composite(hl,Image.new('L',(W,H),0),mask)
    img.paste(Image.new('RGBA',(W,H),(0,0,0,255)),(0,0),hl)
    print("hatch applied to R1 · mask bbox",mask.getbbox())
img.save('lu_v2.png',optimize=True)
json.dump({'bounds':[[float(la0),float(lo0)],[float(la1),float(lo1)]]},open('landuse_bounds_v2.json','w'))
NOTE={'R1-Village planning zone':'hatch','R5-Affordable / EWS Housing Zone':'assigned'}
leg=[]
for z,c in present.most_common():
    if not z or z=='None': continue
    e={'zone':z,'color':list(val2rgb.get(z,DEF)),'n':c}
    if z in HATCH: e['pat']='hatch'
    if z in NOTE and NOTE[z]=='assigned': e['note']='not in APCRDA style file'
    leg.append(e)
json.dump(leg,open('landuse_legend_v2.json','w'))
print("lu_v2.png %.2f MB · %d legend entries · %dx%d"%(os.path.getsize('lu_v2.png')/1048576,len(leg),W,H))
