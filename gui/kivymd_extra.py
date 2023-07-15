from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.dropdownitem.dropdownitem import MDDropDownItem

# TODO: logging
# TODO: menu item object (and copying mechanism)

class menu_manager:
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.menus = {} # the menu objects themselves
        self.menu_data = {} # menu items and stored data

    def _menu_set_callback(self, menu_id, text, **key_values):
        """Callback for drop down menu"""

        # handle extra callbacks
        for callback in self.menu_data[menu_id]['pre_callbacks']:
            callback()

        # update menu data
        self.menus[menu_id].caller.text = text # change the caller text (ex: button text)
        self.menu_data[menu_id]['data'].update(key_values) # store new values
        self.menus[menu_id].dismiss() # close the menu
        #print(menu_id, self.menu_data[menu_id]['data'])

        # manage child menus
        # BFS of the family tree of the menu
        family = []
        queue = [(menu_id, c) for c in self.menu_data[menu_id]['children']]
        cnt = 0
        recur_lim = 10
        while queue and cnt < recur_lim:
            parent_id, child_id = queue.pop(0)
            family.append((parent_id, child_id))
            queue.extend([(child_id, gc) for gc in self.menu_data[child_id]['children']])
            cnt += 1
        if cnt == recur_lim:
            raise RecursionError("Recursion limit ({}) reached".format(recur_lim))
        #print(menu_id, cnt, family)

        # ask each of the family members to reinitiate themselves accordingly
        for parent_id, child_id in family:
            # preserve extra callbacks
            pre_callbacks = self.menu_data[child_id]['pre_callbacks']
            post_callbacks = self.menu_data[child_id]['post_callbacks']
            # repopulate menu list
            if self.menu_data[child_id]['_items'] is None:
                # static menus are just reset
                #print(child_id, 'static')
                self.menu_set(child_id, 0) # reset children menus to default (FIXME: recursive)
            else:
                # dynamic menus have to be recreated
                #print(child_id, 'dynamic')
                self.menu_populate(self.menus[child_id].caller, self.menu_data[child_id]['_items'], parent_id = parent_id)
            # add the callbacks back where they were
            for callback in pre_callbacks:
                self.menu_callbacks_add(child_id, callback, which = 'pre')
            for callback in post_callbacks:
                self.menu_callbacks_add(child_id, callback, which = 'post')

        # handle extra callbacks
        for callback in self.menu_data[menu_id]['post_callbacks']:
            callback()

    def menu_populate(self, obj, items, pre_text = '', parent_id = None, **kwargs):
        """Attach drop down menu to object with items"""

        if not hasattr(obj, 'id') or obj.id == '':
            raise TypeError("object must have an ID")
        menu_id = obj.id

        if hasattr(items, '__call__'):
            _items = items # save a copy of the function to generate items # TODO: check copy
            item_list = items()
        else:
            _items = None
            item_list = [i for i in items]

        # prepare storage
        self.menu_data[menu_id] = {}
        self.menu_data[menu_id]['items'] = item_list # keep items used to populate menu (actually not needed)
        self.menu_data[menu_id]['_items'] = _items # used when items are evaluated on creation
        self.menu_data[menu_id]['data'] = {} # storage for the values we set
        self.menu_data[menu_id]['menu_items'] = [] # storage for menu items
        self.menu_data[menu_id]['children'] = [] # storage for sub menu ids
        self.menu_data[menu_id]['pre_callbacks'] = [] # storage for extra callbacks
        self.menu_data[menu_id]['post_callbacks'] = [] # storage for extra callbacks
        if parent_id:
            if menu_id not in self.menu_data[parent_id]['children']:
                self.menu_data[parent_id]['children'] += [menu_id]
        
        # prepare drop down menu items
        for k, v in enumerate(item_list):
            self.menu_data[menu_id]['menu_items'] += [
                {
                    'text': '{}{}'.format(pre_text, v),
                    'viewclass': 'OneLineListItem',
                    #'height': dp(48),
                    #'right_text': 'Key {}'.format(k),
                    'on_release': lambda k = k, v = v, m_id = menu_id: self._menu_set_callback(
                        menu_id = m_id,
                        text = '{}'.format(v), # TODO: stop passing this, work with objects and indexes
                        selected = k, # this goes in key_values
                        )
                    }
                ]
        
        # create the drop down menu
        menu_args = {
            'position': 'bottom',
            #'bg_color': '',
            'width_mult': '3',
            }
        menu_args.update(kwargs)
        self.menus[menu_id] = MDDropdownMenu(
            caller = obj,
            items = self.menu_data[menu_id]['menu_items'],
            **menu_args,
        )
        self.menus[menu_id].bind()
        
        # update object callback and default to first menu item
        obj.on_release = lambda m_id = menu_id: self.menus[m_id].open()
        self.menu_set(menu_id, 0) # run callback with first item (FIXME)

    def menu_set(self, menu_id, index):
        """Set menu to item by index"""
        n = len(self.menu_data[menu_id]['items'])
        if index < 0 or index > n:
            raise IndexError("Menu index out of range")
        self.menus[menu_id].items[index]['on_release']()

    def menu_set_custom(self, menu_id, text_item):
        # FIXME: only temporary and doesn't show in list
        n = len(self.menu_data[menu_id]['items'])
        self.menu_data[menu_id]['items'] += [text_item]
        self.menu_data[menu_id]['data']['selected'] = n
        self.menus[menu_id].caller.text = text_item

    def _menu_get(self, menu_id, key):
        return self.menu_data[menu_id]['data'][key]
    def menu_get_selected(self, menu_id):
        """Get index of current menu item"""
        return self._menu_get(menu_id, 'selected')
    def menu_get_item(self, menu_id):
        """Get value of current menu item"""
        return self.menu_data[menu_id]['items'][self._menu_get(menu_id, 'selected')]

    def menu_callbacks_add(self, menu_id, callback, which = 'pre'):
        """Add extra callbacks to be executed pre/post/both menu item selection"""
        if which in ['pre', 'both']:
            self.menu_data[menu_id]['pre_callbacks'] += [callback]
        if which in ['post', 'both']:
            self.menu_data[menu_id]['post_callbacks'] += [callback]
    def menu_callbacks_clear(self, menu_id, which = 'both'):
        """Clear extra menu callbacks"""
        if which in ['pre', 'both']:
            self.menu_data[menu_id]['pre_callbacks'] = []
        if which in ['post', 'both']:
            self.menu_data[menu_id]['post_callbacks'] = []

# demo

if __name__ == '__main__':
    
    from kivymd.app import MDApp
    from kivymd.uix.screen import Screen
    from kivymd.uix.label import MDLabel
    from kivymd.uix.button import MDFlatButton
    from kivymd.uix.gridlayout import MDGridLayout
    
    data = {
        'fruits': {
            'apple': {'red': 20, 'green': 30},
            'orange': {'small': 30, 'medium': 35, 'large': 40},
            'banana': {'green': 25, 'yellow': 30, 'ripe': 20},
            },
        'veggies': {
            'tomato': {'roma': 20, 'local': 40},
            'potato': {'small': 10, 'medium': 15, 'large': 20},            
            },
        }

    class Demo(MDApp):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.label_1 = None
            self.label_2 = None
            self.mm = menu_manager()
            
        def build(self):
            screen = Screen()
            grid = MDGridLayout(cols = 1, rows = 6)

            # menu level 1
            list_1 = list(data.keys())
            button_1 = MDDropDownItem(id = 'list_1')
            self.mm.menu_populate(button_1, list_1)

            # menu level 2
            def list_2():
                pick_1 = self.mm.menu_get_item('list_1')
                return list(data[pick_1].keys())
            button_2 = MDDropDownItem(id = 'list_2')
            self.mm.menu_populate(button_2, list_2, parent_id = 'list_1')

            # menu level 3
            def list_3():
                pick_1 = self.mm.menu_get_item('list_1')
                pick_2 = self.mm.menu_get_item('list_2')
                return list(data[pick_1][pick_2].keys())
            button_3 = MDDropDownItem(id = 'list_3')
            self.mm.menu_populate(button_3, list_3, parent_id = 'list_2')

            # button
            button = MDFlatButton(text = 'checkout', on_release = self.checkout)

            # label
            self.label_1 = MDLabel()
            self.label_2 = MDLabel()

            # add extra menu callback on the fly
            def update():
                value = self._get_selected_value()
                self.label_1.text = 'selected: {}'.format(value)
            self.mm.menu_callbacks_add('list_1', update, which = 'post')
            self.mm.menu_callbacks_add('list_2', update, which = 'post')
            self.mm.menu_callbacks_add('list_3', update, which = 'post')
            update()

            grid.add_widget(button_1)
            grid.add_widget(button_2)
            grid.add_widget(button_3)
            grid.add_widget(button)
            grid.add_widget(self.label_1)
            grid.add_widget(self.label_2)
            screen.add_widget(grid)
            return screen
        
        def _get_selected_value(self):
            pick_1 = self.mm.menu_get_item('list_1')
            pick_2 = self.mm.menu_get_item('list_2')
            pick_3 = self.mm.menu_get_item('list_3')
            return data[pick_1][pick_2][pick_3]

        def checkout(self, obj):
            value = self._get_selected_value()
            self.label_2.text = 'price: {}'.format(value)

    app = Demo()
    app.run()
