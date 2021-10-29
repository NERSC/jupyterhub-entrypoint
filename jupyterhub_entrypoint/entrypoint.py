#########################################################################
# @author Josh Geden
# This class creates the main Tornado web app for the entrypoint service
# It sets up the configurable variables and loads any config file
# It also sets up all request handlers with their API endpoint
#########################################################################

import asyncio
import logging
import os
import sys

from jupyterhub.log import CoroutineLogFormatter
from jupyterhub._data import DATA_FILES_PATH
from jupyterhub.utils import url_path_join
from jupyterhub.handlers.static import LogoHandler
from tornado.ioloop import IOLoop
from tornado.web import Application, RedirectHandler, StaticFileHandler
from traitlets import (
    config, default, observe,
    Bool, Dict, Instance, Integer, List, Tuple, Type, Unicode
)

from jupyterhub_entrypoint.ssl_context import SSLContext
from jupyterhub_entrypoint.handlers import (
    AboutHandler, NewHandler, ViewHandler, UpdateHandler,
    EntrypointPostHandler, EntrypointDeleteHandler, SelectionHandler,
    HubSelectionHandler
)
from jupyterhub_entrypoint.types import EntrypointType
from jupyterhub_entrypoint import dbi


class EntrypointService(config.Application, config.Configurable):
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

    config_file = Unicode(
        "entrypoint_config.py",
        help="Config file to load"
    ).tag(config=True)

    database_url = Unicode(
        "sqlite+aiosqlite:///:memory:",
        help="SQLAlchemy engine database URL"
    ).tag(config=True)

    data_files_path = Unicode(
        DATA_FILES_PATH,
        help="Location of JupyterHub data files"
    )

    default_context_name = Unicode(
        help="Name of default context, if unset, uses the first one defined"
    ).tag(config=True)

    @default("default_context_name")
    def _default_context_name(self):
        return self.contexts[0]["context_name"]

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

    contexts = List(
        [], #Dict,
        help="List of contexts"
    ).tag(config=True)

    custom_template_paths = List(
        help="Search paths for custom templates, coming before default ones"
    ).tag(config=True)

    default_template_paths = List(
        help="Paths to default JupyterHub and Entrypoint Service templates"
    )

    # set the default value for the path to the templates folder
    @default("default_template_paths")
    def _default_template_paths(self):
        return [
            os.path.join(self.data_files_path, "entrypoint", "templates"),
            os.path.join(self.data_files_path, "templates"),
        ]

    types = List(
        Tuple(Type(), List()),
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

    verbose_sqlalchemy = Bool(
        False,
        help="Turns on SQLAlchemy echo for verbose output"
    ).tag(config=True)


    # initialize the web app by loading the config file, loading the template,
    # and setting the request handlers
    def initialize(self, argv=None):
        super().initialize(argv)

#       logging.basicConfig(level=logging.INFO)
#       logging.getLogger('tornado.access').disabled = not self.tornado_logs
#       self.log = logging.getLogger(__name__)

        if self.generate_config:
            print(self.generate_config_file())
            sys.exit(0)

        self.init_logging()

        # load the config file if it's there
        if self.config_file:
            self.load_config_file(self.config_file)

        # initialize the ssl certificate
        self.init_ssl_context()

        # create SQLAlchemy engine and optionally initialize database FIXME parameterize
        engine = dbi.async_engine(
            self.database_url,
            echo=self.verbose_sqlalchemy,
            future=True
        )

        # for now we always initialize the database for testing... FIXME

        async def init_db(engine):
            async with engine.begin() as conn:
                await dbi.init_db(conn)

            async with engine.begin() as conn:
                for context in self.contexts:
                    await dbi.create_context(conn, context["context_name"])

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
            "contexts": self.contexts,
            "template_paths": (
                self.custom_template_paths + self.default_template_paths
            )
        }

        # create handlers

        handlers = list()

        # redirect to default context

        handler = (
            self.service_prefix,
            RedirectHandler,
            dict(url=self.service_prefix + self.default_context_name + "/select")
        )
        handlers.append(handler)

        # if there are no contexts just register the no-context handler

        for context in self.contexts:
            handler = (
                self.service_prefix + context["context_name"] + "/select",
                ViewHandler,
                dict(
                    context=context,
                    entrypoint_types=self.entrypoint_types
                )
            )
            handlers.append(handler)

        for context in self.contexts:
            for entrypoint_type in self.entrypoint_types:
                handler = (
                    self.service_prefix + context["context_name"] + "/new/" + entrypoint_type.type_name,
                    NewHandler,
                    dict(
                        context=context,
                        entrypoint_type=entrypoint_type
                    )
                )
                handlers.append(handler)

        for context in self.contexts:
            for entrypoint_type in self.entrypoint_types:
                handler = (
                    self.service_prefix + context["context_name"] + "/update/" + entrypoint_type.type_name + "/(.+)",
                    UpdateHandler,
                    dict(
                        context=context,
                        entrypoint_type=entrypoint_type
                    )
                )
                handlers.append(handler)

        handler = (
            self.service_prefix + "about",
            AboutHandler
        )
        handlers.append(handler)

        # Entrypoint API delete handler

        handler = (
            self.service_prefix + "api/mgmt/users/(.+)/entrypoints/(.+)",
            EntrypointDeleteHandler
        )
        handlers.append(handler)

        # Entrypoint API post handler

        handler = (
            self.service_prefix + "api/mgmt/users/(.+)/entrypoints/",
            EntrypointPostHandler,
            dict(entrypoint_types=self.entrypoint_types)
        )
        handlers.append(handler)

        # Selection API handler

        handler = (
            self.service_prefix + "api/mgmt/users/(.+)/selections/(.+)/contexts/(.+)",
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
            (self.service_prefix + r"static/(.*)", StaticFileHandler,
             {"path": self.settings["static_path"]}),
            (self.service_prefix + r"logo",
             LogoHandler, {"path": self.logo_file})
        ]

        # use the settings and handlers to create a Tornado web app
        self.app = Application(handlers, **self.settings)


    _log_formatter_cls = CoroutineLogFormatter

    @default('log_datefmt')
    def _log_datefmt_default(self):
        """Exclude date from default date format"""
        return "%Y-%m-%d %H:%M:%S"

    @default('log_format')
    def _log_format_default(self):
        """override default log format to include time"""
        return "%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s %(module)s:%(lineno)d]%(end_color)s %(message)s"

    def init_logging(self):
        # This prevents double log messages because tornado use a root logger
        # that self.log is a child of. The logging module dipatches log
        # messages to a log and all of its ancenstors until propagate is set to
        # False.
        self.log.propagate = False

        _formatter = self._log_formatter_cls(
            fmt=self.log_format, datefmt=self.log_datefmt
        )

        # disable curl debug, which is TOO MUCH
        logging.getLogger('tornado.curl_httpclient').setLevel(
            max(self.log_level, logging.INFO)
        )

        for name in ("access", "application", "general"):
            # ensure all log statements identify the application they come from
            log = logging.getLogger(f"tornado.{name}")
            log.name = self.log.name

        # hook up tornado's and oauthlib's loggers to our own
        for name in ("tornado", "oauthlib"):
            logger = logging.getLogger(name)
            logger.propagate = True
            logger.parent = self.log
            logger.setLevel(self.log.level)

    # create an ssl cert
    def init_ssl_context(self):
        self.ssl_content = SSLContext().ssl_context()

    # have the web app listen at the port set by the config
    def start(self):
        self.app.listen(self.port)
        IOLoop.current().start()


def main():
    app = EntrypointService()
    app.initialize()
    app.start()


if __name__ == "__main__":
    main()
