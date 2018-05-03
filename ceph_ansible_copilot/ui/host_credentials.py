
import urwid
from .base import UIBaseClass, ui_button, FixedEdit, SelectableText
import threading


class UI_Credentials(UIBaseClass):
    title = "Host Access"
    seq_no = 4
    hint = ("If your hosts use the same password, use the 'Common "
            "Password' feature.")

    password_length = 20

    def __init__(self, parent=None):

        self.text = (
            "{}\n\nClick 'Check' to confirm passwordless is setup. For hosts "
            "that have an AUTHFAIL/NOPASSWD status, enter the root password "
            "and check again.".format(self.title))

        self.check_btn = ui_button(label='  Check  ', align='right',
                                   callback=self.check_access)

        self.enable_password = urwid.CheckBox("Common Password",
                                              state=False,
                                              on_state_change=self.common_pswd_toggle)

        self.common_password = urwid.AttrMap(
                    FixedEdit(edit_text="",
                              multiline=False, width=self.password_length),
                    "title")

        urwid.connect_signal(self.common_password.base_widget,
                             'change',
                             callback=self.common_pswd_change)

        # pending access table elements
        self.pending_table_headings = urwid.Columns([
            (12, urwid.Text('Hostname')),
            (10, urwid.Text('Status')),
            (self.password_length, urwid.Text('Password'))
            ], dividechars=1)
        self.pending_table_title = urwid.Text("Access Pending",
                                              align='center')
        self.pending_table_body = urwid.SimpleListWalker([])
        self.pending_table = urwid.ListBox(self.pending_table_body)

        # ssh ok table elements
        self.sshok_table_title = urwid.Text("Access OK",
                                            align='left')
        self.sshok_table_headings = urwid.Columns([
            (12, urwid.Text('Hostname'))
            ])
        self.sshok_table_body = urwid.SimpleListWalker([])
        self.sshok_table = urwid.ListBox(self.sshok_table_body)

        self.debug = None                   # Unused

        # instance uses a mutex to control updates to the screen when the
        # ssh setup method is called in parallel across each host
        self.table_mutex = threading.Lock()

        UIBaseClass.__init__(self, parent)
        # self.widget_in_focus = 4

    def _update_hosts(self, hosts):
        """
        Extract the hostname and password from the UI and update the
        hosts dict
        :param hosts (dict): dictionary of hosts
        :return: None
        """

        rows = self.pending_table_body.contents
        for row in rows:
            w = row.original_widget
            contents = w.contents

            hostname = contents[0][0].text
            password = contents[2][0].text

            hosts[hostname].ssh.password = password

    def check_access(self, button):
        """
        User clicked 'check' or 'Next' so we update the hosts dict with the
        current settings from the UI and call each hosts ssh object's setup
        method in parallel to check DNS and ssh access is in place
        :param button: UI button pressed
        :return: None
        """

        btn_label = button.get_label()
        if btn_label == 'Next':
            self.next_page()

        button.set_label("Checking")

        app = self.parent
        hosts = app.hosts

        self._update_hosts(hosts)
        callback = self.refresh

        app.log.debug("Starting ssh threads {}".format(len(hosts.keys())))
        threads = []
        for hostname in sorted(hosts.keys()):
            this_host = hosts[hostname]
            if not this_host.ssh.ok:
                _t = threading.Thread(target=this_host.ssh.setup,
                                      args=(callback,))
                _t.start()
                app.log.debug("Started ssh thread for {}".format(hostname))
                threads.append(_t)

        for _t in threads:
            _t.join()
        app.log.debug("All ssh threads complete")
        for hostname in sorted(hosts.keys()):
            this_host = hosts[hostname]
            app.log.debug("SSH status for {} is "
                          "{}".format(hostname, this_host.ssh.status_code))

        if len(self.pending_table_body) == 0:
            button.set_label('Next')
        else:
            button.set_label('Check')

    def next_page(self):
        # disconnect the signal handler setup by __init__
        urwid.disconnect_signal(self.common_password.base_widget,
                                'change',
                                callback=self.common_pswd_change)
        app = self.parent
        app.next_page()

    def refresh(self):
        """
        refresh is called locally within this page element, and also as a
        callback from the ssh setup method (hence the mutex). It is responsible
        for maintaining the 'pending' and 'access ok' tables shown in the UI
        based on the current state of the hosts dict
        :return: None
        """

        self.table_mutex.acquire()

        app = self.parent
        hosts = app.hosts
        pending_access_items = []
        ssh_ok_items = []

        for hostname in sorted(hosts.keys()):
            this_host = hosts[hostname]

            if this_host.ssh.status_code != 0:
                w = urwid.AttrMap(
                        urwid.Columns([
                            (12, urwid.Text(this_host.hostname)),
                            (10, urwid.Text(this_host.ssh.shortmsg)),
                            (self.password_length,
                             FixedEdit(edit_text=this_host.ssh.password,
                                       width=self.password_length))
                        ], dividechars=1), "active_step", "reversed")
                pending_access_items.append(w)
            else:

                w = urwid.Columns([
                        urwid.AttrMap(
                            SelectableText(this_host.hostname),
                            "active_step", "reversed_green")
                        ])
                ssh_ok_items.append(w)

        self.pending_table_body[:] = pending_access_items
        self.sshok_table_body[:] = ssh_ok_items

        # Update the table headings to show progress
        self.pending_table_title.set_text(
            "Access Pending({})".format(len(self.pending_table_body)))
        self.sshok_table_title.set_text(
            "Access OK({}/{})".format(len(self.sshok_table_body),
                                      len(hosts.keys())))

        if hasattr(app, 'loop'):
            # performing a screen redraw here enables the ssh setup threads to
            # update the UI instead of waiting for the thread to complete
            app.loop.draw_screen()

        self.table_mutex.release()

        return

    def common_pswd_change(self, *args):

        if self.enable_password.state is True:
            new_password = self.common_password.original_widget.edit_text
            self._update_passwords(new_password)

        else:
            # change registered, but checkbox not active so this is a NOOP
            pass

    def _update_passwords(self, new_password):
        """
        Update the password field of all rows within the pending access table
        :param new_password (str): password to use to update all hosts with
        :return: None
        """

        rows = self.pending_table_body.contents
        for row in rows:
            w = row.original_widget
            contents = w.contents
            pswd = contents[2][0]
            pswd.set_edit_text(new_password)

    def common_pswd_toggle(self, *args):
        # set the selected state for each host listed
        new_password = self.common_password.original_widget.edit_text
        if self.enable_password.state is False:         # State before call
            if new_password:
                self._update_passwords(new_password)

    @property
    def render_page(self):

        w = urwid.Pile([
                  urwid.Padding(urwid.Text(self.text),
                                left=1, right=1),
                  urwid.Divider(),
                  urwid.Padding(
                    urwid.Columns([
                        ("fixed", 20, self.enable_password),
                        ("fixed", 22, self.common_password)
                        ]),
                    left=1),
                  urwid.Divider(),
                  urwid.Padding(
                      urwid.Columns([
                          ("weight", 3, urwid.Pile([
                              self.pending_table_title,
                              urwid.BoxAdapter(
                                urwid.Frame(self.pending_table,
                                            header=self.pending_table_headings),
                                10),
                          ])),
                          ("weight", 1, urwid.Pile([
                              self.sshok_table_title,
                              urwid.BoxAdapter(
                                  urwid.Frame(self.sshok_table,
                                              header=self.sshok_table_headings),
                                  10),
                          ]))
                      ], dividechars=1),
                      left=1),
                  self.check_btn
              ])

        w.focus_position = 5                # the Check button widget

        return urwid.AttrMap(
                 urwid.Filler(w, valign='top', top=1),
                 "active_step")
