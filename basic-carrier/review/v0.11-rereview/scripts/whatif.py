import pcbnew, sys
mode=sys.argv[2]; b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.FromMM; tm=pcbnew.ToMM
if mode=='A':
    for t in b.GetTracks():
        if t.GetClass()=='PCB_VIA' and abs(tm(t.GetPosition().x)-181.38)<0.02 and abs(tm(t.GetPosition().y)-117.91)<0.02:
            print('moving via',t.GetNetname()); t.SetPosition(pcbnew.VECTOR2I(mm(181.38),mm(116.75)))
else:
    for z in b.Zones():
        if not z.GetIsRuleArea() and (z.GetNetname().endswith('/MVDD') or z.GetNetname()=='VBATT'):
            z.SetLocalClearance(mm(0.25)); print('clearance 0.25:',z.GetZoneName())
f=pcbnew.ZONE_FILLER(b); f.Fill(b.Zones()); pcbnew.SaveBoard(sys.argv[1],b); print('saved')
