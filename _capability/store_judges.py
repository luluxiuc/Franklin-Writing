# -*- coding: utf-8 -*-
"""把已回裁判的判定写入 judgeN.json。裁判5 的判定由人工转录。"""
import json, os, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = r"D:\ds harness\Fk-writing\_capability"

J1 = {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'A',8:'B',9:'A',10:'A',
      11:'A',12:'A',13:'A',14:'B',15:'A',16:'B',17:'A',18:'A'}
J1c = {1:5,2:5,3:5,4:4,5:5,6:5,7:4,8:5,9:5,10:5,11:4,12:5,13:4,14:5,15:4,16:5,17:5,18:5}

J3 = {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'B',8:'B',9:'B',10:'A',
      11:'B',12:'A',13:'B',14:'B',15:'B',16:'B',17:'A',18:'A'}
J3c = {1:4,2:5,3:5,4:3,5:5,6:5,7:4,8:4,9:4,10:5,11:4,12:5,13:4,14:4,15:3,16:5,17:5,18:5}

J5 = {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'A',8:'B',9:'A',10:'A',
      11:'A',12:'A',13:'A',14:'B',15:'A',16:'B',17:'A',18:'A'}
J5c = {1:5,2:5,3:5,4:5,5:5,6:5,7:4,8:5,9:4,10:5,11:4,12:5,13:4,14:5,15:4,16:5,17:5,18:5}

for name, V, conf in (('judge1', J1, J1c), ('judge3', J3, J3c), ('judge5', J5, J5c)):
    data = [{'no': n, 'verdict': V[n], 'confidence': conf[n], 'reason': '', 'suspect_quote': None}
            for n in sorted(V)]
    json.dump(data, open(os.path.join(B, name + '.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'写入 {name}.json')
