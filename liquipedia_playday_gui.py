from kivymd.app import MDApp
from kivymd.uix.screen import Screen
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRectangleFlatButton, MDFlatButton
from kivymd.uix.boxlayout import BoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.pickers import MDDatePicker
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.dropdownitem.dropdownitem import MDDropDownItem
from kivymd.uix.dialog import MDDialog

from gui.kivymd_extra import menu_manager, add_label

import time, datetime, zoneinfo

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
class input_box(BoxLayout):
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

        # refs
        self.date_start_button = None
        self.date_end_button = None
        self.date_dialog = None
        self.date_timezone_input = None

    def build(self):

        main_grid = MDGridLayout(rows = 5)

        ## row 1: league selector
        league_label = MDLabel(text = 'Pick:')

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
        main_grid.add_widget(league_grid)

        ## row 2: date selector

        # date input
        # TODO: find last wednesday
        date_label = MDLabel(text = 'Date:')
        self.date_start_button = MDRectangleFlatButton(text = '01/01/1970')
        self.date_end_button = MDRectangleFlatButton(text = '19/01/2038')

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
        self.mm.menu_callbacks_add('date_timezone', self.date_RD2L_autoset, which = 'post') # FIXME timezone dialog

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
        main_grid.add_widget(date_grid)

        ## row 3:
        # defining label with all the parameters
        label = MDLabel(
            text="HI PEOPLE!", halign='center',
            theme_text_color="Custom",
            text_color=(0.5, 0, 0.5, 1),
            font_style='Caption',
            pos_hint={'center_x': 0.5, 'center_y': 0.3})
         
        # defining Text field with all the parameters
        name = MDTextField(text="Enter name", pos_hint={
                           'center_x': 0.8, 'center_y': 0.8},
                           size_hint_x=None, width=100)

        # defining Button with all the parameters
        btn = MDRectangleFlatButton(text="Submit", pos_hint={
                                    'center_x': 0.5, 'center_y': 0.3},
                                    on_release=self.btnfunc)

        main_grid.add_widget(add_label([name], 'name label left', pos = 'left'))
        main_grid.add_widget(add_label(btn, 'name label top', pos = 'top'))
        main_grid.add_widget(add_label(label, 'name label bottom', pos = 'bottom'))

        # adding widgets to screen
        self.screen.add_widget(main_grid)

        # returning the screen
        return self.screen


    # defining a btnfun() for the button to
    # call when clicked on it
    def btnfunc(self, obj):
        print("button is pressed!!")

    def date_RD2L_autoset(self):
        timezone = self.mm.menu_get_item('date_timezone')
        tz = timezone_validate(timezone, 'CET')
        now = datetime.datetime.now().astimezone(zoneinfo.ZoneInfo(tz))
        # RD2L specific
        league = self.mm.menu_get_item('league_league')
        if is_weekday(league):
            # ex: Sunday or Wednesday
            start_date = datetime_nearest(now, league, when = 'before')
            self.date_start_button.text = start_date.strftime('%d/%m/%Y')
            self.date_end_button.text = now.strftime('%d/%m/%Y')


    # date picker
    def date_picker_show(self):
        self.date_dialog = MDDatePicker()
        self.date_dialog.bind(on_save = self.date_picker_save, on_cancel = self.date_picker_cancel)
        self.date_dialog.open()
    def date_picker_save(self, instance, value, date_range):
        pass
    def date_picker_cancel(self, instance, value):
        pass

if __name__ == "__main__":
    app = demo_app()
    app.run()
    