def ishexdigit(txt):
    return all(c in '0123456789abcdef' for c in txt.lower())

def parse_account_id(txt):

    # steam stuff
    ID_0 = int('0110000100000000', 16)
    BASE = 'bcdfghjkmnpqrtvw'

    txt = txt.strip('" ')

    if txt.startswith('http://'):
        txt = 'https://' + txt[7:]

    if txt.startswith('https://'):

        txt = txt.rstrip('/')
        if txt[8:12] == 'www.':
            txt = txt[:8] + txt[12:]

        if 'players/' in txt:
            idx1 = txt.find('players/')
            for idx2 in range(idx1 + 8, len(txt)):
                if not txt[idx2].isdigit():
                    break
            return {'account': txt[idx1 + 8: idx2]}

        if 'player/' in txt:
            idx1 = txt.find('player/')
            for idx2 in range(idx1 + 7, len(txt)):
                if not txt[idx2].isdigit():
                    break
            return {'account': txt[idx1 + 7: idx2]}

        if txt.startswith('https://steamcommunity.com/id/'):
            return {'custom': txt[30:]}

        if txt.startswith('https://steamcommunity.com/user/'):
            txt = txt[32:].replace('-', '')
            hexstr = ''.join([hex(BASE.index(c))[2] for c in txt])
            return {'account': str(int(hexstr, 16))}

        if txt.startswith('https://s.team/p/'):
            txt = txt[17:].replace('-', '')
            hexstr = ''.join([hex(BASE.index(c))[2] for c in txt])
            return {'account': str(int(hexstr, 16))}

        if txt.startswith('https://steamcommunity.com/profiles/'):
            txt = txt[36:]

    if txt.startswith('[U:') and txt.endswith(']'):
        if txt[3].isdigit() and txt[5:-1].isdigit():
            return {'account': txt[5:-1]}

    if txt.startswith('STEAM_'):
        if txt[6].isdigit() and txt[8].isdigit() and txt[10:].isdigit():
            return {'account': str(int(txt[10:]) * 2 + int(txt[8]))}

    if txt.startswith('steam:') and len(txt) == 21:
        if ishexdigit(txt[6:]):
            if int(txt[6:], 16) >= ID_0:
                return {'account': str(int(txt[6:], 16) - ID_0)}

    if ishexdigit(txt):
        if len(txt) == 15:
            if int(txt, 16) >= ID_0:
                return {'account': str(int(txt, 16) - ID_0)}

    if txt.isdigit():
        if len(txt) == 17:
            if int(txt) >= ID_0:
                return {'account': str(int(txt) - ID_0)}

        if len(txt) <= 10:
            # for now steam account IDs is max 10 digits
            # unluck for dude with custom url only numbers
            return {'account': txt}

    return {'custom': txt}

if __name__ == '__main__':
    tests = [
        'https://stratz.com/player/99374795?trendsMatchCount=100',
        'https://www.dotabuff.com/esports/players/99374795-jh?team_id=8986317',
        'steam:110000105ec56cb',
        'https://steamcommunity.com/user/hvr-hjrq',
        'https://s.team/p/hvr-hjrq',
        '[U:1:99374795]',
        'STEAM_1:1:49687397',
        '76561198059640523',
        '99374795',
        ]
    results = {
        'account': '99374795',
        'custom': '',
        }

    for t in tests:
        assert(parse_account_id(t)['account'] == results['account'])

    shorts = {
        'ddc-fhjr': '35730796',
        'hgt-jcjh': '88957285',
        'crk-qgbd': '29864962',
        'fmp-ngkg': '59413620',
        'cvj-dtrt': '31862221',
        'kvj-mhkw': '132547967',
        'qmm-qpdb': '193509920',
        'fffb-ktnh': '858815893',
        'hvr-hjrq': '99374795',
        'qtm-ptnj': '198749590',
        'hqbf-gjmc': '1526941313',
        'hdp-wgqr': '86701244',
        'jjd-dgfh': '107095093',
        'hj-qp': '22202',
        'c': '1',
        'd': '2',
        'f': '3',
        'h': '5',
        'j': '6',
        'r': '12',
        'v': '14',
        'cb': '16',
        }

    for s, acc in shorts.items():
        assert(parse_account_id('https://s.team/p/' + s)['account'] == acc)
