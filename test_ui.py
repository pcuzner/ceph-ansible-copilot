import urwid

from ceph_ansible_copilot.ui import UI_Credentials
from ceph_ansible_copilot.ui.palette import palette
from ceph_ansible_copilot import Host


def unknown_input(key):

    if key == 'esc':
        raise urwid.ExitMainLoop


class App(object):

    def next_page(self):
        raise urwid.ExitMainLoop


class Config(object):
    pass


def load_test_data():

    hosts = dict()

    data = [
        # "centos1",
        # "centos2",
        # "centos3",
        "ceph-1",
        "ceph-2",
        "ceph-3"
    ]

    for hostname in data:
        _h = Host(hostname=hostname)
        hosts[hostname] = _h

    return hosts


def main():

    app = App()
    app.cfg = Config()

    app.hosts = load_test_data()

    page = UI_Credentials(parent=app)

    page.refresh()

    ui = page.render_page

    app.loop = urwid.MainLoop(ui,
                              palette,
                              unhandled_input=unknown_input)
    app.loop.run()


if __name__ == "__main__":

    main()
