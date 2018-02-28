#!/usr/bin/env python2

import urwid
import inspect
import sys
import os
import traceback
import shutil
import time
import logging
import argparse

import ceph_ansible_copilot

from ceph_ansible_copilot.utils import (PluginMgr, restore_ansible_cfg,
                                        SSHConfig)

from ceph_ansible_copilot.ui import (UI_Welcome,
                                     UI_Environment,
                                     UI_Host_Definition,
                                     UI_Credentials,
                                     UI_Host_Validation,
                                     UI_Network,
                                     UI_Commit,
                                     UI_Deploy,
                                     UI_Finish,
                                     Breadcrumbs,
                                     ProgressOverlay)

from ceph_ansible_copilot.ui.palette import palette

CEPH_ANSIBLE_ROOT = '/usr/share/ceph-ansible'


def unknown_input(key):

    if key == 'esc':
        raise urwid.ExitMainLoop


class Settings(object):

    def __repr__(self):
        items = [(attr, getattr(self, attr))
                 for attr in self.__dict__ if not attr.startswith('_')]
        s = '\n'
        for attr, value in items:
            if isinstance(value, Settings):
                s += '{}:\n'.format(attr)
                sub_items = repr(value).split("\n")
                for i in sub_items[:-1]:
                    s += '- {}\n'.format(i)
            else:
                s += '{}: {}\n'.format(attr, value)
        return s


class Config(Settings):

    # TODO : read a config file to set up defaults
    # and merge with a saved config

    def __init__(self):
        self.defaults = Settings()
        self.defaults.osd_objectstore = 'filestore'
        self.defaults.sw_src = 'RH CDN'
        self.defaults.dmcrypt = 'standard'
        self.defaults.playbook = '/usr/share/ceph-ansible/site.yml'

        self.hosts = None


def get_ui_sections():
    sections = {}

    for name, obj in inspect.getmembers(sys.modules[__name__],
                                        inspect.isclass):
        if name.startswith('UI_'):
            ui_class = getattr(sys.modules[__name__], name)
            if "seq_no" in ui_class.__dict__:
                seq_no = ui_class.seq_no
            else:
                seq_no = ui_class.lineno()
            sections[seq_no] = (ui_class, ui_class.title)

    return sections


class App(object):
    """
    Main control logic object. It constructs the interface from the other
    classes
    """

    def __init__(self):

        pgm = '{} v{}'.format(
                         os.path.splitext(os.path.basename(__file__))[0],
                         ceph_ansible_copilot.__version__)

        banner = urwid.Columns([
            urwid.Text(("title", pgm),
                       align='left'),
            urwid.Text(("title", "[{}]".format(opts.mode)),
                       align='right')
        ])

        self.title = urwid.AttrMap(banner, "title")

        self.timestamp = None
        self.file_timestamp = None
        self.log = None
        self.pagenum = 0
        self.page = []      # list of UI pages/views
        self.pb_active = False
        self.pb_complete = 0
        self.pb = None
        self.debug = None           # used to check state during debugging

        self.plugin_mgr = None
        self.ssh = None

        self.msg = None
        self.msg_text = None
        self.left_pane = None
        self.right_pane = None
        self.top = None

        self.loop = None
        self.cfg = Config()
        self.opts = opts
        self.hosts = dict()

        if opts.playbook:
            self.playbook = opts.playbook
        else:
            self.playbook = self.cfg.defaults.playbook

        self.ansible_cfg = os.path.join(CEPH_ANSIBLE_ROOT, 'ansible.cfg')
        self.ansible_cfg_bkup = '{}_bak'.format(self.ansible_cfg)

    def refresh_ui(self, left=None, right=None):
        if not left:
            left = self.left_pane.breadcrumbs
        if not right:
            right = self.page[self.pagenum].render_page

        body = urwid.Columns([('fixed',
                               Breadcrumbs.breadcrumb_width,
                               left),
                              right])

        self.top = urwid.Frame(body,
                               header=self.title,
                               footer=self.msg)

    def next_page(self):
        if self.pagenum < len(self.page) - 1:
            self.pagenum += 1

        copilot.left_pane.update()
        self.msg_text = self.page[self.pagenum].hint
        self.show_message(self.msg_text)

        new_page = self.page[self.pagenum]
        new_page.refresh()

        copilot.refresh_ui(left=self.left_pane.breadcrumbs,
                           right=new_page.render_page)

        self.loop.widget = self.top

    def execute_plugins(self):

        self.cfg.hosts = self.hosts
        self.cfg.ceph_version = opts.ceph_version
        self.cfg.cluster_name = opts.cluster_name

        self.log.info("Configuration options supplied:")
        self.log.info(self.cfg)

        self.log.info("End of options")

        plugin_status = {
            "successful": 0,
            "failed": 0
        }

        num_plugins = len(self.plugin_mgr.plugins)
        if num_plugins > 0:
            self.log.info("Plugin execution starting..")

        srtd_names = sorted(self.plugin_mgr.plugins.keys())

        plugins = self.plugin_mgr.plugins

        for plugin_name in srtd_names:
            mod = plugins[plugin_name].module
            yml_file = mod.yml_file

            try:
                self.log.info("Plugin: {}".format(plugin_name))
                plugin_data = mod.plugin_main(self.cfg)

                plugins[plugin_name].executed = True

            except BaseException as error:
                # Use BaseException as a catch-all from the plugins
                plugin_status['failed'] += 1
                self.log.error("Plugin '{}' failed : "
                               "{}".format(plugin_name,
                                           sys.exc_info()[0]))
                self.log.debug(traceback.format_exc())
                break
            else:
                plugin_status['successful'] += 1
                if isinstance(plugin_data, tuple):
                    f_type, contents = plugin_data
                    if contents:
                        self.write_yml(yml_file, contents, f_type)
                        self.log.info("Plugin updated {}".format(yml_file))
                    else:
                        self.log.info("Plugin - no data written to "
                                      "{}".format(yml_file))
                elif not plugin_data:
                    self.log.info("backup and update handled by plugin")

        skipped = num_plugins - (plugin_status['successful'] +
                                 plugin_status['failed'])

        self.log.info("{} plugin(s) sucessful, "
                      "{} failed, "
                      "{} skipped".format(plugin_status['successful'],
                                          plugin_status['failed'],
                                          skipped))

        return plugin_status

    def write_yml(self, yml_file, contents, file_type='yml'):
        self.bkup_yml(yml_file)
        contents.insert(0, ' ')
        contents.insert(0, "# created by copilot - only overrides from"
                           " defaults shown {}".format(self.file_timestamp))
        if file_type == 'yml':
            contents.insert(0, '---')

        # unbuffered write
        with open(yml_file, 'w', 0) as f:
            f.write("\n".join(contents))

        # read it back
        with open(yml_file, 'r') as f:
            contents = f.readlines()

    def bkup_yml(self, yml_file):

        if os.path.exists(yml_file):
            yml_file_bkup = '{}_{}'.format(yml_file,
                                           self.timestamp)
            shutil.copy2(yml_file, yml_file_bkup)
            self.log.info("YML file {}, copied to {}".format(yml_file,
                                                             yml_file_bkup))
        else:
            self.log.warning("Existing file {}, not found".format(yml_file))

    def show_message(self, msg_text, immediate=False):
        self.msg_text = msg_text
        msg = msg_text.lower()
        if msg.startswith('error'):
            attr = 'error_message'
        elif msg.startswith('warning'):
            attr = 'warning message'
        else:
            attr = 'message'
        self.msg.set_attr_map({None: attr})
        self.msg.base_widget.set_text(self.msg_text)

        if immediate:
            self.loop.draw_screen()

    def progress_bar(self, complete=0):
        if not self.pb_active:
            # turn on a progress bar
            self.pb_active = True

            self.pb = ProgressOverlay(bottom_w=self.top, complete=complete)
            self.loop.widget = self.pb
            self.loop.draw_screen()
        else:
            # turn the progress bar off
            self.pb_active = False
            self.pb = None
            self.loop.widget = self.top
            self.loop.draw_screen()

    def progress_bar_update(self, stats):
        if self.pb_active:
            task_state = stats['task_state']
            done = sum([task_state[item] for item in task_state])
            self.loop.widget = self.pb.update(done)
            self.loop.draw_screen()

        else:
            return

    def setup(self):

        self.ssh = SSHConfig()
        if not self.ssh.configured:
            print("Unable to access/create ssh keys")
            sys.exit(4)

        self.file_timestamp = time.ctime()
        self.timestamp = int(time.time())
        self.log = setup_logging()
        self.log.info("{} (v{}) starting at "
                      "{}".format(os.path.basename(__file__),
                                  ceph_ansible_copilot.__version__,
                                  self.file_timestamp))

        self._setup_dirs()

        self.plugin_mgr = PluginMgr(logger=self.log)
        self.log.info("{} plugin(s) "
                      "loaded".format(len(self.plugin_mgr.plugins)))

        for plugin_name in self.plugin_mgr.plugins:
            mod = self.plugin_mgr.plugins[plugin_name].module
            self.log.info("- {}".format(mod.__file__[:-1]))     # *.pyc -> *.py

        self.init_UI()

        self.loop = urwid.MainLoop(copilot.top,
                                   palette,
                                   unhandled_input=unknown_input)

    def _setup_dirs(self):

        group_vars = '/etc/ansible/group_vars'
        ceph_ansible_vars = os.path.join(CEPH_ANSIBLE_ROOT, 'group_vars')
        if os.path.exists(group_vars):
            if os.path.realpath(group_vars) == ceph_ansible_vars:
                self.log.info("ceph-ansible group_vars is linked to ansible's"
                              " directory - no change needed")
            else:
                raise EnvironmentError("group_vars already exists, but doesn't"
                                       " point to ceph-ansible group_vars")
        else:
            # Doesn't exists, so create the symlink to ceph-ansible's dir
            if os.path.exists(ceph_ansible_vars):
                os.symlink(ceph_ansible_vars, group_vars)
                self.log.info("Created symlink to ceph-ansible group_vars")
            else:
                raise EnvironmentError("ceph-ansible group_vars not found. Is "
                                       "ceph-ansible installed?")

    def check_keys(self):
        keys_dir = os.path.join(os.path.expanduser('~'), 'ceph-ansible-keys')
        if os.path.exists(keys_dir):
            self.log.info("Ansible keys directory is ready, no action needed")
        else:
            os.mkdir(keys_dir)
            self.log.info("Ansible keys directory created")

    def init_UI(self):
        ui_elements = get_ui_sections()
        section_names = []
        for idx in sorted(ui_elements):
            (page_class, page_title) = ui_elements[idx]
            section_names.append(page_title)
            self.page.append(page_class(self))

        self.left_pane = Breadcrumbs(self, section_names)
        self.right_pane = self.page[self.pagenum]
        self.msg_text = self.page[self.pagenum].hint

        self.msg = urwid.AttrMap(
                     urwid.Text(self.msg_text), 'message')

        self.refresh_ui(left=self.left_pane,
                        right=self.right_pane.render_page)
        return

    def cleanup(self):

        # if we had a site_yml plugin run it again in delete mode
        # to remove the additional include_vars tasks
        if self.plugin_mgr.plugins['site_yml'].executed:
            self.log.info("running site_yml again to remove "
                          "the include_vars task for all.yml")
            mod = self.plugin_mgr.plugins['site_yml'].module
            mod.plugin_main(config=self.cfg, mode='delete')

        # if we have a _bak version of the ansible.cfg, restore it to it's
        # previous state
        restore_ansible_cfg()


def setup_logging():

    log_path = '/var/log/ceph-ansible-copilot.log'
    logger = logging.getLogger("copilot")
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(log_path, mode='w')

    file_format = logging.Formatter(
        '%(asctime)s [%(levelname)-8s] %(message)s')

    file_handler.setFormatter(file_format)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    return logger


def parse_cli_options():

    modes = ['dev', 'prod']                     # 1st entry is the default!
    copilot_version = ceph_ansible_copilot.__version__

    parser = argparse.ArgumentParser(description="ceph-ansible copilot")

    parser.add_argument("--mode", "-m", type=str, choices=modes,
                        default=modes[0],
                        help="type of cluster to be deployed "
                             "(default is {})".format(modes[0]))

    parser.add_argument("--cluster-name", "-n", type=str,
                        default='ceph',
                        help="cluster name override (default is 'ceph')")

    parser.add_argument("--playbook", "-P", type=str,
                        help="playbook to use for deployment ")

    parser.add_argument("--ceph-version", "-c", type=int,
                        default=12, choices=[10, 12],
                        help="ceph version to install")

    parser.add_argument('--version', action='version',
                        version='{} {}'.format(parser.prog,
                                               copilot_version))

    args = parser.parse_args()
    return args


if __name__ == "__main__":

    opts = parse_cli_options()

    # check that the cwd is /usr/share/ceph-ansible to pick up the correct
    # environment (cfg, plugins, actions etc)
    if os.getcwd() != CEPH_ANSIBLE_ROOT:
        print("-> copilot must be started from the {} "
              "directory".format(CEPH_ANSIBLE_ROOT))
        sys.exit(4)

    if opts.playbook:
        if not os.path.exists(opts.playbook):
            print("-> playbook file not found. Is it fully qualified?")
            sys.exit(4)

    copilot = App()
    copilot.setup()
    copilot.loop.run()
    copilot.cleanup()

    print("--- DEBUG STUFF ---")
    print("Config:")
    print(copilot.cfg)
    selected_hosts = [host_name for host_name in copilot.hosts
                      if copilot.hosts[host_name].selected is True]

    print("Selected hosts are: {}".format(selected_hosts))
