import requests, json, time, os
import pandas as pd
import numpy as np

from d2tools.api import *
from d2tools.utilities import *
from utilities import *

from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer

## input

INPUT_PATH = 'input'
OUTPUT_PATH = 'sheets'
FNAME = 'rd2l_s30'

# match history search parameters
params = {'date': 180} # last 6 months
# TODO: put a date in the cache for opendota requests

update_mmrs = True
update_info = True
retry = True
save = True


# hero stats
hero_stats_path = os.path.join(INPUT_PATH, 'hero_stats2.csv')
hero_stats = pd.read_csv(hero_stats_path, sep = ';', index_col = 0)
def hero_name(hero_id):
    return hero_stats[hero_stats['id'] == hero_id]['localized_name'].values[0]
def hero_stat(hero_id, stat):
    return hero_stats[hero_stats['id'] == hero_id][stat].values[0]

# wordcloud
stops = set(stopwords.words('english'))
stops.update(['g', 'gg', 'gege', 'u', 'im', 'get', 'like', 'eh', 'ayy',
              'ur', 'well', 'gl', 'xd', 'ty', 'glhf', 'yes', 'no', 'hes',
              'pls', 'plz', 'yah', 'yeah', 'lol', 'go', 'got', 'also',
              'ggs', 'sry', 'ye', 'idk', 'r', 'wp', 'ggwp', 'ok', 'hf',
              'lel', 'dont', 'okay'])

## main
with open(os.path.join(INPUT_PATH, FNAME + '.json'), 'r') as f:
    rd2l = json.load(f)

for season in rd2l['seasons']:
    for league in season['leagues']:
        division = league['divisions'][0]

        if 'dsparser' not in division or division['dsparser'] < 3:
            draft = read_google_sheet(division['draftsheet'])
        else:
            # dotabuff links are now hyperlinks
            # https://github.com/pandas-dev/pandas/issues/13439
            draft = read_google_sheet(division['draftsheet'], resolve_links = True)

        draft['account_id'] = draft['Dotabuff Link'].apply(extract_account_id2)
        draft['alts'] = draft[['Second account', 'Third account']].apply(list, axis = 1).astype(str).apply(extract_account_ids)
        draft['accounts'] = draft.apply(lambda x: x['alts'] + [x['account_id']], axis = 1)
        draft = draft[draft['Activity check'] == 'Yes'].reset_index(drop = True)
        draft = draft[['Timestamp', 'Discord ID', 'Name', 'account_id', 'alts', 'accounts', 'MMR']].copy()


        cols = [
            'mmr_estimate', 'mmr_estimate_2', 'nb_solo', 'nb_matches',
            'top3_heroes', 'nb_heroes', 'versatility', 'meta',
            'pos1', 'pos2', 'pos3', 'pos4', 'pos5',
            'games_total', 'patches_played',
            'top5_words', 'key_words', 'nb_words', 'words_per_match',
            'avg_pings', 'country', 'steam_name'
            ]
        draft[cols] = None

        # average rank of last 20 solo ranked games
        for i, player in list(draft.iterrows())[:]:

            accs = player['accounts']
            print(i + 1, '/', len(draft), ':', accs)

            # join matches from all accounts, sorted by starting time
            matches = []
            for a in accs:
                matches_ = get_player_matches(a, **params, force = update_mmrs)
                if isinstance(matches_, dict) and 'error' in matches_:
                    # try again
                    # TODO: this should be in the opendota API code, not here
                    matches_ = get_player_matches(a, **params, force = retry)
                    if isinstance(matches_, dict) and 'error' in matches_:
                        # likely private profile
                        print('Error getting matches', a)
                        matches_ = []
                matches.extend(matches_)
            matches = sorted(matches, key = lambda x: x['start_time'], reverse = True)

            if len(matches) > 0:
                # estimate mmr from solo games
                solo = [m for m in matches if m['party_size'] == 1]
                mmrs = [rank2mmr(m['average_rank'], 0) for m in solo[:20]]
                if len(mmrs) >= 5 and all([m != 0 for m in mmrs]):
                    # not enough samples
                    # or unable to get mmr from medal (ex: immortal)
                    draft.loc[i, 'mmr_estimate'] = np.round(sum(mmrs) / len(mmrs), -1)

                # better mmr estimate
                # search each account, keep highest mmr
                player_mmrs = {}
                for a in accs:
                    solo2 = get_player_matches(a, **params, force = False)
                    solo2 = [m for m in solo2 if m != 'error']
                    solo2 = sorted(solo2, key = lambda x: x['start_time'], reverse = True)
                    # solo normal or ranked games
                    solo2 = [m for m in solo2 if m['party_size'] == 1 and m['lobby_type'] in [0, 7]]
                    mmrs2 = [rank2mmr(m['average_rank'], -1) for m in solo2]
                    mmrs2 = [m for m in mmrs2 if m != 0][:20]
                    if len(mmrs2) >= 5 and all([m != 0 for m in mmrs2]):
                        # weighted average with 0.25 decay for bias towards recent games
                        player_mmrs[a] = np.round(pd.Series(mmrs2[::-1]).ewm(com = 2).mean().iloc[-1], -1)
                if len(player_mmrs) > 0:
                    draft.loc[i, 'mmr_estimate_2'] = max(player_mmrs.values())

                # activity
                draft.loc[i, 'nb_solo'] = len(solo)
                draft.loc[i, 'nb_matches'] = len(matches)
                
                # versatility
                heroes = [m['hero_id'] for m in matches]
                u, c = np.unique(heroes, return_counts = True)
                top3 = u[np.argsort(c)][::-1][:3]
                draft.loc[i, 'top3_heroes'] = ', '.join([hero_name(h) for h in top3])
                draft.loc[i, 'nb_heroes'] = len(u)
                c_norm = c / c.max()
                draft.loc[i, 'versatility'] = np.round(c_norm.mean() / max(c_norm.var(), 1), 2)

                # meta player
                # sumprod(hero_games, hero_pickban) / sum(games)
                pb = [hero_stat(h, 'pro_ban') + hero_stat(h, 'pro_pick') for h in u]
                draft.loc[i, 'meta'] = np.round(np.dot(c, pb) / c.sum())

                # hero roles
                # sum(hero pickrate for role * nb of games on hero) for all heroes
                roles = [[hero_stat(h, 'pos{}_pick'.format(r)) for r in range(1, 6)] for h in u]
                roles = np.array(roles)
                roles_total = (roles.T * c).sum(axis = 1) / c.sum()
                for r, perc in zip(range(1, 6), roles_total):
                    draft.loc[i, 'pos{}'.format(r)] = np.round(perc, 3)

            # experience
            history = []
            for a in accs:
                history_ = get_player_history(a, force = update_info)
                if isinstance(history_, dict) and 'error' in history_:
                    # try again
                    # TODO: this should be in the opendota API code, not here
                    history_ = get_player_history(a, force = retry)
                    if isinstance(history_, dict) and 'error' in history_:
                        # likely private profile
                        print('Error getting history', a)
                        history_ = dict()
                history.append(history_)

            if len(history) > 0 and any(h for h in history):
                history = [h for h in history if len(h) > 0]
                games_total = [h['leaver_status'] for h in history if h]
                games_total = [gt['0']['games'] for gt in games_total if gt]
                draft.loc[i, 'games_total'] = sum(games_total)
                patches = [p for h in history for p in list(h['patch'].keys())]
                draft.loc[i, 'patches_played'] = len(np.unique(patches))

            # chattyness
            wordcloud = []
            for a in accs:
                wc = get_player_wordcloud(a, force = update_info, **params)
                if isinstance(wc, dict) and 'error' in wc:
                    # try again
                    # TODO: this should be in the opendota API code, not here
                    wc = get_player_wordcloud(a, force = retry, **params)
                    if isinstance(wc, dict) and 'error' in wc:
                        # likely private profile
                        print('Error getting wordcloud', a)
                        wc = dict()
                wordcloud.append(wc)
            
            if len(wordcloud) > 0 and any(w for w in wordcloud):
                wordcloud = [w['my_word_counts'].items() for w in wordcloud if w and len(w['my_word_counts'])]
                if len(wordcloud) > 0:
                    wordcloud = pd.concat([pd.DataFrame(w) for w in wordcloud])
                    wordcloud = wordcloud.groupby(list(wordcloud.index[:1])).sum()
                    words, counts = wordcloud.index.to_numpy(), wordcloud.values.flatten()
                    top = np.argsort(counts)[::-1]
                    words_flat = [ww for w, c in zip(words, counts) if w not in stops for ww in [w] * c]
                    draft.loc[i, 'top5_words'] = ' '.join([w for w in words[top] if w not in stops][:5])
                    draft.loc[i, 'key_words'] = ' '.join(words_flat)
                    draft.loc[i, 'nb_words'] = len(words)
                    draft.loc[i, 'words_per_match'] = np.round(counts.sum() / draft.loc[i, 'nb_matches'], 2)
                    # FIXME: words per match not great because not all matches are parsed by opendota

            # pings
            pings = []
            for a in accs:
                pings_ = get_player_pings(a, force = update_info, **params)
                if isinstance(pings_, dict) and 'error' in pings_:
                    # try again
                    # TODO: this should be in the opendota API code, not here
                    pings_ = get_player_pings(a, force = retry, **params)
                    if isinstance(pings_, dict) and 'error' in pings_:
                        # likely private profile
                        print('Error getting pings', a)
                        pings_ = dict()
                pings.append(pings_)

            if len(pings) > 0 and any(p for p in pings):
                pings = pd.concat([pd.DataFrame(p) for p in pings]).groupby('x')['games'].sum()
                if len(pings) > 0:
                    ping, ping_count = pings.index, pings.values
                    draft.loc[i, 'avg_pings'] = np.round(np.dot(ping, ping_count) / np.sum(ping_count), 2)

            # info for liquipedia
            try:
                draft.loc[i, 'country'] = get_player_data(accs[0], force = update_info)['country']
                draft.loc[i, 'steam_name'] = get_player_data(accs[0], force = False)['name']
            except:
                pass

            # account privacy
            priv_st = [get_matches(account_id = a, force = update_info)['result']['status'] for a in accs]
            priv = [s == 15 for s in priv_st]
            if all(priv):
                draft.loc[i, 'privacy'] = 'private'
            elif any(priv):
                draft.loc[i, 'privacy'] = 'partial'
            else:
                draft.loc[i, 'privacy'] = 'public'

        # extra: keywords with tf-idf
        vectorizer = TfidfVectorizer()
        words = draft['key_words'].fillna('').copy()

        if words.size == 0 or (words.size == 1 and '' in words.values):
            # FIXME
            words = pd.Series(['nodata'])
        
        matrix = vectorizer.fit_transform(words)
        feature_names = vectorizer.get_feature_names_out()
        
        def keywords(text, n = 10, perc = 0.50):   
            keyw = vectorizer.transform([text]).tocoo()
            keys, vals = keyw.col, keyw.data
            topi = np.argsort(vals)[::-1] # sorting by value
            topp = np.cumsum(vals[topi]) < np.sum(vals) * perc # keep most representative
            topp = np.insert(topp, 0, True)[:-1]

            # topi[topp] is a slice of topi which contains perc% of value
            # keys[topi[topp]] is the index of words in tfidf feature list
            # keys[topi[topp]][:n] is only the first 10 words
            
            topw = feature_names[keys[topi[topp]]] # most representative words
            topv = vals[topi[topp]] # values of representative words

            ww, cc = np.unique(text.split(' '), return_counts = True)
            topc = cc[np.searchsorted(ww, topw)] # unique returns sorted ww list
            word_value_formula = topc * (4 * topv + 1) * (4 * topv + 1) # values are < 1
            topwn = topw[np.argsort(word_value_formula)[::-1]][:n]
            return topwn

        draft['key_words'] = words.apply(lambda x: ' '.join(keywords(x)))

        # cleanup
        draft['alts'] = draft['alts'].apply(lambda acc: ', '.join([str(a) for a in acc]))
        draft['accounts'] = draft['accounts'].apply(lambda acc: ', '.join([str(a) for a in acc]))

        # save report
        if save:
            fname = '{}_{}_{}.csv'.format(
                FNAME,
                league['name'][:3].lower(),
                datestr(time.time(), frmt = '%Y-%m-%d')
                )
            draft.to_csv(os.path.join(OUTPUT_PATH, fname), sep = ';')
