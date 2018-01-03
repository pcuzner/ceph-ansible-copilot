#!/usr/bin/env python2

import inspect


class BaseCheck(object):

    valid_run_modes = ['prod', 'dev']

    def __init__(self):
        self.problems = {
            "error": [],
            "warning": []
        }

    def check(self):

        check_methods = [member for member in
                         [getattr(self, attr) for attr in dir(self)]
                         if inspect.ismethod(member) and
                         member.__name__.startswith("_check")]

        for checker in check_methods:
            checker()

    def _add_problem(self, severity, msg):
        self.problems[severity].append(msg)

    @property
    def state(self):
        error_count = len(self.problems['error'])
        warn_count = len(self.problems['warning'])
        if error_count + warn_count == 0:
            return 'OK'
        else:
            if error_count > 0:
                return 'NOTOK({}Err)'.format(error_count)
            else:
                return 'NOTOK({}Wrn)'.format(warn_count)

    @property
    def state_long(self):
        state_desc = list()
        if len(self.problems['error']) > 0:
            state_desc.append("Error:{}".format(', '.join(self.problems['error'])))
        if len(self.problems['warning']) > 0:
            state_desc.append("Warning:{}".format(', '.join(self.problems['warning'])))

        return ' / '.join(state_desc)





