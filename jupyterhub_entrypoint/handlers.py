#########################################################################
# @author Josh Geden
# This class is a Tornado request handler that is used in entrypoint.py
# It returns a rendered jinja template when its GET method is called
#########################################################################

import logging
import os

from jinja2 import Environment
from jupyterhub.utils import url_path_join
from jupyterhub.services.auth import HubAuthenticated
from tornado import web
from tornado.escape import json_decode

from jupyterhub_entrypoint import dbi
from jupyterhub_entrypoint.types import EntrypointValidationError


class BaseHandler(web.RequestHandler):
    """Common behaviors across all handler classes."""

    def initialize(self):
        """Initialize settings common to all handlers."""

        super().initialize()
        self.engine = self.settings["engine"]

    @property
    def log(self):
        """I can't seem to avoid typing self.log"""
        return self.settings.get(
            "log", logging.getLogger("tornado.application")
        )


class ViewHandler(HubAuthenticated, BaseHandler):
    """TBD"""

    def initialize(self, tag, entrypoint_types, loader):
        """TBD"""

        super().initialize()
        self.tag = tag
        self.entrypoint_types = entrypoint_types
        self.loader = loader
        self.env = Environment(loader=self.loader, enable_async=True)
        self.template_index = self.env.get_template("index.html")

    @web.authenticated
    async def get(self):
        """TBD"""

        user = self.get_current_user()
        username = user["name"]
        tag_name = self.tag["tag_name"]

        async with self.engine.begin() as conn:
            entrypoints = await dbi.retrieve_many_entrypoints(
                conn, username, None, tag_name
            )

        entrypoints = entrypoints.get(tag_name, {})

        selection = None
        for entrypoint_type in self.entrypoint_types:
            for entrypoint in entrypoints.get(entrypoint_type.type_name, []):
                if entrypoint["selected"]:
                    selection = entrypoint
                    break

        hub_auth = self.hub_auth
        base_url = hub_auth.hub_prefix
        chunk = await self.template_index.render_async(
            base_url=base_url,
            entrypoint_types=self.entrypoint_types,
            entrypoints=entrypoints,
            login_url=hub_auth.login_url,
            logout_url=url_path_join(base_url, "logout"),
            no_spawner_check=True,
            selection=selection,
            service_prefix=self.settings["service_prefix"],
            static_url=self.static_url,
            tag_name=tag_name,
            tags=self.settings["tags"],
            user=user, 
        )
        self.write(chunk)


class NewHandler(HubAuthenticated, BaseHandler):

    def initialize(self, tag, entrypoint_type, loader):
        """TBD"""

        super().initialize()
        self.tag = tag
        self.entrypoint_type = entrypoint_type
        self.loader = loader
        self.env = Environment(loader=self.loader, enable_async=True)
        self.template_manage = self.env.get_template("manage.html")

    @web.authenticated
    async def get(self):

        user = self.get_current_user()
        hub_auth = self.hub_auth
        base_url = hub_auth.hub_prefix
        chunk = await self.template_manage.render_async(
            base_url=base_url,
            login_url=hub_auth.login_url,
            logout_url=url_path_join(base_url, "logout"),
            no_spawner_check=True,
            service_prefix=self.settings["service_prefix"],
            static_url=self.static_url,
            user=user, 
            entrypoint_type=self.entrypoint_type,
            tag_name=self.tag["tag_name"],
            tags=self.settings["tags"],
            entrypoint_data=None
        )
        self.write(chunk)


class UpdateHandler(HubAuthenticated, BaseHandler):

    def initialize(self, tag, entrypoint_type, loader):
        """TBD"""

        super().initialize()
        self.tag = tag
        self.entrypoint_type = entrypoint_type
        self.loader = loader
        self.env = Environment(loader=self.loader, enable_async=True)
        self.template_manage = self.env.get_template("manage.html")

    @web.authenticated
    async def get(self, entrypoint_name):

        user = self.get_current_user()
        username = user["name"]
        hub_auth = self.hub_auth
        base_url = hub_auth.hub_prefix

        async with self.engine.begin() as conn:
            result = await dbi.retrieve_one_entrypoint(
                conn, username, entrypoint_name
            ) # tag_names is paused but should also pass through
        entrypoint_data = result["entrypoint_data"]
        tag_names = result["tag_names"]

        chunk = await self.template_manage.render_async(
            base_url=base_url,
            login_url=hub_auth.login_url,
            logout_url=url_path_join(base_url, "logout"),
            no_spawner_check=True,
            service_prefix=self.settings["service_prefix"],
            static_url=self.static_url,
            user=user, 
            entrypoint_type=self.entrypoint_type,
            tag_name=self.tag["tag_name"],
            tags=self.settings["tags"],
            entrypoint_data=entrypoint_data
        )
        self.write(chunk)


class EntrypointHandler(HubAuthenticated, BaseHandler):
    """TBD"""
    pass

class EntrypointPostHandler(EntrypointHandler):
    """TBD"""

    def initialize(self, entrypoint_types):
        """TBD"""

        super().initialize()
        self.entrypoint_types = entrypoint_types

    @web.authenticated
    async def post(self, user):
        """TBD"""

        try:
            payload = json_decode(self.request.body)
            entrypoint_data = payload["entrypoint_data"]
            await self.validate(user, entrypoint_data)
            async with self.engine.begin() as conn:
                await dbi.create_entrypoint(
                    conn,
                    user,
                    entrypoint_data["entrypoint_name"],
                    entrypoint_data["entrypoint_type"],
                    entrypoint_data,
                    payload["tag_names"]
                )

            self.write({"result": True, "message": "Entrypoint added"})
        except EntrypointValidationError:
            self.log.error(f"Validation error: {entrypoint_data}")
            self.write({"result": False, "message": "Validation error"})
        except Exception as e:
            self.log.error(f"Error ({e}): {entrypoint_data}")
            # Types of errors may need a bit more elaboration (like unique names)
            self.write({"result": False, "message": "Error"})

    @web.authenticated
    async def put(self, user):
        """TBD"""

        try:
            payload = json_decode(self.request.body)
            entrypoint_data = payload["entrypoint_data"]
            await self.validate(user, entrypoint_data)
            async with self.engine.begin() as conn:
                await dbi.update_entrypoint(
                    conn,
                    user,
                    entrypoint_data["entrypoint_name"],
                    entrypoint_data["entrypoint_type"],
                    entrypoint_data,
#                   payload["tag_names"] FIXME should be able to change this too
                )

            self.write({"result": True, "message": "Entrypoint updated"})
        except EntrypointValidationError:
            self.log.error(f"Validation error: {entrypoint_data}")
            self.write({"result": False, "message": "Validation error"})
        except Exception as e:
            self.log.error(f"Error ({e}): {entrypoint_data}")
            # Types of errors may need a bit more elaboration (like unique names)
            self.write({"result": False, "message": "Error"})

    async def validate(self, user, entrypoint_data):
        """Validate request and run appropriate validator on entrypoint data.

        Raises:
            EntrypointValidationError: If the user field doesn't match the
            authenticated user, or the user argument, or the entrypoint type
            cannot be identified.

        """

        current_user = self.get_current_user()
        username = current_user["name"]
        if username != user:
            raise EntrypointValidationError
        if username != entrypoint_data.get("user"):
            raise EntrypointValidationError

        for entrypoint_type in self.entrypoint_types:
            if entrypoint_type.type_name == entrypoint_data["entrypoint_type"]:
                await entrypoint_type.validate(entrypoint_data)
                return
        raise EntrypointValidationError


class EntrypointDeleteHandler(EntrypointHandler):
    """Deletes entrypoints."""
    
    @web.authenticated
    async def delete(self, user, entrypoint_name):
        """TBD"""

        async with self.engine.begin() as conn:
            await dbi.delete_entrypoint(conn, user, entrypoint_name)
        self.write({})


class SelectionHandler(HubAuthenticated, BaseHandler):
    """Updates user entrypoint selections."""

    @web.authenticated
    async def put(self, user, entrypoint_name, tag_name):
        """TBD"""

        async with self.engine.begin() as conn:
            await dbi.update_selection(conn, user, entrypoint_name, tag_name)
        self.write({})

    @web.authenticated
    async def delete(self, user, entrypoint_name, tag_name):
        """TBD"""

        # FIXME entrypoint_name isn't doing anything here, maybe don't need it
        async with self.engine.begin() as conn:
            await dbi.delete_selection(conn, user, tag_name)
        self.write({})


class HubSelectionHandler(BaseHandler):
    """Gives the hub and endpoint to contact to find out a user's selection."""

    def initialize(self, entrypoint_types):
        """TBD"""

        super().initialize()
        self.entrypoint_api_token = os.environ["ENTRYPOINT_API_TOKEN"]
        self.entrypoint_types = entrypoint_types

    async def get(self, user, tag_name):
        """TBD"""

        if not self.validate_token():
            raise web.HTTPError(403)

        try:
            async with self.engine.begin() as conn:
                entrypoint_data = await dbi.retrieve_selection(
                    conn, 
                    user, 
                    tag_name
                )
        except ValueError:
            raise web.HTTPError(404)
       
        cmd = list()
        for entrypoint_type in self.entrypoint_types:
            if entrypoint_type.type_name == entrypoint_data["entrypoint_type"]:
                cmd = entrypoint_type.cmd(entrypoint_data)
                break
        self.write(dict(cmd=cmd))

    def validate_token(self):
        """TBD"""

        return (
            self.request.headers["Authorization"] ==
            f"token {self.entrypoint_api_token}"
        )
