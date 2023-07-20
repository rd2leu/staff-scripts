from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.dropdownitem.dropdownitem import MDDropDownItem
from kivymd.uix.list import MDList
from kivymd.uix.list import IconLeftWidget, ILeftBodyTouch, OneLineAvatarListItem
from kivy.metrics import dp

def add_label(widgets, text, pos = 'left', grid_args = {}, **kwargs):
    """Place widgets in a grid with a label"""
    if hasattr(widgets, '__len__'):
        n = len(widgets)
        items = [i for i in widgets]
    else:
        n = 1
        items = [widgets]
    grid_order = list(range(n))
    if pos in ['top', 'up', 'above']:
        grid_params = {'cols': 1, 'rows': n + 1}
        grid_order.insert(0, n) # index 0 item n
    elif pos in ['down', 'bottom', 'below']:
        grid_params = {'cols': 1, 'rows': n + 1}
        grid_order.insert(n, n)
    elif pos in ['left', 'before']:
        grid_params = {'cols': n + 1, 'rows': 1}
        grid_order.insert(0, n)
    elif pos in ['right', 'after']:
        grid_params = {'cols': n + 1, 'rows': 1}
        grid_order.insert(n, n)
    else:
        raise TypeError("add_label() got an unexpected value for argument 'pos'")
    grid_params.update(grid_args)
    grid = MDGridLayout(**grid_params)
    label = MDLabel(text = text, **kwargs)
    items += [label]
    for idx in grid_order:
        grid.add_widget(items[idx])
    return grid


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
            'ver_growth': 'down',
            'hor_growth': 'right',
            'opening_time': 0.1,
            #'bg_color': '',
            'max_height': dp(224),
            'border_margin': dp(24),
            #'border_margin': dp(4),
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

class GridContainer(ILeftBodyTouch, MDGridLayout):
    adaptive_width = True

class managed_list(MDList):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.items = {} # the list item rows (by row index)
        self.row_items = {} # objects within the grid container of a row
        self._cuids = {} # callback uid TODO: fbind unbind
        self._n = -1

        # build
        self.add_row(icon = 'plus')
        #self.set_callback(0, lambda caller: self.add_row)
        self.set_callback(0, self.add_row)

    # FIXME: why this? don't need uid here yo
    def _next(self):
        self._n += 1
        return self._n

    #TODO: __get_item__ __iter__ __len__
    def __getitem__(self, index):
        if isinstance(index, int):
            return list(self)[index]
        elif isinstance(index, tuple):
            return list(self)[index[0]][index[1]]
        elif isinstance(index, list):
            return [self[i] for i in index]
        else:
            raise IndexError("Index not in [int, tuple]")
    def __iter__(self):
        for i in self.items:
            if i in self.row_items:
                yield list(self.row_items[i].values())
            else:
                yield []
    def __len__(self):
        return len(self.items)

    def add_row(self, icon = 'minus'):
        """Add empty row with left side icon"""
        idx = self._next()
        print('add_row', idx, icon)
        item = OneLineAvatarListItem(
            IconLeftWidget(icon = icon,
                           #on_release = lambda caller: print(caller),
                           id = 'a{}'.format(idx),
                           ),
            GridContainer(
                rows = 1,
                id = 'g{}'.format(idx),
                size_hint = (None, 1),
                ),
            id = 'i{}'.format(idx),
            )
        item.remove_widget(item.ids['_text_container'])
        self.add_widget(item)
        self.items[idx] = item
        #self.set_callback(idx, lambda caller, i = idx: self.remove_row(i))
        self.set_callback(idx, lambda i = idx: self.remove_row(i))
        return idx

    def remove_row(self, idx):
        print('remove_row', idx)
        item = self.items.pop(idx)
        self.remove_widget(item)
        self._cuids.pop(idx)

    def set_callback(self, idx, callback, *args, **kwargs):
        """Set custom callback for left side icon"""
        print('set_callback', idx)
        icon = self.items[idx].ids['a{}'.format(idx)]
        # check if callback already exists
        # https://kivy.org/doc/stable/api-kivy.event.html#kivy.event.EventDispatcher.unbind_uid
        #if idx in self._cuids:
        #    icon.unbind_uid('on_release', self._cuids[idx])
        # set callback and save uid
        #self._cuids[idx] = icon.fbind('on_release', callback, *args, **kwargs)
        icon.on_release = callback
        self._cuids[idx] = idx

    def add_item(self, idx, obj):
        """Add items to a row"""
        print('add_item', idx, obj.id)
        if not hasattr(obj, 'id') or obj.id == '':
            raise TypeError("object must have an ID")
        item_id = obj.id
        if item_id in self.items:
            raise KeyError("object with id '{}' already in list".format(item_id))

        self.row_items[idx] = {}
        self.row_items[idx][item_id] = obj
        self.items[idx].ids['g{}'.format(idx)].add_widget(obj)
        
    def remove_item(self, idx, item_id):
        """Remove items from a row"""
        print('add_item', idx, item_id)
        obj = self.row_items[idx].pop(item_id)
        self.items[idx].ids['g{}'.format(idx)].remove_widget(obj)


# demo

if __name__ == '__main__':
    
    from kivymd.app import MDApp
    from kivymd.uix.screen import Screen
    from kivymd.uix.label import MDLabel
    from kivymd.uix.button import MDFlatButton
    from kivymd.uix.gridlayout import MDGridLayout
    
    data = {
        'fruits': {
            'apple': {'yellow-brown': '15', 'red': 20, 'green': 30},
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
            self.lm = managed_list()
            self.lm.remove_row(0)
            
        def build(self):
            screen = Screen()
            grid = MDGridLayout(cols = 1)

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
            button_4 = MDFlatButton(text = 'add', on_release = self.add)
            button_5 = MDFlatButton(text = 'checkout', on_release = self.checkout)

            # label
            self.label_1 = MDLabel()
            self.label_2 = MDLabel()

            # add extra menu callback
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
            grid.add_widget(button_4)
            grid.add_widget(button_5)
            grid.add_widget(self.label_1)
            grid.add_widget(self.label_2)
            grid.add_widget(self.lm)

            screen.add_widget(grid)
            return screen

        def add(self, obj):
            thing = self._get_selected_item()
            price = self._get_selected_value()
            text = '{}: {}'.format(thing, price)
            idx = self.lm.add_row()
            self.lm.add_item(idx, MDLabel(
                text = text,
                id = str(idx),
                size_hint = (None, 1),
                ))
        
        def _get_selected_value(self):
            pick_1 = self.mm.menu_get_item('list_1')
            pick_2 = self.mm.menu_get_item('list_2')
            pick_3 = self.mm.menu_get_item('list_3')
            return data[pick_1][pick_2][pick_3]

        def _get_selected_item(self):
            pick_2 = self.mm.menu_get_item('list_2')
            pick_3 = self.mm.menu_get_item('list_3')
            return '{} {}'.format(pick_3, pick_2)

        def checkout(self, obj):
            total = sum([int(t.text.split(': ')[1]) for r in self.lm for t in r])
            self.label_2.text = 'price: {}'.format(total)

    app = Demo()
    app.run()
