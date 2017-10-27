
import urwid

from .base import UIBaseClass, ui_button


class UI_Commit(UIBaseClass):
    title = "Commit Changes"
    hint = (
        "Prior to updating files, the old version is saved with a "
        "timestamp suffix"
    )
    seq_no = 6

    def __init__(self, parent):

        app = parent

        self.text = (
            "Commit\n\nThe commit phase will update configuration files "
            "to prepare the installer. {} plugins have been found that will "
            "be used to update the installer's configuration files. Once the "
            "commit is done, you may continue to the deploy phase, or exit "
            "'co-pilot' and run the deployment process "
            "manually".format(len(app.plugin_mgr.plugins)))

        self.next_btn = ui_button(label="Commit", callback=self.validate)

        UIBaseClass.__init__(self, parent)

    def validate(self, button):
        app = self.parent

        btn_text = self.next_btn.base_widget[0].get_label()
        if btn_text == "Commit":

            # Attempt to run the plugins registered with the main App object
            status = app.execute_plugins()

            if status['failed'] == 0:
                app.check_keys()
                app.next_page()
            else:
                self.next_btn.base_widget[0].set_label("Quit")
                app.show_message("Error: the commit process encountered "
                                 "{} failure. Please check the copilot "
                                 "log".format(status['failed']))
        else:
            raise urwid.ExitMainLoop

    @property
    def render_page(self):
        return urwid.AttrMap(
                 urwid.Filler(
                   urwid.Pile([
                     urwid.Padding(
                       urwid.Text(self.text),
                       left=2, right=2),
                     urwid.Divider(),
                     self.next_btn]),
                   valign='top', top=1),
                 'active_step')
