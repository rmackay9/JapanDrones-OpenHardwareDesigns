# KiCad python: add_via1.py board net x y [d drill]
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kutil import *
B = Board(sys.argv[1]); d = float(sys.argv[5]) if len(sys.argv) > 5 else 0.45; dr = float(sys.argv[6]) if len(sys.argv) > 6 else 0.25
B.add_via(float(sys.argv[3]), float(sys.argv[4]), sys.argv[2], d, dr); B.save(); print('via added')
