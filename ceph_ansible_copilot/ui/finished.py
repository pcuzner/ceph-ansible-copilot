
import urwid
from .base import UIBaseClass, ui_button


class UI_Finish(UIBaseClass):

    title = "Finish"
    hint = "Exit co-pilot"
    seq_no = 8

    def __init__(self, parent):
        self.text = (
            "The deployment is complete")

        self.btn = ui_button(label='Exit', callback=self.quit_ui)

        UIBaseClass.__init__(self, parent)

    def quit_ui(self, button):
        # just leave for now..
        raise urwid.ExitMainLoop

    @property
    def render_page(self):
        return urwid.AttrMap(
                 urwid.Filler(
                   urwid.Pile([
                     urwid.Padding(urwid.Text(self.title), left=2),
                     urwid.Divider(),
                     urwid.Padding(urwid.Text(self.text), left=2, right=2),
                     urwid.Divider(),
                     self.btn]),
                   valign='top', top=1),
                 'active_step')
