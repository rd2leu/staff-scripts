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

def schedule_get_matches(week, season = None, league = None, division = None, **kwargs):

    encoding = 'utf-16'
    org = kwargs.get('org', 'rd2l').lower()

    # read league info
    ttag_lookup = {'main': 's', 'mini': 'm'}
    tour = kwargs.get('tournament', 'main').lower()
    ttag = ttag_lookup.get(tour, tour)
    encoding2 = encoding.replace('-', '')

    schedule_str = org, ttag, season, encoding2
    schedule_path = os.path.join('schedule', '{}_{}{}_{}.json'.format(*schedule_str))

    with open(schedule_path, encoding = encoding) as f:
        schedule_info = json.load(f)

    schedule = season_info_get(
        schedule_info,
        seasons = season,
        leagues = league,
        divisions = division,
        )['schedule']

    matches = [s for s in schedule if s['week'] == week][0]['matches']
    matches = [(m['left_top'], m['right_bot']) for m in matches]

    return matches

if __name__ == '__main__':

    ## input
    search = {
        'org': 'rd2l',
        'tournament': 'main', # mini main side shakira ...
        'season': '31',
        'league': 'Sunday', # Wednesday Sunday
        'division': '2',
        }

    week = 1

    matches = schedule_get_matches(week, **search)
