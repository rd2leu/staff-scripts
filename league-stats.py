import os, json, time
import pandas as pd
import numpy as np

import seaborn as sns
from matplotlib import pyplot as plt

from d2tools.api import get_league_matches
from utilities import datestr, datetoseconds

def pd_append(df, array):
    return pd.concat([df, pd.DataFrame([array], columns = df.columns)], ignore_index = True)

## inhouse tickets
tickets_NA = {
    'RD2L NA': [16436],
    'MD2L': [11607],
    'L2DL': [13977, 14958],
    'Outback': [17086],
    'Squeaky Clean': [13885, 17694],
    'Casual Feeder': [12920],
    'Bama': [14272, 15024, 15754, 16593],
    'Ontario': [13147],
    'The Timbits': [16823],
    'Full Effect': [14733],
    'Pepega': [16386],
    'Lyrical': [15816],
    'Pyron Flax': [13700],
}
tickets_EU = {
    'Clarity': [14090, 15265, 16567],
    'RD2L EU': [15672, 16556, 16982],
    'Chadhouse': [17134],
    'Doghouse': [13824, 14994, 16716],
    'Crimson Witnesses': [17466],
    'IGC': [13630],
    'PGC': [15510, 16149, 17693],
    'IDL': [17409],
    'LMOR': [13149],
    'Albania Dota': [15050],
    'Polish Dota': [14820, 15367, 15786, 16138, 16737],
    'Alliance Keppa Kleb': [13880, 15154],
    'Nordic': [5626],
    'The Station': [15328],
    'The chestnuts': [14162],
    'Dudes': [14445, 14677],
    'DNesTV': [13508],
    'Nest': [15887],
    '/d2g/': [16445],
}

timezone = 'CET'
start_time_str = 'March 01 2024 - 01:00'
start_time = datetoseconds(start_time_str, 'CET')
end_time_str = 'April 01 2025 - 01:00'
end_time = datetoseconds(end_time_str, 'CET')

force = False

## main

data = pd.DataFrame(columns = [
    'league_id', 'league', 'region', 'start_time', 'match_id', 'series_id',
    ])

for league, league_ids in tickets_NA.items():
    for league_id in league_ids:
        matches = get_league_matches(league_id, force = force)
        for m in matches:
            if start_time < m['start_time'] < end_time:
                d = [league_id, league, 'NA', m['start_time'], m['match_id'], m['series_id']]
                data = pd_append(data, d)

for league, league_ids in tickets_EU.items():
    for league_id in league_ids:
        matches = get_league_matches(league_id, force = force)
        for m in matches:
            if start_time < m['start_time'] < end_time:
                d = [league_id, league, 'EU', m['start_time'], m['match_id'], m['series_id']]
                data = pd_append(data, d)

# drop best-of series games
series = data[data['series_id'] != 0]
series = series[series['series_id'].duplicated(keep = False)]
data = data[~data['match_id'].isin(series['match_id'])]
data = data.drop(['series_id'], axis = 1).reset_index(drop = True)
data.to_csv('inhouse.csv', sep = ';')

# plot
frequency = '2M'

dt = pd.to_datetime(data['start_time'], unit = 's', utc = True)
data['Year'] = dt.dt.year
data['Month'] = dt.dt.month_name()
data['Date'] = dt.dt.strftime('%B %Y')
data.index = dt
data.sort_index(inplace = True)

grp = data[data['region'] == 'EU'].groupby(pd.Grouper(freq = frequency))
data2 = grp[['region', 'Date']].first()
data2['Count'] = grp['match_id'].count()

data['region'] = data['region'].fillna('NA') # sometimes NA evaluated as NaN
grp = data[data['region'] == 'NA'].groupby(pd.Grouper(freq = frequency))
data3 = grp[['region', 'Date']].first()
data3['Count'] = grp['match_id'].count()

data4 = pd.concat([data2, data3])
data4['Date'] = data4.index
data4.reset_index(inplace = True, drop = True)
data4.rename({'region': 'Region'}, axis = 1, inplace = True)

sns.set_theme(rc = {'figure.figsize': (12, 8)})
sns.lineplot(
    data = data4, x = 'Date', y = 'Count', hue = 'Region',
    linewidth = 10,
    )
plt.grid(axis = 'y')
plt.show()
