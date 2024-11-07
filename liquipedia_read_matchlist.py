import numpy as np
import pandas as pd
import os

with open(os.path.join('groups', 'div1.txt')) as f:
    div1 = f.read()
with open(os.path.join('groups', 'div2.txt')) as f:
    div2 = f.read()
with open(os.path.join('groups', 'div3.txt')) as f:
    div3 = f.read()
with open(os.path.join('groups', 'wed.txt')) as f:
    wed = f.read()

week = 7 # change this
div = div3 # and this

data = div.split('{{Matchlist')[week]
date = data.split('title=')[1].split('\n')[0].split('|')[0].rstrip('th').strip()
print(date, '2024')
for d in data.split('Match2')[1:]:
    teams = [t.split('}}')[0].strip() for t in d.split('TeamOpponent|')[1:]]
    print('    (\'', teams[0], '\', \'', teams[1], '\'),', sep = '')
