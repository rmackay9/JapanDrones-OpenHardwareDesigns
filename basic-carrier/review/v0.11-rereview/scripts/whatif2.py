import pcbnew, sys
mode=sys.argv[2]; b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.FromMM; tm=pcbnew.ToMM
rm=[]
for t in b.GetTracks():
    if t.GetNetname()!='/VimDrones_mod2/FD6288_VB3': continue
    if t.GetClass()=='PCB_VIA':
        if abs(tm(t.GetPosition().x)-181.38)<0.02 and abs(tm(t.GetPosition().y)-117.91)<0.02: rm.append(t)
    else:
        xs=sorted([tm(t.GetStart().y),tm(t.GetEnd().y)])
        if abs(tm(t.GetStart().x)-181.38)<0.02 and abs(tm(t.GetEnd().x)-181.38)<0.02 and abs(xs[0]-116.25)<0.02 and abs(xs[1]-117.91)<0.02: rm.append(t)
print('removing',len(rm),[x.GetClass()+' '+x.GetLayerName() for x in rm])
for t in rm: b.Remove(t)
if mode=='D':
    for z in b.Zones():
        if not z.GetIsRuleArea() and (z.GetNetname().endswith('/MVDD') or z.GetNetname()=='VBATT'): z.SetLocalClearance(mm(0.25))
f=pcbnew.ZONE_FILLER(b); f.Fill(b.Zones()); pcbnew.SaveBoard(sys.argv[1],b); print('saved')
