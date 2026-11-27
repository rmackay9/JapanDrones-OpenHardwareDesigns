import json,sys
d=json.load(open(sys.argv[1]))
for v in d['violations']:
    if v['severity']=='error':
        print(v['type'], '|', ' || '.join(f"{i['description']} @({i['pos']['x']:.2f},{i['pos']['y']:.2f})" for i in v['items']))
for u in d['unconnected_items']: print('UNCONN', [i['description'] for i in u['items']])
