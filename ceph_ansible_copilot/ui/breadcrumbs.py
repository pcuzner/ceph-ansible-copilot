
import urwid

from .base import UIBaseClass


class Breadcrumbs(UIBaseClass):

    breadcrumb_width = 17           # width of the left hand pane

    def __init__(self, parent, steps):
        UIBaseClass.__init__(self, parent)

        self.steps = steps
        self.position = 0

        urwid.WidgetWrap.__init__(self,
                                  self.breadcrumbs)

    @property
    def breadcrumbs(self):
        return urwid.AttrMap(
                 urwid.Filler(
                   urwid.Pile(self._build_sections()),
                   valign='top', top=1),
                 'inactive_step')

    def _build_sections(self):
        widgets = []
        item_ptr = 0
        for item in self.steps:

            if item_ptr == self.position:
                disp_attr = 'active_step'
            else:
                disp_attr = 'inactive_step'

            widgets.append(urwid.AttrMap(
                             urwid.Text(' {}'.format(item)),
                             disp_attr))
            item_ptr += 1
        return widgets

    def update(self, position=None):

        if not position:
            if self.position < len(self.steps) - 1:
                self.position += 1
        else:
            self.position = position
