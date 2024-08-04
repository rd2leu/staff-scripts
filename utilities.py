import os, json
import pandas as pd
import numpy as np

import openpyxl
from io import BytesIO
from urllib.request import urlopen

def _partial_in(array, sub):
    for a in array:
        if sub in a:
            return True
    return False

def find_matching(array, substring, lower = True, partial = True, sep = ' '):
    """returns the index of first array element containing substring"""
    if lower:
        arr = np.array([v.lower() for v in array])
        sub = str(substring).lower()
    else:
        arr = np.array(array)
        sub = str(substring)
    idx = len(arr) # out of range
    for i, arr_item in enumerate(arr):
        split = arr_item.split(sep)
        if all([k in split for k in sub.split(sep)]):
            # all substring items were found with exact match
            idx = i
            break
    # if exact match is not found, check again for partial
    if partial and idx == len(arr):
        for i, arr_item in enumerate(arr):
            split = arr_item.split(sep)
            match = True
            for k in sub.split(sep):
                # substring may be partially in one element of array
                if not _partial_in(split, k):
                    match = False
                    break
            if match:
                idx = i
                break
    return idx

def season_info_get(info, lookup = 'name', **kwargs):
    """generic season info get, matching 'name' to **kwargs"""
    info = info.copy()
    for i, (k, v) in enumerate(kwargs.items()):
        if k not in info:
            raise NameError('level {} key \'{}\' not found'.format(i, k))
        idx = 0
        # check elements searchable
        check = True
        for item in info[k]:
            if not hasattr(item, 'keys'):
                check = False
                break
            if lookup not in item:
                check = False
                break
        if check and v is not None:
            items_lookup = [item[lookup] for item in info[k]]
            idx = find_matching(items_lookup, v)
            if idx >= len(items_lookup):
                raise KeyError({k: v})
        info = info[k][idx]
    return info

def season_info_get_teams(info, season = None, league = None, division = None, **kwargs):
    """get teams info from season info json"""
    search = {'seasons': season, 'leagues': league, 'divisions': division}
    division = season_info_get(info, **search)
    return division['teams']

def read_google_sheet(url, resolve_links = False):
    spreadsheet_id = url[url.index('/d/') + 3: url.index('/edit')]
    sheet_id = url[url.rindex('gid=') + 4:]
    export_frmt = 'https://docs.google.com/spreadsheets/d/{}/export?format={}&gid={}'
    if not resolve_links:
        export_url = export_frmt.format(spreadsheet_id, 'csv', sheet_id)
        return pd.read_csv(export_url)
    else:
        export_url = export_frmt.format(spreadsheet_id, 'xlsx', sheet_id)
        raw = BytesIO(urlopen(export_url).read())
        data = pd.read_excel(raw)
        n = len(data)
        workbook = openpyxl.load_workbook(raw)
        sheetname = workbook.sheetnames[0]
        sheet = workbook[sheetname]
        # get column names from header
        header = []
        for cell in next(sheet.rows):
            c = cell.value
            if hasattr(c, 'text'):
                c = c.text.split('"')[1] # Moggoblin's formula thing
            header += [c]
        # update dataframe with hyperlinks when found
        col_names = ['Dotabuff Link', 'Second account', 'Third account']
        for col_name in col_names:
            col_idx = header.index(col_name)
            col = next(c for i, c in enumerate(sheet.columns) if i == col_idx) # seek
            col_data = []
            for c in col:
                d = c.value
                if hasattr(c, 'hyperlink'):
                    if hasattr(c.hyperlink, 'target'):
                        # ask for permission
                        d = c.hyperlink.target
                col_data += [d]
                if len(col_data) == n + 1:
                    # no more player rows
                    break
            col_data = col_data[1:] # drop header
            data[col_name] = col_data
        data.dropna(how = 'all', inplace = True)
        return data

# find league info
if __name__ == '__main__':
        
    team_info_path = os.path.join('draft', 'rd2l_s28_utf16.json')
    with open(team_info_path, encoding = 'utf-16') as f:
        season_info = json.load(f)

    # teams in first division in first league in first season
    teams = season_info_get_teams(season_info)
    print(teams[0]['name'])

    #
    search = {
        'season': '28',
        'league': 'sun',
        'division': '2'
        }
    teams = season_info_get_teams(season_info, **search)
    print(teams[0]['name'])
