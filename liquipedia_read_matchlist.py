import numpy as np
import pandas as pd
import os

# not pretty but it gets the job done
with open(os.path.join('groups', 'div1.txt'), encoding = 'utf-8') as f:
    div1 = f.read()
with open(os.path.join('groups', 'div2.txt'), encoding = 'utf-8') as f:
    div2 = f.read()
##with open(os.path.join('groups', 'div3.txt'), encoding = 'utf-8') as f:
##    div3 = f.read()
##with open(os.path.join('groups', 'wed.txt'), encoding = 'utf-8') as f:
##    wed = f.read()

##with open(os.path.join('groups', 'shakira.txt'), encoding = 'utf-8') as f:
##    shakira = f.read()

week = 2 # change this
div = div1 # and this

data = div.split('{{Matchlist')[week]
date = data.split('title=')[1].split('\n')[0].split('|')[0].rstrip('th').strip()
print(date, '2025')
#for d in data.split('Match2')[1:]:
for d in data.split('Match')[1:]:
    teams = [t.split('}}')[0].strip() for t in d.split('TeamOpponent|')[1:]]
    print('    (\'', teams[0], '\', \'', teams[1], '\'),', sep = '')
