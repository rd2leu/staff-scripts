# dota amateur leagues are run by an organizer
# ex: in RD2L EU that is volunteer staff
# orgs may organize different types of tournaments
# ex: mini, main, sidecup, shakira cup
# tournaments may have seasons, at least 1 for non-recurring
# tournaments may have divisions, at least 1
# tournaments may have regions, ex: NA and SA
# tournaments may have other grouping features, ex: Sunday or Wednesday league

import os, json
from utilities import season_info_get

## input
search = {
    'org': 'rd2l',
    'tournament': 'main', # mini main side shakira ...
    'season': '31',
    'league': 'Sunday', # Wednesday Sunday
    'division': '2',
    }

week = 1

# teams
encoding = 'utf-16'

## main

# read league info
ttag_lookup = {'main': 's', 'mini': 'm'}
tour = search['tournament'].lower()
ttag = ttag_lookup.get(tour, tour)
encoding2 = encoding.replace('-', '')

schedule_str = search['org'], ttag, search['season'], encoding2
schedule_path = os.path.join('schedule', '{}_{}{}_{}.json'.format(*schedule_str))

with open(schedule_path, encoding = encoding) as f:
    schedule_info = json.load(f)

league_id = season_info_get(
    schedule_info,
    seasons = search['season'],
    leagues = search['league']
    )['id']

schedule = season_info_get(
    schedule_info,
    seasons = search['season'],
    leagues = search['league'],
    divisions = search['division'],
    )['schedule']

matches = [s for s in schedule if s['week'] == week][0]['matches']
