# zoom.py tag net layer x0 y0 x1 y1 out.png [scale]  : net copper in red, same-layer other copper by net colour, labels
import sys, numpy as np, cv2, json, colorsys, hashlib
from cu import *
def zoom(b, net, layer, x0, y0, x1, y1, out, s=40, label=True, extra_layers=()):
    W=int((x1-x0)*s); H=int((y1-y0)*s)
    img=np.full((H,W,3),255,np.uint8)
    def P(pts): return np.round((np.asarray(pts)-[x0,y0])*s*16).astype(np.int32)
    def col(n):
        if n==net: return (60,60,230)
        if n=='GND': return (200,200,200)
        h=int(hashlib.md5(n.encode()).hexdigest()[:6],16)/0xffffff
        r,g,bb=colorsys.hsv_to_rgb(h,0.55,0.9); return (int(bb*255),int(g*255),int(r*255))
    d=b.d
    def inb(x,y,m=3): return x0-m<=x<=x1+m and y0-m<=y<=y1+m
    for z in d['zones']:
        if z['rule'] or layer not in z['fill']: continue
        for p in z['fill'][layer]:
            xs=[q[0] for q in p['o']]; ys=[q[1] for q in p['o']]
            if max(xs)<x0 or min(xs)>x1 or max(ys)<y0 or min(ys)>y1: continue
            tmp=np.zeros((H,W),np.uint8)
            cv2.fillPoly(tmp,[P(p['o'])],1,shift=4)
            if p['h']: cv2.fillPoly(tmp,[P(h) for h in p['h']],0,shift=4)
            img[tmp>0]=col(z['net'])
    labs=[]
    for t in d['tracks']:
        if t['layer']!=layer or not (inb(t['x0'],t['y0']) or inb(t['x1'],t['y1'])): continue
        c=col(t['net']); 
        if t['net']!=net and t['net']!='GND': c=tuple(int(v*0.7) for v in c)
        if 'poly' in t:
            for p in t['poly']: cv2.fillPoly(img,[P(p['o'])],c,shift=4)
        else: cv2.fillPoly(img,[P(Board.stadium(t['x0'],t['y0'],t['x1'],t['y1'],t['w']))],c,shift=4)
        if t['net'] not in (net,'GND'): labs.append(((t['x0']+t['x1'])/2,(t['y0']+t['y1'])/2,t['net'].split('/')[-1]))
    for p in d['pads']:
        if layer not in p['layers'] or not inb(p['x'],p['y'],6): continue
        for q in p['layers'][layer]:
            cv2.fillPoly(img,[P(q['o'])],col(p['net']),shift=4); cv2.polylines(img,[P(q['o'])],True,(0,0,0),1,shift=4)
        if x0<=p['x']<=x1 and y0<=p['y']<=y1: labs.append((p['x'],p['y'],p['ref']+'.'+p['num']))
    for v in d['vias']:
        if layer not in v['layers'] or not inb(v['x'],v['y']): continue
        c=P([[v['x'],v['y']]])[0]
        cv2.circle(img,tuple(int(k) for k in c),int(v['layers'][layer]['d']/2*s*16),col(v['net']),-1,shift=4)
        cv2.circle(img,tuple(int(k) for k in c),int(v['layers'][layer]['d']/2*s*16),(0,0,0),1,shift=4)
        cv2.circle(img,tuple(int(k) for k in c),int(v['drill']/2*s*16),(255,255,255),-1,shift=4)
    # outline
    o=d['outline'][0]; cv2.polylines(img,[P(o['o'])]+[P(h) for h in o['h']],True,(0,160,0),2,shift=4)
    if label:
        seen=set()
        for x,y,tx in labs:
            if not (x0<=x<=x1 and y0<=y<=y1): continue
            k=(int((x-x0)*s/50),int((y-y0)*s/14),tx)
            if k in seen: continue
            seen.add(k); cv2.putText(img,tx,(int((x-x0)*s)-10,int((y-y0)*s)+4),cv2.FONT_HERSHEY_SIMPLEX,0.38,(0,0,0),1,cv2.LINE_AA)
    # grid ticks each mm
    for xx in range(int(np.ceil(x0)),int(x1)+1):
        cv2.line(img,(int((xx-x0)*s),0),(int((xx-x0)*s),8 if xx%5 else 16),(0,0,0),1); 
        if xx%2==0: cv2.putText(img,str(xx),(int((xx-x0)*s)+2,26),cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,0,0),1)
    for yy in range(int(np.ceil(y0)),int(y1)+1):
        cv2.line(img,(0,int((yy-y0)*s)),(8 if yy%5 else 16,int((yy-y0)*s)),(0,0,0),1)
        if yy%2==0: cv2.putText(img,str(yy),(18,int((yy-y0)*s)+4),cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,0,0),1)
    cv2.imwrite(out,img)
if __name__=='__main__':
    a=sys.argv; b=Board(a[1]+'.json',res=10)
    zoom(b,a[2],a[3],float(a[4]),float(a[5]),float(a[6]),float(a[7]),a[8],int(a[9]) if len(a)>9 else 40)
