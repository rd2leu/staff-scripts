import numpy as np
import pandas as pd
import os
import copy

## CONFIG

resolve_ties = False

# allows: None, 'up', 'stay', 'down', 'top_6'
stay = 'top_6'



## MAIN

# read back liquipedia matches section and parse it
# not super pretty but it works
with open(os.path.join('groups', 'matches.txt')) as f:
    matches = f.read()

# table of results to fill in from liquipedia
results = {}
default = {'win': [], 'tie': [], 'lose': []}
def add_result(results, team, r, opp):
    if team not in results:
        results[team] = copy.deepcopy(default) # python is by reference
    if r not in default.keys():
        raise KeyError('result r: {} is invalid}'.format(r))
    results[team][r] += [opp]

# parse liqupedia match list
weeks = matches.split('{{Matchlist')[1:]
for week in weeks:
    # look for the date of each week
    date = week.split('title=')[1].split('\n')[0].split('|')[0].rstrip('th').strip()
    for game in week.split('Match2')[1:]:
        # find team names
        teams = [t.split('}}')[0].strip() for t in game.split('TeamOpponent|')[1:]]
        # find games score
        win = [int(g[0]) - 1 for g in game.split('winner=')[1:] if g[0].isdigit()]
        if len(win) == 2:
            # only count full data
            if win[0] == win[1]:
                winner = win[0]
                loser = 1 - winner
                add_result(results, teams[winner], 'win', teams[loser])
                add_result(results, teams[loser], 'lose', teams[winner])
            else:
                add_result(results, teams[0], 'tie', teams[1])
                add_result(results, teams[1], 'tie', teams[0])

# sort results by map wins, then wins, then ties
results2 = {}
for t, res in results.items():
    results2[t] = {r: len(v) for r, v in res.items()}

data = pd.DataFrame(results2).T
data['map'] = 2 * data['win'] + 1 * data['tie'] # games are BO2
data.sort_values(['map', 'win', 'tie'], ascending = False, inplace = True)
data = data.reset_index().rename(columns = {'index': 'team'})

# leaderboard ties
reslist = data[['win', 'tie', 'lose']]
dups = reslist.duplicated(keep = False)
data['tied'] = reslist.duplicated(keep = False)

uniq = np.unique(reslist.values, axis = 0).tolist()
data['ties'] = -1
data.loc[data['tied'], 'ties'] = reslist.apply(lambda x: uniq.index(x.to_list()), axis = 1)

# get tie position on leaderboard
ties = data.groupby('ties')
tie_positions = {k: v.min() for k, v in ties.indices.items() if k != -1}
data['ties'].replace(tie_positions, inplace = True)

# sort ties by leaderboard (again, in case)
ties = data.groupby('ties')
ties = ties['team'].agg(list)
ties = ties[ties.index != -1]
ties.sort_index(inplace = True)

data['pos'] = data.index
data.loc[data['tied'], 'pos'] = data.loc[data['tied'], 'ties']

# tiebreakers
if resolve_ties == True:

    ## TODO: check head to head first

    # sum leaderboard ranks of teams above as points
    # resolve with the tied team with most points
    tiebreaker_points_factor = {
        'win': 2,
        'tie': 1,
        'lose': -1,
        }
    tbpf = tiebreaker_points_factor # name too long

    for pos, tie in ties.items():
        teams_above = data[data.index < pos]
        print(pos, teams_above)
        tb_points = {}
        for team in tie:
            points = 0

            for t in results[team]['win']:
                if t in teams_above['team'].values:
                    t_pos = data[data['team'] == t].iloc[0]['pos']
                    points += tbpf['win'] * (pos - t_pos) # always > 0

            for t in results[team]['tie']:
                if t in teams_above['team'].values:
                    t_pos = data[data['team'] == t].iloc[0]['pos']
                    points += tbpf['tie'] * (pos - t_pos)

            for t in results[team]['lose']:
                if t in teams_above['team'].values:
                    t_pos = data[data['team'] == t].iloc[0]['pos']
                    points += tbpf['lose'] * (0 + t_pos) # its negative

            tb_points[team] = points

        # tiebreaker summary table
        tbpt = pd.DataFrame({'team': tb_points.keys(), 'tbp': tb_points.values()})
        tbpt.sort_values('tbp', ascending = False, inplace = True)

        # sort out the order of teams (some might still be tied)
        resolution = []
        pts = tbpt['tbp'].values
        pts_old = pts[0]
        pts_cnt = pos
        resolution += [pts_cnt]
        for pts_new in pts[1:]:
            if pts_new == pts_old:
                pts_cnt += 1
                resolution += [resolution[-1]]
            else:
                pts_old = pts_new
                pts_cnt += 1
                resolution += [pts_cnt]
        tbpt['pos'] = resolution

        # update standings table before going to next tie
        for i, res in tbpt.iterrows():
            # sorry for ugly pandas assignment
            idx = data[data['team'] == res['team']].index
            data.loc[idx, 'pos'] = res['pos']
            data.loc[idx, 'tbp'] = res['tbp']
        data = data.sort_values('pos').reset_index(drop = True)

data['pos'] = data['pos'] + 1
print(data, end = '\n\n')

header = """==Group Standings==
{{box|start}}
{{GroupTableStart| Group Standings |width=420px|padding=2em
|lrthread=
|preview=}}
"""

footer = """{{GroupTableEnd}}
{{box|end}}
"""

out = header
for idx, row in data.iterrows():
    out += '{{GroupTableSlot|'
    out += '{} |win_m={}|tie_m={}|lose_m={}|place={}'.format(*[
        row['team'],
        row['win'], row['tie'], row['lose'],
        row['pos'],
        ])
    if stay is not None:
        if stay == 'top_6':
            if idx < 2:
                out += '|pbg=up'
            elif idx < 6:
                out += '|pbg=stay'
            else:
                out += '|pbg=down'
        else:
            out += '|pbg={}'.format(stay)
    out += '}}\n'

out += footer
print(out)
