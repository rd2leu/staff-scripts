from kivymd.app import MDApp
from kivymd.uix.screen import Screen
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRectangleFlatButton, MDFlatButton, MDIconButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.pickers import MDDatePicker
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.dropdownitem.dropdownitem import MDDropDownItem
from kivymd.uix.dialog import MDDialog

from gui.kivymd_extra import menu_manager, managed_list, add_label

import time, datetime, zoneinfo

# kivymd.__version__ == '1.1.1'
# kivy.__version__ == '2.1.0'

# https://kivy.org/doc/stable/api-kivy.uix.gridlayout.html#kivy.uix.gridlayout.GridLayout
# https://kivymd.readthedocs.io/en/1.0.0/components/menu/index.html
# https://kivy.org/doc/stable/api-kivy.uix.button.html#module-kivy.uix.button
# https://kivy.org/doc/stable/api-kivy.uix.filechooser.html
# https://kivymd.readthedocs.io/en/0.104.0/components/dropdown-item/index.html
# https://kivymd.readthedocs.io/en/0.104.2/components/button/index.html
# https://kivymd.readthedocs.io/en/latest/components/menu/index.html#center-position
# https://kivymd.readthedocs.io/en/latest/components/dropdownitem/
# https://kivymd.readthedocs.io/en/latest/search/?q=viewclass&check_keywords=yes&area=default
# https://github.com/kivymd/KivyMD/blob/master/kivymd/uix/dropdownitem/dropdownitem.py
# https://kivymd.readthedocs.io/en/0.104.2/components/carousel/
# https://kivymd.readthedocs.io/en/1.0.0/components/datepicker/index.html
# https://stackoverflow.com/questions/24649750/kivy-anchor-and-gridlayout-centering
# https://kivymd.readthedocs.io/en/1.1.1/components/screen/index.html
# https://stackoverflow.com/questions/65340738/kivymd-custom-input-dialog-problem-with-getting-text
# https://kivymd.readthedocs.io/en/1.1.1/components/dialog/index.html
# https://docs.python.org/3/library/zoneinfo.html#zoneinfo.available_timezones
# https://pytz.sourceforge.net/#helpers
# https://github.com/kivymd/KivyMD/blob/master/kivymd/uix/list/list.py
# https://github.com/kivymd/KivyMD/blob/master/kivymd/uix/list/list.kv
# https://kivymd.readthedocs.io/en/1.1.1/components/list/index.html#custom-list-item

# note:
#   in general pytz handles special cases better (ex: daylight saving)
#   and is used by pandas, but here we don't need to be very precise
def timezone_to_short(timezone):
    """Convert TZ_database name to local short aberviation"""
    return zoneinfo.ZoneInfo(timezone).tzname(datetime.datetime.now())
def timezone_validate(timezone, default = None):
    """Check if timezone is a valid TZ database name or abberviation to one, returning the TZ identifier"""
    try:
        # timezone is a valid TZ database name
        zoneinfo.ZoneInfo(timezone)
        return timezone
    except zoneinfo.ZoneInfoNotFoundError:
        now = datetime.datetime.now()
        # not great, not terrible
        n = 2
        times = [now + datetime.timedelta(days = i * 365.249 / n) for i in range(n)]
        for tz in zoneinfo.available_timezones():
            for t in times:
                short = zoneinfo.ZoneInfo(tz).tzname(t)
                if timezone == short:
                    # timezone is a TZ database abbreviation
                    return tz
        return default

def is_weekday(s):
    return s.lower() in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

def datetime_nearest(dt, day_of_week = 'Monday', when = 'before'):
    #weekdays = [datetime.date(2001, 1, 1 + i).strftime('%A').lower() for i in range(7)] # that day was a monday
    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    dow = weekdays.index(day_of_week.lower())
    if when == 'before':
        return dt - datetime.timedelta(days = (dt.weekday() - dow) % 7)
    elif when == 'after':
        return dt + datetime.timedelta(days = (dow - dt.weekday()) % 7)
    else:
        raise ValueError("Argument when must be 'before' or 'after', got '{}'".format(when))

## input box dialog (popup window)
class input_box(MDBoxLayout):
    def __init__(self, title = '', hint = '', *args, **kwargs):
        # add some defaults
        kwargs_ = {
            'orientation': 'vertical',
            'size_hint_y': None,
            }
        kwargs_.update(kwargs)
        super().__init__(*args, **kwargs_)
        if title != '':
            label = MDLabel(text = title)
            self.add_widget(label)
        self.text_input = MDTextField(hint_text = hint)
        self.add_widget(self.text_input)
    def get_data(self):
        return self.text_input.text



## TODO: fetch from github or use kivy.uix.filechooser
import os, json
import numpy as np
team_info_path = os.path.join('output', 'rd2l_s27_utf16.json')
with open(team_info_path, encoding = 'utf-16') as f:
    season_info = json.load(f)



## main application
class demo_app(MDApp):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.screen = Screen()
        self.mm = menu_manager() # menu manager

        # match list
        self.lm = managed_list() # list manager

        # refs
        self.main_grid = None
        self.date_start_button = None
        self.date_end_button = None
        self.date_timezone_input = None
        self.result = None

    def build(self):

        self.main_grid = MDGridLayout(rows = 6)

        ## row 1: league selector
        league_label = MDLabel(text = 'League:')

        # orgs
        league_org_button = MDDropDownItem(id = 'league_org') # using a menu item as a button, so that it looks the same
        league_org_list = [season_info['name']] # FIXME: read list from file
        self.mm.menu_populate(league_org_button, league_org_list)
        
        # seasons
        league_season_button = MDDropDownItem(id = 'league_season')
        def league_season_list():
            org = self.mm.menu_get_selected(league_org_button.id)
            return [s['name'] for s in season_info['seasons']]
        self.mm.menu_populate(league_season_button, league_season_list, parent_id = league_org_button.id)

        # leagues
        league_league_button = MDDropDownItem(id = 'league_league')
        def league_league_list():
            org = self.mm.menu_get_selected(league_org_button.id)
            season = self.mm.menu_get_selected(league_season_button.id)
            return [l['name'] for l in season_info['seasons'][season]['leagues']]
        self.mm.menu_populate(league_league_button, league_league_list, parent_id = league_season_button.id)

        # divisions
        league_division_button = MDDropDownItem(id = 'league_division')
        def league_division_list():
            org = self.mm.menu_get_selected(league_org_button.id)
            season = self.mm.menu_get_selected(league_season_button.id)
            league = self.mm.menu_get_selected(league_league_button.id)
            return [d['name'] for d in season_info['seasons'][season]['leagues'][league]['divisions']]
        self.mm.menu_populate(league_division_button, league_division_list, parent_id = league_league_button.id)

        # layout
        league_grid = MDGridLayout(cols = 5)
        league_grid.add_widget(league_label)
        league_grid.add_widget(league_org_button)
        league_grid.add_widget(league_season_button)
        league_grid.add_widget(league_league_button)
        league_grid.add_widget(league_division_button)
        self.main_grid.add_widget(league_grid)

        ## row 2: date selector

        # date input
        # TODO: find last wednesday
        date_label = MDLabel(text = 'Search dates:')
        self.date_start_button = MDRectangleFlatButton(id = 'date_start', on_release = self.date_picker_show)
        self.date_end_button = MDRectangleFlatButton(id = 'date_end', on_release = self.date_picker_show)

        # timezone picker
        date_timezone_list = ['CET', 'GMT', 'EDT', 'PDT', 'EET', '...']
        date_timezone_button = MDRectangleFlatButton(id = 'date_timezone')
        self.mm.menu_populate(date_timezone_button, date_timezone_list)

        # popup for custom timezones
        def date_timezone_handler():
            if self.mm.menu_get_item('date_timezone') == '...':
                # create popup layout
                self.date_timezone_input = input_box(
                    title = 'Choose another timezone',
                    hint = 'ex: Australia/Melbourne EEST +08',
                    )
                # add submit button callback
                def input_dialog_callback(obj):
                    data = self.date_timezone_input.get_data()
                    if data != '':
                        self.mm.menu_set_custom('date_timezone', data)
                # open popup dialog
                pop = MDDialog(
                    title = '',
                    type = 'custom',
                    content_cls = self.date_timezone_input,
                    buttons = [
                        MDFlatButton(
                            text = 'Save',
                            on_release = input_dialog_callback,
                            )
                        ]
                    )
                pop.open()
                # set list to default in case dialog is dismissed
                self.mm.menu_set('date_timezone', 0)
        self.mm.menu_callbacks_add('date_timezone', date_timezone_handler, which = 'post')
        #self.mm.menu_callbacks_add('date_timezone', self.date_RD2L_autoset, which = 'post') # FIXME: trigger on timezone input dialog

        # RD2L specific, set start and end date depending on league
        self.mm.menu_callbacks_add('league_org', self.date_RD2L_autoset, which = 'post')
        self.mm.menu_callbacks_add('league_season', self.date_RD2L_autoset, which = 'post')
        self.mm.menu_callbacks_add('league_league', self.date_RD2L_autoset, which = 'post')
        self.mm.menu_callbacks_add('league_division', self.date_RD2L_autoset, which = 'post')
        self.date_RD2L_autoset()
        
        # layout
        date_grid = MDGridLayout(cols = 4)
        date_grid.add_widget(date_label)
        date_grid.add_widget(self.date_start_button)
        date_grid.add_widget(self.date_end_button)
        date_grid.add_widget(date_timezone_button)
        self.main_grid.add_widget(date_grid)

        ## row 3: other parameters

        # best of selector
        other_bestof_label = MDLabel(text = 'Best of:')
        other_bestof_list = ['1', '2', '3', '5']
        other_bestof_button = MDRectangleFlatButton(id = 'other_bestof')
        self.mm.menu_populate(other_bestof_button, other_bestof_list)

        # cached
        other_cached_label = MDLabel(text = 'Cached:')
        other_cached_list = ['Yes', 'No']
        other_cached_button = MDRectangleFlatButton(id = 'other_cached')
        self.mm.menu_populate(other_cached_button, other_cached_list)

        # layout
        other_grid = MDGridLayout(cols = 4)
        other_grid.add_widget(other_bestof_label)
        other_grid.add_widget(other_bestof_button)
        other_grid.add_widget(other_cached_label)
        other_grid.add_widget(other_cached_button)
        self.main_grid.add_widget(other_grid)

        ## row 4: match picker
        def match_team_list_names():
            org = self.mm.menu_get_selected(league_org_button.id)
            season = self.mm.menu_get_selected(league_season_button.id)
            league = self.mm.menu_get_selected(league_league_button.id)
            division = self.mm.menu_get_selected(league_division_button.id)
            #print(org, season, league, division)
            return [t['name'] for t in season_info['seasons'][season]['leagues'][league]['divisions'][division]['teams']]

        def match_add():
            idx = self.lm.add_row()
            b1 = MDRectangleFlatButton(id = 'match_{}_team_1'.format(idx))
            self.lm.add_item(idx, b1)
            vs = MDLabel(text = 'vs', id = 'match_{}_vs')
            self.lm.add_item(idx, vs)
            b2 = MDRectangleFlatButton(id = 'match_{}_team_2'.format(idx))
            self.lm.add_item(idx, b2)
            self.mm.menu_populate(b1, match_team_list_names, parent_id = league_division_button.id)
            self.mm.menu_populate(b2, match_team_list_names, parent_id = league_division_button.id)

        self.lm.set_callback(0, match_add)
        for i in range(len(match_team_list_names()) // 2):
            # add a list item for each match
            match_add()

        # layout
        self.main_grid.add_widget(self.lm)

        ## row 5, 6: run
        submit_button = MDRectangleFlatButton(text = 'Submit', id = 'submit', on_release = self.submit)
        self.result = MDLabel(text = 'Result', id = 'result')         
        self.main_grid.add_widget(submit_button)
        self.main_grid.add_widget(self.result)
        self.screen.add_widget(self.main_grid)

        return self.screen

    def date_RD2L_autoset(self):
        timezone = self.mm.menu_get_item('date_timezone')
        tz = timezone_validate(timezone, 'CET')
        now = datetime.datetime.now().astimezone(zoneinfo.ZoneInfo(tz))
        # RD2L specific
        league = self.mm.menu_get_item('league_league')
        if is_weekday(league):
            # ex: Sunday or Wednesday
            start_date = datetime_nearest(now, league, when = 'before')
            self.date_start_button.text = start_date.strftime('%Y-%m-%d')
            self.date_end_button.text = now.strftime('%Y-%m-%d')

    # date picker
    def date_picker_show(self, obj):
        if obj.id == 'date_start':
            title = 'Start date'
            date = datetime.datetime.strptime(self.date_start_button.text, '%Y-%m-%d')
        elif obj.id == 'date_end':
            title = 'End date'
            date = datetime.datetime.strptime(self.date_end_button.text, '%Y-%m-%d')
        date_dialog = MDDatePicker(year = date.year, month = date.month, day = date.day, title_input = title) # TODO: change this to range picker
        date_dialog.bind(on_save = lambda inst, val, rng: self.date_picker_save(val, obj))
        date_dialog.open()
    def date_picker_save(self, value, obj):
        obj.text = value.strftime('%Y-%m-%d')

    def submit(self, obj):
        self.result.text = 'working ...'


if __name__ == "__main__":
    app = demo_app()
    app.run()
    
