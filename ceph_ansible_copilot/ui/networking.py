import urwid
from .base import UIBaseClass, ui_button

class UI_Network(UIBaseClass):
    title = "Network"
    hint = (
        "For production, dedicated public and cluster networks are "
        "recommended"
    )
    seq_no = 5

    def __init__(self, parent):

        self.text = (
            "Network Configuration\n\nDuring the host probes, the available "
            "networks have been autodetected. Networks that are common to all "
            "hosts appear on the left, and networks common to all OSD hosts "
            "are shown on the right."
        )

        self.public_grp = []
        self.cluster_grp = []
        public_networks = []
        cluster_networks = []

        self.public_buttons = urwid.Pile([urwid.RadioButton(self.public_grp,
                                                            txt)
                                          for txt in public_networks])
        self.cluster_buttons = urwid.Pile([urwid.RadioButton(self.cluster_grp,
                                                             txt)
                                           for txt in cluster_networks])

        self.next_btn = ui_button(callback=self.validate)

        UIBaseClass.__init__(self, parent)

    def _get_public_networks(self):
        """ subnets shared by ALL hosts """
        app = self.parent
        cfg = app.cfg
        hosts = cfg.hosts

        # get a list of all networks
        all_subnets = set()
        candidate_subnets = []
        for host_name in hosts:
            all_subnets.update(app.cfg.hosts[host_name].subnets)

        # process each one
        for net in all_subnets:
            if all(net in hosts[host_name].subnets for host_name in hosts):
                candidate_subnets.append(net)

        return candidate_subnets

    def _get_cluster_networks(self):
        """ subnets shared by OSD hosts """
        app = self.parent
        cfg = app.cfg
        hosts = cfg.hosts

        # get a list of all networks
        osd_subnets = set()
        candidate_subnets = []
        osd_hosts = [host_name for host_name in hosts
                     if 'osd' in hosts[host_name].roles]
        for host_name in osd_hosts:
            osd_subnets.update(hosts[host_name].subnets)

        # process each one
        for net in osd_subnets:
            if all(net in hosts[host_name].subnets for host_name in osd_hosts):
                candidate_subnets.append(net)

        return candidate_subnets

    def validate(self, button):
        # get and set the selected networks based on the radio button settings
        app = self.parent
        cfg = app.cfg
        hosts = cfg.hosts

        public = [btn.get_label() for btn in self.public_grp
                  if btn.state is True]
        cluster = [btn.get_label() for btn in self.cluster_grp
                   if btn.state is True]

        if public:
            cfg.public_network = public[0]
            # self.data['public_network'] = public[0]
            cfg.cluster_network = cluster[0]
            # self.data['cluster_network'] = cluster[0]
            app.next_page()
        else:
            app.show_message("Error: public network selection unavailable")
            return

    def refresh(self):
        """ populate the UI elements from the gathered host data """
        app = self.parent

        public_networks = self._get_public_networks()
        cluster_networks = self._get_cluster_networks()
        if not public_networks:
            app.show_message("Error: Hosts do not share a common subnet "
                             "for the public network")
            return

        if not cluster_networks:
            cluster_networks = public_networks

        self.public_buttons = urwid.Pile([
                                  urwid.RadioButton(self.public_grp, txt)
                                  for txt in public_networks])

        self.cluster_buttons = urwid.Pile([
                                 urwid.RadioButton(self.cluster_grp, txt)
                                 for txt in cluster_networks])

    @property
    def render_page(self):

        return urwid.AttrMap(
                 urwid.Filler(
                   urwid.Pile([
                     urwid.Padding(
                       urwid.Text(self.text),
                       left=2, right=2),
                     urwid.Divider(),
                     urwid.Columns([
                         urwid.Pile([
                             urwid.Text("Public Network", align="center"),
                             urwid.Padding(self.public_buttons,left=4)
                         ]),
                         urwid.Pile([
                             urwid.Text("Cluster Network", align="center"),
                             urwid.Padding(self.cluster_buttons, left=4)
                         ])
                     ]),
                     urwid.Divider(),
                     self.next_btn
                   ]),
                   valign='top', top=1),
                 'active_step')

