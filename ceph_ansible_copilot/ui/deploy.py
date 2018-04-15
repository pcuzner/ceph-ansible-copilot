import urwid
import os

from .base import UIBaseClass, button_row, DataRow
from ceph_ansible_copilot.ansible import ResultCallback, StaticPlaybook


class UI_Deploy(UIBaseClass):

    title = "Deploy"
    hint = "Run time will depend on the size of the cluster being created"
    seq_no = 8

    def __init__(self, parent):
        self.text = (
            "Deploy\n\nThe deployment phase will start the installer "
            "to configure the required hosts."
        )

        self.deploy_attempted = False
        self.success = 0
        self.skipped = 0
        self.failed = 0
        self.unreachable = 0
        self.task_info_w = urwid.Text("Waiting to start")
        self.success_w = urwid.Text(str(self.success),
                                    align='center')
        self.skipped_w = urwid.Text(str(self.skipped),
                                    align='center')
        self.failed_w = urwid.Text(str(self.failed),
                                   align='center')
        self.unreachable_w = urwid.Text(str(self.unreachable),
                                        align='center')

        self.button_row = button_row([('Skip', self.skip_deploy),
                                      ('Deploy', self.deploy)])
        self.failed_hosts = []
        self.failure_list_w = urwid.SimpleListWalker([])
        self.failure_walker_w = urwid.ListBox(self.failure_list_w)

        self.failure_title_w = urwid.Text("")

        UIBaseClass.__init__(self, parent)

    def skip_deploy(self, button):
        app = self.parent
        # check if there were problems, and if so update the next page's text
        self._update_next_page()
        app.next_page()

    def _update_next_page(self):
        app = self.parent
        next_pg = app.pagenum + 1
        app.page[next_pg].text = self.status_msg

    @property
    def status_msg(self):
        """ define the deployment state"""

        app = self.parent
        cfg = app.cfg
        hosts = app.hosts

        if not self.deploy_attempted:
            return (
                "The deployment process was skipped, but the commit to the "
                "installer configuration has been applied. Run the Ansible "
                "playbook manually to perform the installation."
            )

        elif cfg.playbook_rc == 0:
            return (
                "The deployment process was successful. You may now perform "
                "post installation tasks against your Ceph cluster."
            )

        elif self.failed == len([host for host in hosts.keys()
                                 if hosts[host].selected is True]):
            return (
                "The deployment process experienced task failures against "
                "every host in the configuration. To diagnose the issues, "
                "refer to copilot's log file."
            )
        else:
            return (
                "The deployment process was partially successful. {} task(s) "
                "failed across {} host(s). For further diagnostic information "
                "refer to copilot's log file.".format(self.failed,
                                                      len(self.failed_hosts))
            )

    def deploy(self, button):

        app = self.parent
        cfg = app.cfg

        self.deploy_attempted = True
        btn_text = self.button_row.base_widget[1].get_label()
        if btn_text == 'Next':
            self._update_next_page()
            app.next_page()
            return

        if btn_text == 'Rerun':
            # reset the failure table
            self.failure_title_w.set_text("")
            self.failure_list_w = urwid.SimpleListWalker([])

            app.refresh_ui()
            app.loop.widget = app.top

        self.button_row.base_widget[1].set_label('Running')

        host_list = '/etc/ansible/hosts'
        results = ResultCallback(pb_callout=self.page_update,
                                 logger=app.log)

        deploy_pb = StaticPlaybook(host_list=host_list, callback=results)

        if not app.playbook:
            # set the playbook based on the deployment type
            app.playbook = cfg.defaults.playbook[cfg.deployment_type]

        deploy_pb.setup(pb_file=app.playbook)
        app.log.info("Playbook starting, using {}".format(app.playbook))
        app.show_message("Ceph deployment started "
                         "(using {})".format(os.path.basename(app.playbook)),
                         immediate=True)

        deploy_pb.run()

        cfg.playbook_rc = deploy_pb.rc
        self.task_info_w.set_text('')           # remove task name from ui

        if deploy_pb.rc == 0:
            self.button_row.base_widget[1].set_label('Next')
            app.show_message('Deployment Complete - playbook '
                             'completed rc={}'.format(deploy_pb.rc))
        else:
            app.show_message('Error: {} problems encountered during '
                             'deployment'.format(self.failed),
                             immediate=True)
            self.button_row.base_widget[1].set_label('Rerun')

    def page_update(self, stats):
        app = self.parent

        task_states = stats['task_state']

        for key in task_states:
            self.__setattr__(key, task_states[key])

        self.success_w.set_text(str(self.success))
        self.failed_w.set_text(str(self.failed))
        self.unreachable_w.set_text(str(self.unreachable))
        self.skipped_w.set_text(str(self.skipped))
        self.task_info_w.set_text(stats['task_name'])

        self.failed_hosts = stats['failures'].keys()
        if self.failed_hosts:
            app.log.error("failed hosts ({}): ".format(len(self.failed_hosts),
                                                       ','.join(self.failed_hosts)))

            if self.failure_title_w.get_text()[0] == '':

                self.failure_title_w.set_text("Failure Details")

            error_rows = []
            for host in self.failed_hosts:
                # FIXME should add to the table, not recreate each time!
                host_errors = [self._get_err(e_dict)
                               for e_dict in stats['failures'][host]]

                app.log.error("{}: {}".format(host, host_errors))
                app.log.debug("{}: {}".format(host, stats['failures'][host]))

                host_errors.insert(0, "{}\n".format(stats['task_name']))
                host_text = ','.join(host_errors)
                error_rows.append(DataRow(host, host_text))

            self.failure_list_w = urwid.SimpleListWalker(error_rows)

            app.refresh_ui()
            app.loop.widget = app.top

        app.loop.draw_screen()

    def _get_err(self, error_dict):

        errors = list()

        if 'results' in error_dict:

            for err in error_dict.get('results'):
                if not err.get('failed'):
                    continue

                if 'cmd' in err:
                    errors.append(' '.join(err.get('cmd')))
                if 'stderr_lines' in err:
                    errors.append(err.get('stderr_lines'))
                if 'msg' in err:
                    errors.append(err.get('msg'))

        if 'reason' in error_dict:
            errors.append(error_dict.get('reason'))
        if 'msg' in error_dict:
            errors.append(error_dict.get('msg'))
        if 'stdout' in error_dict:
            errors.append(error_dict.get('stdout'))
        else:
            errors.append(error_dict.get('stderr', ''))

        return ' '.join(errors)

    @property
    def render_page(self):

        failure_lb = urwid.ListBox(self.failure_list_w)

        return urwid.AttrMap(
                 urwid.Filler(
                       urwid.Pile([
                         urwid.Padding(urwid.Text(self.text),
                                       left=2, right=2),
                         self.button_row,
                         urwid.Divider(),
                         urwid.Padding(
                             urwid.Pile([
                               urwid.Columns([
                                   (6, urwid.Text("Task:")),
                                   self.task_info_w
                               ]),
                               urwid.Columns([
                                 urwid.Text("\nProgress", align='left'),
                                 urwid.Pile([
                                   urwid.Text('Complete', align='center'),
                                   self.success_w]),
                                 urwid.Pile([
                                   urwid.Text("Skipped", align='center'),
                                   self.skipped_w]),
                                 urwid.Pile([
                                   urwid.Text("Failures", align='center'),
                                   self.failed_w]),
                                 urwid.Pile([
                                   urwid.Text("Unreachable", align='center'),
                                   self.unreachable_w])
                                 ])]), left=2, right=2),
                       urwid.Divider(),
                       urwid.Padding(self.failure_title_w, left=2),
                       urwid.Padding(
                           urwid.BoxAdapter(failure_lb, 10),
                           left=2)]),
                   valign='top', top=1),
                 'active_step')
