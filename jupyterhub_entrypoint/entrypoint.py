#########################################################################
# @author Josh Geden
# This class creates the main Tornado web app for the entrypoint service
# It sets up the configurable variables and loads any config file
# It also sets up all request handlers with their API endpoint
#########################################################################

import asyncio
import os
import sys
import logging
from tornado import ioloop, web
from jinja2 import FileSystemLoader

from traitlets import Bool, Dict, Instance, Integer, List, Tuple, Type, Unicode, default, observe
from traitlets.config import Application, Configurable

from jupyterhub.utils import url_path_join
from jupyterhub._data import DATA_FILES_PATH
from jupyterhub.handlers.static import LogoHandler

from .api import APIHubCurrentHandler, APIHubTypeHandler, APIPathHandler, APIUserSelectionHandler, APIUserValidationHandler
from .ssl_context import SSLContext
from .handlers import ViewHandler, EntrypointHandler, SelectionHandler, HubSelectionHandler
from .types import EntrypointType

from jupyterhub_entrypoint import dbi


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

#   # The following variables are configurable traitlet variables
#   additional_handlers = List(
#       [],
#       help="A list of additional request handlers"
#   ).tag(config=True)

    config_file = Unicode(
        "entrypoint_config.py",
        help="Config file to load"
    ).tag(config=True)

    data_files_path = Unicode(
        DATA_FILES_PATH,
        help="Location of JupyterHub data files"
    )

    default_tag_name = Unicode(
        help="Name of default tag, if unset, uses the first tag defined"
    ).tag(config=True)

    @default("default_tag_name")
    def _default_tag_name(self):
        return self.tags[0]["tag_name"]
    
    entrypoint_api_token = Unicode(
        os.environ.get("JUPYTERHUB_API_TOKEN"),
        help="Secret token to access JupyterHub as an API"
    ).tag(config=True)

    entrypoint_types = List(
        Instance(EntrypointType),
        help="TBD"
    )

    logo_file = Unicode(
        "",
        help="Logo path, can be used to override JupyterHub one",
    ).tag(config=True)

    # set the default value for the logo file
    @default("logo_file")
    def _logo_file_default(self):
        return os.path.join(
            self.data_files_path, "static", "images", "jupyterhub-80.png"
        )

    port = Integer(
        8889,
        help="Port this service will listen on"
    ).tag(config=True)

    service_prefix = Unicode(
        os.environ.get("JUPYTERHUB_SERVICE_PREFIX",
                       "/services/entrypoint/"),
        help="Entrypoint service prefix"
    ).tag(config=True)

#   systems = List(
#       [],
#       help="A list of available systems"
#   ).tag(config=True)

    tags = List(
        [], #Dict,
        help="List of tags"
    ).tag(config=True)

    template_paths = List(
        help="Search paths for jinja templates, coming before default ones"
    ).tag(config=True)

    types = List(
        Tuple(Type(), Tuple()),
        help="TBD"
    ).tag(config=True)

    @observe("types")
    def _observe_types(self, change):
        new = change["new"]
        new_entrypoint_types = list()
        for spec in new:
            cls, args = spec
            entrypoint_type = cls(*args)
            new_entrypoint_types.append(entrypoint_type)
        self.entrypoint_types = new_entrypoint_types

    # set the default value for the path to the templates folder
    @default("template_paths")
    def _template_paths_default(self):
        return ["templates",
                os.path.join(self.data_files_path, "templates"),
                os.path.join(self.data_files_path, "entrypoint", "templates")]

    tornado_logs = Bool(
        False,
        help="Determines whether tornado.access logs be included in stdout"
    ).tag(config=True)


    # initialize the web app by loading the config file, loading the template,
    # and setting the request handlers
    def initialize(self, argv=None):
        super().initialize(argv)

        logging.basicConfig(level=logging.INFO)
        logging.getLogger('tornado.access').disabled = not self.tornado_logs
        self.log = logging.getLogger(__name__)

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

        self.log.info(self.template_paths)

        # create a jinja loader to get the necessary html templates
        loader = FileSystemLoader(self.template_paths)

        # create SQLAlchemy engine and optionally initialize database FIXME parameterize
        engine = dbi.async_engine(
            f"sqlite+aiosqlite:///:memory:",
#           echo=True,
            future=True
        )

        # for now we always initialize the database for testing... FIXME

        async def init_db(engine):
            async with engine.begin() as conn:
                await dbi.init_db(conn)

            async with engine.begin() as conn:
                for tag in self.tags:
                    await dbi.create_tag(conn, tag["tag_name"])

        loop = asyncio.get_event_loop()
        coroutine = init_db(engine)
        loop.run_until_complete(coroutine)

        # create a dict of settings to pass on to the request handlers
        self.settings = {
            "service_prefix": self.service_prefix,
            "entrypoint_api_token": self.entrypoint_api_token,
            "static_path": os.path.join(self.data_files_path, "static"),
            "static_url_prefix": url_path_join(self.service_prefix, "static/"),
            "engine": engine,
            "tags": self.tags,
        }

        # create handlers

        handlers = list()

        # if there are no tags just register the notag handler

        for tag in self.tags:
            handler = (
                self.service_prefix + tag["tag_name"], 
                ViewHandler,
                dict(
                    tag=tag,
                    entrypoint_types=self.entrypoint_types,
                    loader=loader
                )
            )
            handlers.append(handler)

        # redirect to default tag

        handler = (
            self.service_prefix,
            web.RedirectHandler,
            dict(url=self.service_prefix + self.default_tag_name)
        )
        handlers.append(handler)

        # Entrypoint API handler

        handler = (
            self.service_prefix + "api/mgmt/users/(.+)/entrypoints/(.*)",
            EntrypointHandler
        )
        handlers.append(handler)

        # Selection API handler

        handler = (
            self.service_prefix + "api/mgmt/users/(.+)/selections/(.+)/tags/(.+)",
            SelectionHandler
        )
        handlers.append(handler)

        # Hub's selection handler

        handler = (
            self.service_prefix + "api/hub/users/(.+)/selections/(.+)",
            HubSelectionHandler,
            dict(
                entrypoint_types=self.entrypoint_types,
            )
        )
        handlers.append(handler)

        handlers += [
#           (self.service_prefix + r"(.*)", ViewHandler, {"loader": loader}),
#           (r"(.*)", ViewHandler, {"loader": loader, "systems": self.systems,
#            "entrypoint_types": self.entrypoint_types}),
            (self.service_prefix + r"static/(.*)", web.StaticFileHandler,
             {"path": self.settings["static_path"]}),
            (self.service_prefix + r"logo",
             LogoHandler, {"path": self.logo_file})
        ]



#       # create the default list of handlers (to show the html template, load static assets, and load the logo)
#       handlers = [
#           ('', ViewHandler, {"loader": loader, "systems": self.systems,
#            "entrypoint_types": self.entrypoint_types}),
#           (r"static/(.*)", web.StaticFileHandler,
#            {"path": self.settings["static_path"]}),
#           (r"logo",
#            LogoHandler, {"path": self.logo_file})
#       ]

#       # add any handlers set in the config file to the list of handlers
#       handlers += self.additional_handlers

#       # create an APIUserSelectionHandler and APIUserValidationHandler for each system set in the config file
#       for system in self.systems:
#           handlers += [(rf"users/(.+)/systems/{system['name']}",
#                         APIUserSelectionHandler, {"system": system['name']}),

#                        (rf"validate/users/(.+)/systems/{system['name']}",
#                         APIUserValidationHandler, {"system": system['name'], "host": system['hostname']}),
#                        ]

#       # create an APIHubHandler
#       handlers += [(rf"hub/users/(.+)/systems/(.+)", APIHubCurrentHandler),
#                    (rf"hub/users/(.+)/systems/(.+)/types/(.+)", APIHubTypeHandler)]

#       # create an APIPathHandler for each entrypoint type set in the config file
#       for entrypoint in self.entrypoint_types:
#           handlers += [(rf"users/(.+)/systems/(.+)/types/(.+)", APIPathHandler)]

#       # append the service prefix to the front of each request handlers' API endpoint
#       # e.g. users/{user}/systems/{system} => services/entrypoint/users/{user}/systems/{system}
#       handlers = list(
#           map(lambda x: (self.service_prefix + x[0], *x[1:]), handlers))

#       # The following API endpoints are created by default
#       # service_prefix/entrypoints/users/{user}/type/{type}?system={system} to get the list of available entrypoints for a given system
#       # service_prefix/users/{user}/systems/{system} to get a user's selected entrypoint for a system
#       # service_prefix/validate/users/{user}/systems/{system} to re-validate a user's selected entrypoint for a system
#       for handler in handlers:
#           self.log.info(handler[0])

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
