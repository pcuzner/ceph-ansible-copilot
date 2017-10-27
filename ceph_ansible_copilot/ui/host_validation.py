import urwid
from .base import UIBaseClass, ui_button, TableRow
from ceph_ansible_copilot.ansible import ResultCallback, DynamicPlaybook


class UI_Host_Validation(UIBaseClass):
    title = "Host Validation"
    hint = ("Validation can show issues that would prevent a successful "
            "deployment")
    seq_no = 4

    pb_tasks = [dict(name="setup module",
                     action=dict(module="setup", args=""))
                ]

    def __init__(self, parent):

        self.text = (
            "Host Validation\n\nThe hosts have already been checked for "
            "DNS and passwordless SSH. The next step is to 'probe' the hosts "
            "to validate that their configuration matches the intended Ceph "
            "role."
        )

        self.probe_btn = ui_button(label='Probe', align='center',
                                   callback=self.probe)
        self.next_btn = ui_button(label='Next', align='right',
                                  callback=self.next_page)

        self.table_body = urwid.SimpleListWalker([])
        self.table = urwid.ListBox(self.table_body)
        self.table_footer = urwid.Text(
            "Use arrow keys to move, 'space' to toggle the use of a host")
        self.probed = False

        UIBaseClass.__init__(self, parent)

    def probe(self, button):

        app = self.parent
        cfg = app.cfg
        hosts = app.hosts

        host_list = sorted(hosts.keys())
        app.show_message("Probing hosts...") #, immediate=True)

        self.clear_table()

        probe_callback = ResultCallback(self.parent.progress_bar_update,
                                        logger=self.parent.log)

        probe_playbook = DynamicPlaybook(host_list=host_list,
                                         callback=probe_callback)
        probe_playbook.setup(pb_name='Probe Hosts',
                             pb_tasks=self.pb_tasks
                             )

        # turn the progress bar on
        app.progress_bar(complete=len(host_list))

        rc = probe_playbook.run()

        # turn the progress bar off
        app.progress_bar()

        msg = ("Probe complete : {} successful, {} failed, "
               "{} unreachable".format(probe_callback.stats['task_state']
                                                           ['success'],
                                       probe_callback.stats['task_state']
                                                           ['failed'],
                                       probe_callback.stats['task_state']
                                                           ['unreachable']))

        for host in probe_callback.stats['successes']:
            hosts[host].seed(probe_callback.stats['successes'][host])

        self.validate()
        self.probed = True
        self.populate_table()

        app.refresh_ui()
        app.loop.widget = self.parent.top
        app.loop.draw_screen()

        # must be done after the draw screen due to the rendering of the table
        # rows updating the copilot msg widget
        app.show_message(msg, immediate=True)

    def validate(self):
        return

    def clear_table(self):
        app = self.parent

        self.table_body = urwid.SimpleFocusListWalker([])
        app.refresh_ui()
        app.loop.widget = app.top
        app.loop.draw_screen()

    def populate_table(self):
        app = self.parent

        table_rows = []
        for hostname in sorted(app.hosts.keys()):
            # establish column field defaults
            if app.hosts[hostname]._facts:
                this_host = app.hosts[hostname]
                w = urwid.AttrMap(TableRow(this_host.info(), app),
                                  'body',
                                  'reverse')
                table_rows.append(w)

        self.table_body = urwid.SimpleListWalker(table_rows)

        # urwid.connect_signal(self.table_body, "modified", self.show_row_state)

        return

    def next_page(self, button):

        app = self.parent
        hosts = self.parent.hosts
        cfg = self.parent.cfg

        if self.probed:

            osd_hosts = [h for h in hosts
                         if hosts[h].selected and 'osd' in hosts[h].roles
                         and hosts[h].state.lower() == 'ready']

            journals_available = all(hosts[h].ssd_count > 0
                                     for h in osd_hosts)
            if not journals_available:
                cfg.osd_scenario = 'collocated'
                # self.data['osd_scenario'] = 'collocated'
            else:
                cfg.osd_scenario = 'non-collocated'
                # self.data['osd_scenario'] = 'non-collocated'

            app.next_page()
        else:
            app.show_message("Error: Before continuing, the hosts must be probed")

    @property
    def render_page(self):

        table_headings = [(3, urwid.Text('Sel')),
                          (4, urwid.Text('Role')),
                          (12, urwid.Text('Hostname')),
                          (4, urwid.Text('CPU ')),
                          (3, urwid.Text('RAM')),
                          (3, urwid.Text('NIC')),
                          (3, urwid.Text('HDD')),
                          (3, urwid.Text('SSD')),
                          (4, urwid.Text('Size')),
                          (8, urwid.Text('Status'))]

        table_header = urwid.Columns(table_headings, 1)

        self.table = urwid.ListBox(self.table_body)

        results = urwid.Padding(
                    urwid.BoxAdapter(
                        urwid.LineBox(
                            urwid.Frame(self.table,
                                        header=table_header,
                                        footer=self.table_footer),
                            title="Host Configuration"),
                        13),
                    left=1,
                    right=1)

        return urwid.AttrMap(
                 urwid.Filler(
                   urwid.Pile([
                               urwid.Padding(urwid.Text(self.text),
                                             left=2, right=2),
                               # urwid.Divider(),
                               self.probe_btn,
                               urwid.Divider(),
                               results,
                               # urwid.Divider(),
                               self.next_btn]),
                   valign='top', top=1),
                 'active_step')

