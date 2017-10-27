

import ast
import glob
import os
import imp
import json


class PluginMgr(object):

    def __init__(self, plugin_dir='/usr/share/ceph-ansible-copilot/plugins',
                 logger=None):

        self.logger = logger
        self.plugin_dir = os.path.abspath(plugin_dir)
        self.logger.debug("Plugin directory : {}".format(self.plugin_dir))

        if os.path.exists(self.plugin_dir):
            self.plugins = self.load_plugins()
        else:
            self.plugins = []

    def load_plugins(self):
        plugins = []
        self.logger.info("Plugins to be loaded from {}".format(self.plugin_dir))
        candidate_modules = glob.glob('{}/*.py'.format(self.plugin_dir))

        for f in candidate_modules:
            full_path = os.path.join(self.plugin_dir, f)
            tree = self.parse_ast(full_path)
            signature = self.analyse_module(tree)

            if self.valid_plugin(signature):

                # load the plugin
                mod = self._load_plugin(full_path)
                plugins.append(mod)
            else:
                self.logger.warning("{} signature invalid, skipped")
                self.logger.warning(json.dumps(signature))

        return plugins

    def _load_plugin(self, plugin_module):

        mod_namespace = os.path.splitext(os.path.basename(plugin_module))[0]
        mod = imp.load_source(mod_namespace, plugin_module)

        return mod

    @staticmethod
    def valid_plugin(signature):
        var_names = ['description', 'yml_file']

        if 'plugin_main' not in signature['functions']:
            return False

        if not all(v in signature['vars'] for v in var_names):
            return False

        target_dir = os.path.split(signature['vars']['yml_file'])[0]
        if not os.path.exists(target_dir):
            return False

        return True

    def parse_ast(self, filename):
        with open(filename, "rt") as f:
            return ast.parse(f.read(), filename=filename)

    def analyse_module(self, tree):
        functions = []
        var_list = {}

        for e in tree.body:
            if isinstance(e, ast.FunctionDef):
                functions.append(e.name)
            if isinstance(e, ast.Assign):
                for t in e.targets:
                    var_list[t.id] = e.value.s
        return {"functions": functions,
                "vars": var_list}
