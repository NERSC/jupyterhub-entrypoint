#########################################################################
# @author Josh Geden
# This class creates the main Tornado web app for the entrypoint service
# It sets up the configurable variables and loads any config file
# It also sets up all request handlers with their API endpoint
#########################################################################

import os
import sys
from tornado import ioloop, web
from jinja2 import FileSystemLoader

from traitlets import Bool, Dict, Integer, List, Unicode, default
from traitlets.config import Application, Configurable

from jupyterhub.utils import url_path_join
from jupyterhub._data import DATA_FILES_PATH
from jupyterhub.handlers.static import LogoHandler

from .api import APIPathHandler, APIUserSelectionHandler, APIUserValidationHandler
from .ssl_context import SSLContext
from .view import ViewHandler
from .storage import FileStorage


class EntrypointService(Application, Configurable):
    """Configurable Tornado web application class that initializes request handlers"""

    flags = Dict({
        'generate-config': (
            {'EntrypointService': {'generate_config': True}},
            'Generate default config file',
        )
    })

    generate_config = Bool(
        False,
        help="Generate default config file"
    ).tag(config=True)

    # The following variables are configurable traitlet variables
    additional_handlers = List(
        [],
        help="A list of additional request handlers"
    ).tag(config=True)

    config_file = Unicode(
        "entrypoint_config.py",
        help="Config file to load"
    ).tag(config=True)

    data_files_path = Unicode(
        DATA_FILES_PATH,
        help="Location of JupyterHub data files"
    )

    entrypoint_api_token = Unicode(
        os.environ.get("JUPYTERHUB_API_TOKEN"),
        help="Secret token to access JupyterHub as an API"
    ).tag(config=True)

    entrypoint_types = List(
        [],
        help="A list of dicts: (name: str, displayname: str, mutable: bool)"
    ).tag(config=True)

    file_storage_template_path = Unicode(
        "{user[0]}/{user}/{type}/{uuid}.json",
        help="Path for where file storage object saves files"
    ).tag(config=True)

    logo_file = Unicode(
        "",
        help="Logo path, can be used to override JupyterHub one",
    ).tag(config=True)

    port = Integer(
        8889,
        help="Port this service will listen on"
    ).tag(config=True)

    service_prefix = Unicode(
        os.environ.get("JUPYTERHUB_SERVICE_PREFIX",
                       "/services/entrypoint/"),
        help="Entrypoint service prefix"
    ).tag(config=True)

    service_url = Unicode(
        os.environ.get("JUPYTERHUB_SERVICE_URL",
                       "http://proxy:8000"),
        help="Entrypoint service url"
    ).tag(config=True)

    storage_path = Unicode(
        os.environ.get("STORAGE_PATH", "./data"),
        help="Location for file storage"
    ).tag(config=True)

    systems = List(
        [],
        help="A list of available systems"
    ).tag(config=True)

    template_paths = List(
        help="Search paths for jinja templates, coming before default ones"
    ).tag(config=True)

    # set the default value for the logo file
    @default("logo_file")
    def _logo_file_default(self):
        return os.path.join(
            self.data_files_path, "static", "images", "jupyterhub-80.png"
        )

    # set the default value for the path to the templates folder
    @default("template_paths")
    def _template_paths_default(self):
        return ["templates",
                os.path.join(self.data_files_path, "templates"),
                os.path.join(self.data_files_path, "entrypoint", "templates")]

    # initialize the web app by loading the config file, loading the template,
    # and setting the request handlers
    def initialize(self, argv=None):
        super().initialize(argv)

        if self.generate_config:
            print(self.generate_config_file())
            sys.exit(0)

        # load the config file if it's there
        if self.config_file:
            self.load_config_file(self.config_file)

        # initialize the ssl certificate
        self.init_ssl_context()

        # get the base data path to find the templates folder
        base_paths = self._template_paths_default()
        for path in base_paths:
            if path not in self.template_paths:
                self.template_paths.append(path)

        print(self.template_paths)

        # create a jinja loader to get the necessary html templates
        loader = FileSystemLoader(self.template_paths)

        # create a dict of settings to pass on to the request handlers
        self.settings = {
            "service_prefix": self.service_prefix,
            "service_url": self.service_url,
            "entrypoint_api_token": self.entrypoint_api_token,
            "static_path": os.path.join(self.data_files_path, "static"),
            "static_url_prefix": url_path_join(self.service_prefix, "static/"),
            "storage": FileStorage(os.path.join(self.storage_path, self.file_storage_template_path))
        }

        # create the default list of handlers (to show the html template, load static assets, and load the logo)
        handlers = [
            ('', ViewHandler, {"loader": loader, "systems": self.systems,
             "entrypoint_types": self.entrypoint_types}),
            (r"static/(.*)", web.StaticFileHandler,
             {"path": self.settings["static_path"]}),
            (r"logo",
             LogoHandler, {"path": self.logo_file})
        ]

        # add any handlers set in the config file to the list of handlers
        handlers += self.additional_handlers

        # create an APIUserSelectionHandler for each system set in the config file
        for system in self.systems:
            handlers += [(rf"users/(.+)/systems/{system['name']}",
                          APIUserSelectionHandler, {"system": system['name']}),

                         (rf"validate/users/(.+)/systems/{system['name']}",
                          APIUserValidationHandler, {"system": system['name'], "host": system['hostname']})]

        # create an APIPathHandler for each entrypoint type set in the config file
        for entrypoint in self.entrypoint_types:
            handlers += [(f"entrypoints/users/(.+)/type/{entrypoint['name']}",
                          APIPathHandler, {"entrypoint_type": entrypoint['name']})]

        # append the service prefix to the front of each request handlers' API endpoint
        # e.g. users/{user}/systems/{system} => services/entrypoint/users/{user}/systems/{system}
        handlers = list(
            map(lambda x: (self.service_prefix + x[0], *x[1:]), handlers))

        # The following API endpoints are created by default
        # service_prefix/entrypoints/users/{user}/type/{type}?system={system} to get the list of available entrypoints for a given system
        # service_prefix/users/{user}/systems/{system} to get a user's selected entrypoint for a system
        # service_prefix/validate/users/{user}/systems/{system} to re-validate a user's selected entrypoint for a system
        for handler in handlers:
            print(handler[0])

        # use the settings and handlers to create a Tornado web app
        self.app = web.Application(handlers, **self.settings)

    # create an ssl cert
    def init_ssl_context(self):
        self.ssl_content = SSLContext().ssl_context()

    # have the web app listen at the port set by the config
    def start(self):
        self.app.listen(self.port)
        ioloop.IOLoop.current().start()


def main():
    app = EntrypointService()
    app.initialize()
    app.start()


if __name__ == "__main__":
    main()
