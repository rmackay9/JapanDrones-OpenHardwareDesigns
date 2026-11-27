import pcbnew, sys
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.FromMM
def net(n): return b.FindNet(n)
def track(n,layer,x0,y0,x1,y1,w=0.3):
    t=pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(mm(x0),mm(y0))); t.SetEnd(pcbnew.VECTOR2I(mm(x1),mm(y1))); t.SetWidth(mm(w)); t.SetLayer(b.GetLayerID(layer)); t.SetNet(net(n)); b.Add(t)
def via(n,x,y):
    v=pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(x),mm(y))); v.SetDrill(mm(0.3)); v.SetWidth(pcbnew.F_Cu,mm(0.6)); v.SetNet(net(n)); b.Add(v)
def zone(n,layer,x0,y0,x1,y1):
    z=pcbnew.ZONE(b); z.SetLayer(b.GetLayerID(layer)); z.SetNet(net(n)); z.SetAssignedPriority(60)
    o=z.Outline(); o.NewOutline()
    for x,y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1)): o.Append(mm(x),mm(y))
    b.Add(z)
# 1-3 edge tests (board left edge x=100.11, front edge y=50)
track('VBATT','F.Cu',100.56,95,100.56,97)          # 0.30 mm from left edge  -> expect edge violation
track('/VimDrones_mod/MVDD','In2.Cu',100.56,70,100.56,72)   # MVDD inner -> expect
track('/VimDrones_mod1/FD6288_VS2','B.Cu',150,50.45,152,50.45)  # phase 0.30 from front edge -> expect
track('+5.2V','F.Cu',100.56,90,100.56,92)          # other net at 0.30: no M6 violation expected (board rule 0.2)
# 4-7 corner tests around hole (102.61,52.5)
via('+5.2V',104.9,54.0)                              # non-GND via inside KO square, 2.7 mm from centre
track('+3V3','B.Cu',104.2,54.6,105.6,54.6)          # non-GND track in KO on B
track('+3V3','In2.Cu',104.2,55.2,105.6,55.2)        # inner layer: not covered by rule
via('GND',100.9,54.9)                                # GND via: allowed
zone('VBATT','F.Cu',104.3,50.8,105.9,52.2)          # non-GND zone fill inside KO
# zone that pokes over the edge: filler should clip to 0.5
zone('VBATT','In3.Cu',99.0,60.0,101.5,62.0)
f=pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
pcbnew.SaveBoard(sys.argv[1],b)
print('saved')
