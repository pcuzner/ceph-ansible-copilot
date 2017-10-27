
import urwid
import inspect
import string


class TableRow(urwid.WidgetWrap):
    """
    Table row-like implementation that uses space to toggle the rows
    selected state
    """

    # inspired by https://repos.goffi.org/urwid-satext/file/tip/urwid_satext

    def __init__(self, text, app, align='left'):
        """
        @param text: same as urwid.Text's text parameter
        @param align: same as urwid.Text's align parameter
        """

        self._was_focused = False
        self.text = text
        self.app = app
        urwid.WidgetWrap.__init__(self, urwid.Text(text, align=align))

        if 'X' in self.text[:3]:
            self._selected = True
        else:
            self._selected = False

        data_field = self.text[3:].split()
        hostname = data_field[1]

        self.roles = self.app.cfg.hosts[hostname].roles
        self._mon = True if 'mon' in self.roles else False
        self._rgw = True if 'rgw' in self.roles else False
        self._osd = True if 'osd' in self.roles else False

    def get_value(self):
        assert isinstance(self.text, basestring)

        if isinstance(self.text, basestring):
            return self.text

    def get_text(self):
        """for compatibility with urwid.Text"""
        return self.get_value()

    def set_text(self, text):
        """/!\ set_text doesn't change self.selected_txt !"""
        self.text = text
        self.setState(self._selected)

    def _set_txt(self):

        hosts = self.app.cfg.hosts

        data_field = self.get_value()[3:].split()
        hostname = data_field[1]

        if self._selected:
            self.text = ' X ' + self.text[3:]
            hosts[hostname].selected = True
        else:
            self.text = '   ' + self.text[3:]
            hosts[hostname].selected = False

        self._w.base_widget.set_text(self.text)

    def setState(self, selected):
        """Toggle the selected state of a table row

        @param selected: boolean state value
        """
        assert type(selected) == bool
        self._selected = selected
        self._set_txt()
        self._was_focused = False
        self._invalidate()

    def getState(self):
        return self._selected

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key in [' ', 'enter']:
            self.setState(not self._selected)
        elif key in ['M', 'm']:
            pass
        elif key in ['O', 'o']:
            pass
        elif key in ['R', 'r']:
            pass
        else:
            return key

    def render(self, size, focus=False):

        app = self.app
        hosts = app.cfg.hosts

        if not focus:
            app.show_message("")
            if self._was_focused:
                self._set_txt()
                self._was_focused = False

        else:
            field = self.text[3:].split()
            host_name = field[1]
            if hosts[host_name].state.lower() == 'ready':
                status = hosts[host_name].state
            else:
                status = "{}:{}".format(hosts[host_name].state,
                                        hosts[host_name].state_msg)

            msg = "{} {}".format(host_name,
                                 status)

            app.show_message(msg)

            if not self._was_focused:
                self._w.base_widget._invalidate()
                self._was_focused = True

        return self._w.render(size, focus)


class ProgressOverlay(urwid.WidgetWrap):
    def __init__(self, bottom_w=None, complete=0):

        self.bottom_w = bottom_w
        self.done = 0
        self.complete = complete

        urwid.WidgetWrap.__init__(self,
                                  self.render_page)

    @property
    def render_page(self):
        pb = urwid.Pile([
               urwid.AttrMap(
                 urwid.Filler(
                   urwid.LineBox(
                     urwid.ProgressBar('pg_normal', 'pg_complete',
                                       current=self.done, done=self.complete),
                     title="Probing hosts")),
                 'pg_normal')])

        w = urwid.Overlay(pb, self.bottom_w, align='center', valign='top',
                          width=60, height=5, top=5)
        return w

    def update(self, done):
        self.done = done
        return self.render_page


class SelectableText(urwid.Text):

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class ButtonLabel(urwid.SelectableIcon):
    """
    Simple class which moves the cursor beyond the length of the button text
    to hide the flashing cursor
    """

    def set_text(self, label):
        """
        set_text is invoked by Button.set_label
        """
        self.__super.set_text(label)
        self._cursor_position = len(label) + 1

# class ErrorListBox(urwid.ListBox):
#
#     def keypress(self, size, key):
#         cur_pos = self.get_focus()[1]
#         if key == 'up':
#
#             if cur_pos == 0:
#                 copilot.show_message("")
#             else:
#                 copilot.show_message("up {}:{}".format(cur_pos, self.get_focus()))
#         elif key == 'down':
#             # if self.get_focus() == len(self.body) - 1
#             copilot.show_message("down")
#         return key


class DataRow(urwid.WidgetWrap):

    item_col_size = 12

    def selectable(self):
        return True

    def __init__(self, item, long_description):
        self.item = item
        self.desc = long_description
        w = urwid.Columns([
            (DataRow.item_col_size, urwid.Text(self.item)),
            urwid.Text(self.desc)])
        self._w = urwid.AttrMap(w, "body", "bkgnd_white")

        urwid.WidgetWrap.__init__(self, self._w)

    def keypress(self, size, key):
        # dummy keypress needed to pass back the key handling
        return key


class MyButton(urwid.Button):
    """
    Use the ButtonLabel class to decorate the button instead of the standard
    SelectableIcon class. The button end chars are also changed to make them
    more visually appealing
    """

    button_left = "["
    button_right = "]"

    def __init__(self, label, on_press=None, user_data=None):
        self._label = ButtonLabel("")
        cols = urwid.Columns([
            ('fixed', len(self.button_left), urwid.Text(self.button_left)),
            self._label,
            ('fixed', len(self.button_right), urwid.Text(self.button_right))],
            dividechars=1)

        super(urwid.Button, self).__init__(cols)

        if on_press:
            urwid.connect_signal(self, 'click', on_press, user_data)

        self.set_label(label)
        self._label.align = 'center'


class FixedEdit(urwid.Edit):
    """Edit fields with fixed maximum length and validation"""

    def __init__(self, caption="",
                 edit_text="", multiline=False,
                 align='left', wrap='any', allow_tab=False,
                 valid_chars=string.printable,
                 width=0):

        self.max_width = width
        self.valid_chars = valid_chars

        urwid.Edit.__init__(self,
                            caption=caption,
                            edit_text=edit_text,
                            multiline=multiline,
                            align=align,
                            wrap=wrap,
                            allow_tab=allow_tab)

    def keypress(self, (maxcol,), key):
        rc = urwid.Edit.keypress(self, (maxcol,), key)

        if len(self.edit_text) > self.max_width:
            self.edit_text = self.edit_text[0:self.max_width]

        return rc

    def valid_char(self, ch):
        # if the field is full disregard the keypress
        if len(self.edit_text) == self.max_width:
            return False
        else:
            # otherwise check for the validity of the key
            return True if ch in self.valid_chars else False


class FilteredEdit(urwid.Edit):
    """Edit fields with fixed maximum length and validation"""

    def __init__(self, caption="",
                 edit_text="", multiline=False,
                 align='left', wrap='any', allow_tab=False,
                 valid_chars=string.printable):

        self.valid_chars = valid_chars

        urwid.Edit.__init__(self,
                            caption=caption,
                            edit_text=edit_text,
                            multiline=multiline,
                            align=align,
                            wrap=wrap,
                            allow_tab=allow_tab)

    def keypress(self, (maxcol,), key):
        rc = urwid.Edit.keypress(self, (maxcol,), key)
        return rc

    def valid_char(self, ch):
        # check for the validity of the key
        return True if ch in self.valid_chars else False


class UIBaseClass(urwid.WidgetWrap):

    title = "TITLE MISSING"
    hint = ""
    alphanum = string.digits + string.letters

    def __init__(self, parent):
        self.parent = parent

        urwid.WidgetWrap.__init__(self,
                                  self.render_page)

    @classmethod
    def lineno(cls):
        (_s, line_no) = inspect.getsourcelines(cls)
        return line_no

    @property
    def render_page(self):
        return urwid.AttrMap(urwid.Filler(urwid.Text("Default page"),
                                          valign='top', top=2),
                             'active_step')

    def refresh(self):
        return


def ui_button(label='Next', align='right', callback=None):
    btn_size = len(label) + 4
    return urwid.Padding(
             urwid.GridFlow([
               urwid.AttrMap(
                 MyButton(label=label, on_press=callback),
                 # urwid.Button(label=label, on_press=callback),
                 'buttn', 'buttnf')],
               btn_size, 4, 0, align=align),
             left=2, right=2)


def button_row(button_list, align='right'):

    buttons = []                            # list of tuples - label, callback
    for button in button_list:
        buttons.append(urwid.AttrMap(
                         MyButton(label=button[0], on_press=button[1]),
                       'buttn', 'buttnf'))

    return urwid.Padding(urwid.GridFlow(buttons, 12, 4, 0, align=align),
                         left=2, right=2)
