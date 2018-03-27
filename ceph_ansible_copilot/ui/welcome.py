import urwid
from .base import UIBaseClass, ui_button

class UI_Welcome(UIBaseClass):
    title = "Welcome"
    hint = "Click 'next' to continue"
    seq_no = 1

    def __init__(self, parent):

        self.next_btn = ui_button(callback=self.validate)

        self.text = (
            "{}\n\nCo-Pilot provides a simple to use, guided workflow to "
            "install your Ceph Cluster. Host selection and deployment "
            "readiness is validated prior to the installation process "
            "starting and installation itself is monitored within this "
            "interface.\n\n"
            "If errors are encountered during deployment, co-pilot will "
            "show you the errors, and allow you to rerun the "
            "deployment.".format(self.title)
        )

        UIBaseClass.__init__(self, parent)

    def validate(self, button):
        app = self.parent
        # nothing to validate in the welcome screen!
        app.next_page()

    @property
    def render_page(self):
        return urwid.AttrMap(
            urwid.Filler(urwid.Pile([urwid.Padding(urwid.Text(self.text),
                                                   left=2, right=2),
                                     urwid.Divider(),
                                     self.next_btn]),
                         valign='top', top=1),
            'active_step')
