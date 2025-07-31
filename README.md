# staff-scripts

Collection of useful scripts to automate RD2L staff tasks.

### General:
- draft_sheet_parser.py: reads the draft spreadsheet (google docs) and generates the team info .json under the `staff-scripts/draft`.
- fantasy.py: calculates fantasy league scores based on participant entries in fantasy/draft.
- cheat-sheet.py: collects player history and stats for making a pre-season cheatsheet (ex: estimate MMR from medal for non-immortal players).
- playday-stats.py: used for trivia stats (ex: most minutes without a last hit) and end of season stats.
- utilities2.py: converts dotabuff/stratz/... urls or steam urls or steam IDs into Dota 2 account IDs.

### Liquipedia:
- liquipedia_teamlist.py: generates the liquipedia list of teams and players from parsed draft sheet.
- liquipedia_map.py: generates liquipedia Map text from a match ID (picks, bans, time, winner).
- liquipedia_playday.py: generates liquipedia Match2 text for a complete playday (after filling schedule).
- liquipedia_standings.py: reads a liquipedia text of matches and generates a liquipedia standings text.

# How to install:
- Download and install Python from `https://www.python.org/downloads/` (select option to add PIP to Path)
- Install libraries with `pip install pandas numpy requests scikit-learn lmdbm jsonpickle openpyxl`
- Download and unzip the `staff-scripts` project `https://github.com/rd2leu/staff-scripts/archive/refs/heads/master.zip`
- Download and unzip the `d2tools` project under the subfolder `/d2tools` (ex: `/d2tools/api.py`)
- Get a Steam API key by filling in a form here: `https://steamcommunity.com/dev/apikey` and save it to a `/key.txt` file.

### Q/A:
- Liquipedia team missing error: create team templates here: `https://liquipedia.net/dota2/Liquipedia:Team_Templates`
- How to open .csv files: `https://www.libreoffice.org/`
- `requests.exceptions.JSONDecodeError` make sure `staff-scripts/key.txt` contains your Steam API key.
