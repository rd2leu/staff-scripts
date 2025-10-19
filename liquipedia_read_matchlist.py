import numpy as np
import pandas as pd
import os
import pyperclip

template2 = """                            "schedule": [
{}
                            ]"""

template3 = """                                {{
                                    "week": {},
                                    "matches": [
{}
                                    ]
                                }}"""

template4 = """                                        {{
                                            "left_top": "{}",
                                            "right_bot": "{}"
                                        }}"""

# not pretty but it gets the job done
with open(os.path.join('groups', 'matches.txt')) as f:
    raw = f.read()
weeks = raw.split('{{Matchlist')

text2 = []
for w, week in enumerate(weeks[1:]):
    date = week.split('title=')[1].split('\n')[0].split('|')[0].strip()
    print(date, '2025')
    text3 = []
    for d in week.split('Match')[1:]:
        teams = [t.split('}}')[0].strip() for t in d.split('TeamOpponent|')[1:]]
        print('    (\'', teams[0], '\', \'', teams[1], '\'),', sep = '')
        text3 += [template4.format(*teams)]
    text2 += [template3.format(w + 1, ',\n'.join(text3))]
text = ',\n'.join(text2)

print(text)
pyperclip.copy(text)
print('Copied to clicpboard!')        
