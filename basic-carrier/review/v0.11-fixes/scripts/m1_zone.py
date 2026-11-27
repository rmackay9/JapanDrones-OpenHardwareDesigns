# KiCad python: m1_zone.py board  -- review M1: In2/In3 VBATT across the rear band (y 125-140), joined to the XT90 + pin
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kutil import *
B = Board(sys.argv[1])
src = B.zone('VBATTT_STARISH')[0]
pts = [(100.61, 125.0), (147.0, 125.0), (147.0, 119.0), (155.6, 119.0), (155.6, 125.0), (190.75, 125.0),
       (190.75, 139.5), (100.61, 139.5)]
z = B.clone_zone(src, 'VBATT_REAR_INNER', ['In2.Cu', 'In3.Cu'], pts, prio=3)
print('added', z.GetZoneName(), z.GetNetname(), [B.b.GetLayerName(l) for l in z.GetLayerSet().CuStack()], z.GetAssignedPriority())
B.save()
