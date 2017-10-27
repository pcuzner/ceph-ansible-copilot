import urwid
from .base import UIBaseClass, FixedEdit, ui_button
from ceph_ansible_copilot.utils import user_exists, get_selected_button


class UI_Environment(UIBaseClass):
    title = "Environment"
    hint = "These settings define the basic constraints for the installer"
    seq_no = 2

    def __init__(self, parent):

        software_src_list = ['RH CDN', 'Distro', 'Community']
        osd_types = ['filestore', 'bluestore']
        dmcrypt_settings = ['standard', 'encrypted']

        cfg = parent.cfg

        self.sw_source_group = []
        self.osd_type = []
        self.dmcrypt_group = []

        self.text = (
            "Environment\n\nDefine the types of environment settings that "
            "will determine the way the cluster is installed and configured."
        )

        # self.cluster_name = FixedEdit(caption="Cluster Name    : ",
        #                               width=12,
        #                               valid_chars=self.alphanum)
        # self.cluster_name.edit_text = 'ceph'
        self.deployment_user = FixedEdit("Deployment User : ", width=8,
                                         valid_chars=self.alphanum)
        self.deployment_user.edit_text = 'root'

        software_buttons = [urwid.RadioButton(self.sw_source_group, txt,
                                              state=False)
                            for txt in software_src_list]
        software_buttons[software_src_list.index(cfg.defaults.sw_src)].state = True
        self.software_sources = urwid.GridFlow(software_buttons,
                                14, 4, 0, align='left')

        osd_buttons = [urwid.RadioButton(self.osd_type, txt,
                                         state=False)
                       for txt in osd_types]
        osd_buttons[osd_types.index(cfg.defaults.osd_objectstore)].state=True
        self.osd_options = urwid.GridFlow(osd_buttons,
                                          14, 4, 0, align='left')

        dmcrypt_buttons = [urwid.RadioButton(self.dmcrypt_group, txt,
                                         state=False)
                       for txt in dmcrypt_settings]
        dmcrypt_buttons[dmcrypt_settings.index(cfg.defaults.dmcrypt)].state = True
        self.dmcrypt_options = urwid.GridFlow(dmcrypt_buttons,
                                          14, 4, 0, align='left')
        self.next_btn = ui_button(callback=self.validate)

        UIBaseClass.__init__(self, parent)

    def validate(self, button):
        app = self.parent
        cfg = app.cfg

        # validate the settings are acceptable
        ansible_user = self.deployment_user.get_edit_text()

        # does the deployment user exist?
        if not user_exists(ansible_user):
            app.show_message("Error: User '{}' does not "
                             "exist".format(ansible_user))

        # then set the data dict to contain the relevant information from this
        # page

        # self.data['cluster_name'] = self.cluster_name.get_edit_text()
        # cfg.settings.cluster_name = self.cluster_name.get_edit_text()

        # self.data['deployment_user'] = ansible_user
        cfg.deployment_user = ansible_user
        # self.data['osd_objectstore'] = get_selected_button(self.osd_type)
        cfg.osd_objectstore = get_selected_button(self.osd_type)
        # self.data['sw_source'] = get_selected_button(self.sw_source_group)
        cfg.sw_source = get_selected_button(self.sw_source_group)

        if get_selected_button(self.dmcrypt_group) == 'encrypted':
            cfg.dmcrypt = 'true'
            # self.data['dmcrypt'] = 'true'
        else:
            # self.data['dmcrypt'] = 'false'
            cfg.dmcrypt = 'false'

        app.next_page()

    @property
    def render_page(self):

        names = urwid.Padding(
            urwid.Pile([
                # urwid.AttrMap(self.cluster_name, 'editbox'),
                # urwid.AttrMap(self.cluster_network, 'editbox'),
                urwid.AttrMap(self.deployment_user, 'editbox')]),
            left=2,
            right=2
        )

        software = urwid.Padding(
            urwid.Pile([
                urwid.Text("Select the type of software source below"),
                self.software_sources,
            ]),
            left=2,
            right=2
        )

        osd_setting = urwid.Padding(
            urwid.Pile([
                urwid.Text("Select the OSD type"),
                self.osd_options,
                urwid.Divider(),
                urwid.Text("Select the level of data security on OSDs"),
                self.dmcrypt_options
            ]),
            left=2,
            right=2
        )

        return urwid.AttrMap(urwid.Filler(urwid.Pile([
            urwid.Padding(urwid.Text(self.text), left=2, right=2),
            urwid.Divider(),
            names,
            urwid.Divider(),
            software,
            urwid.Divider(),
            osd_setting,
            urwid.Divider(),
            self.next_btn]), valign='top', top=1),
            'active_step')
