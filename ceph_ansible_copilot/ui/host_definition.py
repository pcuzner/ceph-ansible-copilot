import urwid
import string
import re

from .base import (UIBaseClass,
                   FilteredEdit,
                   ui_button)

from ceph_ansible_copilot.utils import (expand_hosts,
                                        check_dns,
                                        check_ssh_access)

from ceph_ansible_copilot import Host


class UI_Host_Definition(UIBaseClass):
    title = "Host Definition"
    hint = ("You can define a host as a name, or a mask e.g. myhost1 or "
            "myhost[1-3]")
    seq_no = 3
    host_name_chars = (string.digits + string.letters + '[]-')

    def __init__(self, parent):
        # self.hosts_ok = False
        self.text = (
            "Host Definition\n\nIn the boxes below enter the names, or "
            "hostname masks for the servers that will become members of "
            "a Ceph cluster"
        )

        self.mons =FilteredEdit(multiline=True,
                                valid_chars=self.host_name_chars)
        self.mon_list = urwid.BoxAdapter(
                          urwid.AttrMap(
                     urwid.LineBox(urwid.AttrMap(
                         urwid.Filler(self.mons, 'top'), "body"),
                         title='MONs'), "body"), 14)
        urwid.connect_signal(self.mons, "change", self.check_mon_input)

        self.osds = FilteredEdit(multiline=True,
                                 valid_chars=self.host_name_chars)
        self.osd_list = urwid.BoxAdapter(
                          urwid.AttrMap(
                            urwid.LineBox(urwid.AttrMap(
                         urwid.Filler(self.osds, 'top'), "body"),
                         title='OSDs'), "body"), 14)
        urwid.connect_signal(self.osds, "change", self.check_osd_input)

        self.rgws = FilteredEdit(multiline=True,
                                 valid_chars=self.host_name_chars)
        self.rgw_list = urwid.BoxAdapter(
                          urwid.AttrMap(
                     urwid.LineBox(urwid.AttrMap(
                         urwid.Filler(self.rgws, 'top'), "body"),
                         title='RGWs'), "body"),14)
        urwid.connect_signal(self.rgws, "change", self.check_rgw_input)

        self.mdss = FilteredEdit(multiline=True,
                                 valid_chars=self.host_name_chars)
        self.mds_list = urwid.BoxAdapter(
                          urwid.AttrMap(
                          urwid.LineBox(urwid.AttrMap(
                            urwid.Filler(self.mdss, 'top'), "body"),
                            title='MDSs'), "body"), 14)

        urwid.connect_signal(self.mdss, "change", self.check_mds_input)

        self.lbox_lookup = {"mons": self.mon_list,
                            "osds": self.osd_list,
                            "rgws": self.rgw_list,
                            "mdss": self.mds_list
                            }

        self.host_panels = urwid.Columns([
                                       self.mon_list,
                                       self.osd_list,
                                       self.rgw_list,
                                       self.mds_list], min_width=10)

        self.next_btn = ui_button(callback=self.validate)

        self.valid_hosts = {
            "mons": True,
            "rgws": True,
            "osds": True,
            "mdss": True
        }

        UIBaseClass.__init__(self, parent)

    def hostname_ok(self, hostname):
        pattern_chars = ['[', ']']


        # just check for hostname mask syntax
        if any(s in hostname for s in pattern_chars):
            # regex = re.compile("^[\w]+[\[][\d]+[\-][\d]+[\]]")
            regex = re.compile("[a-zA-Z0-9\-][[]\d-\d[]]$")
            if regex.search(hostname.rstrip()):
                brkt_pos = hostname.index('[')
                sfx_range = hostname[brkt_pos+1:-1].split('-')
                if int(sfx_range[0]) >= int(sfx_range[1]):
                    return "invalid numeric range, must be low-high"

            else:
                return "invalid hostname pattern - {}".format(hostname)


        return 'ok'

    def _check_input(self, newtext, host_type):
        app = self.parent

        # check the syntax of the host text conforms to hostname or host
        # pattern syntax

        lbox = self.lbox_lookup[host_type]

        host_lines = newtext.split('\n')
        host_count = 0
        self.valid_hosts[host_type] = True
        # hosts_ok = True
        for host in host_lines:
            if host:
                host_count += 1
                host_state = self.hostname_ok(host)
                if host_state != 'ok':
                #     self.hosts_ok = True
                #     pass
                # else:
                    # houston, we have a problem
                    # self.hosts_ok = False
                    self.valid_hosts[host_type] = False
                #base_widget gives fixededit
                # original widget gives the container
                # orginal.base gives the filtered edit

                    lbox.original_widget.set_attr_map({None: "error_box"})
                    app.show_message('Error: {}'.format(host_state))


        # if self.hosts_ok:
        if self.valid_hosts[host_type]:
            # set the linebox attr to body
            lbox.original_widget.set_attr_map({None: "body"})

            app.show_message('')

    def check_mon_input(self, widget, newtext):
        self.host_panels.focus_position = 0
        self._check_input(newtext, "mons")

    def check_osd_input(self, widget, newtext):
        self.host_panels.focus_position = 1
        self._check_input(newtext, "osds")

    def check_rgw_input(self, widget, newtext):
        self.host_panels.focus_position = 2
        self._check_input(newtext, "rgws")

    def check_mds_input(self, widget, newtext):
        self.host_panels.focus_position = 3
        self._check_input(newtext, "mdss")

    def validate(self, button):
        app = self.parent
        cfg = app.cfg
        hosts = cfg.hosts

        # all hosts entered must be valid
        if not all(self.valid_hosts[host_type] is True
                   for host_type in self.valid_hosts):
            return

        mons = expand_hosts(self.mon_list.base_widget.edit_text)
        osds = expand_hosts(self.osd_list.base_widget.edit_text)
        rgws = expand_hosts(self.rgw_list.base_widget.edit_text)
        mdss = expand_hosts(self.mds_list.base_widget.edit_text)

        # with the list expanded, the next thing to check is the deployment
        # rules
        # TODO

        host_list = list(set(mons + osds + rgws + mdss))

        app.show_message("Checking DNS for {} "
                         "hosts".format(len(host_list)),
                         immediate=True)

        lookup_errors = check_dns(host_list)
        if lookup_errors:
            ctx = 'host' if len(lookup_errors) == 1 else 'hosts'
            app.show_message('Error: DNS resolution issues with {}: '
                             '{}'.format(ctx, ','.join(lookup_errors)))
            return

        app.show_message("Checking passwordless ssh is configured",
                         immediate=True)
        ssh_errors = check_ssh_access(host_list=host_list)
        if ssh_errors:
            app.show_message('Error: Passwordless ssh access failed'
                                 ' for; {}'.format(','.join(ssh_errors)))
            return


        # all provided hosts resolve, so lets continue
        # self.data['mon_list'] = mons
        # self.data['osd_list'] = osds
        # self.data['rgw_list'] = rgws
        # self.data['mds_list'] = mdss
        cfg.mons = mons
        cfg.osds = osds
        cfg.rgws = rgws
        cfg.mdss = mdss

        # Create the host objects
        for hostname in host_list:
            roles = []
            if hostname in mons:
                roles.append('mon')
            if hostname in osds:
                roles.append('osd')
            if hostname in rgws:
                roles.append('rgw')
            if hostname in mdss:
                roles.append('mds')

            hosts[hostname] = Host(hostname=hostname,
                                   roles=roles)

        app.next_page()

    @property
    def render_page(self):

        host_widgets = urwid.Padding(self.host_panels,
                                    left=2, right=2)


        return urwid.AttrMap(
                 urwid.Filler(
                   urwid.Pile([
                               urwid.Padding(urwid.Text(self.text),
                                             left=2, right=2),
                               urwid.Divider(),
                               host_widgets,
                               urwid.Divider(),
                               self.next_btn]),
                   valign='top',top=1),
                 'active_step')
