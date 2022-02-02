
import logging
import os

from jinja2 import Environment, FileSystemLoader
from jupyterhub.services.auth import HubOAuthenticated
from jupyterhub.utils import url_path_join
from tornado.escape import json_decode
from tornado.web import authenticated, HTTPError, RequestHandler

from jupyterhub_entrypoint import dbi
from jupyterhub_entrypoint.types import (
    EntrypointType, EntrypointValidationError
)


class BaseHandler(RequestHandler):
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


class EntrypointHandler(HubOAuthenticated, BaseHandler):
    """TBD"""


class WebHandler(EntrypointHandler):
    """TBD"""

    def initialize(self):
        """TBD"""

        super().initialize()
        self.loader = FileSystemLoader(self.settings["template_paths"])
        self.env = Environment(loader=self.loader, enable_async=True)


class AboutHandler(WebHandler):
    """TBD"""

    def initialize(self):
        """TBD"""

        super().initialize()
        self.template_about = self.env.get_template("about.html")
        self.about_text = self.settings["about_text"]

    @authenticated
    async def get(self):
        """TBD"""

        user = self.get_current_user()
        hub_auth = self.hub_auth
        base_url = hub_auth.hub_prefix

        chunk = await self.template_about.render_async(
            about_text=self.about_text,
            base_url=base_url,
            login_url=hub_auth.login_url,
            logout_url=url_path_join(base_url, "logout"),
            no_spawner_check=True,
            service_prefix=self.settings["service_prefix"],
            static_url=self.static_url,
            user=user,
        )
        self.write(chunk)


class ViewHandler(WebHandler):
    """TBD"""

    def initialize(self):
        """TBD"""

        super().initialize()
        self.entrypoint_types = self.settings["entrypoint_types"]
        self.template_index = self.env.get_template("index.html")

    @authenticated
    async def get(self, context_name):
        """TBD"""

        user = self.get_current_user()
        username = user["name"]

        async with self.engine.begin() as conn:
            entrypoints = await dbi.retrieve_many_entrypoints(
                conn, username, None, context_name
            )

        entrypoints = entrypoints.get(context_name, {})

        selection = None
        for entrypoint_type_name in self.entrypoint_types:
            for entrypoint in entrypoints.get(entrypoint_type_name, []):
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
            context_name=context_name,
            contexts=self.settings["contexts"],
            user=user,
        )
        self.write(chunk)


class NewHandler(WebHandler):

    def initialize(self):
        """TBD"""

        super().initialize()
        self.entrypoint_types = self.settings["entrypoint_types"]
        self.template_manage = self.env.get_template("manage.html")

    @authenticated
    async def get(self, entrypoint_type_name):

        context_name = self.get_query_argument("context")

        entrypoint_type = self.entrypoint_types.get(entrypoint_type_name)
        if entrypoint_type is None:
            raise WebError(404)

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
            entrypoint_type=entrypoint_type,
            context_name=context_name,
            checked_context_names=[context_name],
            contexts=self.settings["contexts"],
            entrypoint_data=None
        )
        self.write(chunk)


class UpdateHandler(WebHandler):

    def initialize(self):
        """TBD"""

        super().initialize()
        self.entrypoint_types = self.settings["entrypoint_types"]
        self.template_manage = self.env.get_template("manage.html")

    @authenticated
    async def get(self, uuid):

        context_name = self.get_query_argument("context")

        user = self.get_current_user()
        username = user["name"]
        hub_auth = self.hub_auth
        base_url = hub_auth.hub_prefix

        async with self.engine.begin() as conn:
            result = await dbi.retrieve_one_entrypoint(
                conn, username, uuid=uuid
            )
        entrypoint_type_name = result["entrypoint_type_name"]
        entrypoint_data = result["entrypoint_data"]
        context_names = result["context_names"]

        entrypoint_type = self.entrypoint_types.get(entrypoint_type_name)
        if entrypoint_type is None:
            raise WebError(404)

        chunk = await self.template_manage.render_async(
            base_url=base_url,
            login_url=hub_auth.login_url,
            logout_url=url_path_join(base_url, "logout"),
            no_spawner_check=True,
            service_prefix=self.settings["service_prefix"],
            static_url=self.static_url,
            user=user,
            entrypoint_type=entrypoint_type,
            context_name=context_name,
            checked_context_names=context_names,
            contexts=self.settings["contexts"],
            entrypoint_data=entrypoint_data,
            uuid=uuid
        )
        self.write(chunk)


class EntrypointAPIHandler(EntrypointHandler):
    """TBD"""

    def initialize(self):
        """TBD"""

        super().initialize()
        self.entrypoint_types = self.settings["entrypoint_types"]
        self.context_names = [
            context["context_name"] for context in self.settings["contexts"]
        ]

    @authenticated
    async def post(self):
        """TBD"""

        user = self.get_current_user().get("name")

        try:
            payload = json_decode(self.request.body)
            entrypoint_type_name = payload["entrypoint_type"]
            entrypoint_data = payload["entrypoint_data"]
            await self.validate_entrypoint_data(user, entrypoint_type_name, entrypoint_data)
            context_names = payload["context_names"] or self.context_names
            self.validate_context_names(context_names)
            async with self.engine.begin() as conn:
                await dbi.create_entrypoint(
                    conn,
                    user,
                    entrypoint_data["entrypoint_name"],
                    entrypoint_type_name,
                    entrypoint_data,
                    context_names
                )
            self.write({"result": True, "message": "Entrypoint added"})
        except EntrypointValidationError:
            self.log.error(f"Validation error: {entrypoint_data}")
            self.write({"result": False, "message": "Validation error"})
        except Exception as e:
            self.log.error(f"Error ({e}): {entrypoint_data}")
            self.write({"result": False, "message": "Error"})

    @authenticated
    async def put(self, uuid):
        """TBD"""

        user = self.get_current_user().get("name")

        async with self.engine.begin() as conn:
            result = await dbi.retrieve_one_entrypoint(
                conn, user, uuid=uuid
            )
        entrypoint_type_name = result["entrypoint_type_name"]
        current_context_names = result["context_names"]

        try:
            payload = json_decode(self.request.body)
            entrypoint_data = payload["entrypoint_data"]
            await self.validate_entrypoint_data(user, entrypoint_type_name, entrypoint_data)
            context_names = payload["context_names"] or self.context_names
            self.validate_context_names(context_names)
            to_tag = list(
                set(context_names).difference(
                    set(current_context_names)
                )
            )
            to_untag = list(
                set(current_context_names).difference(
                    set(context_names)
                )
            )
            async with self.engine.begin() as conn:
                await dbi.update_entrypoint_uuid(
                    conn,
                    user,
                    uuid,
                    entrypoint_data["entrypoint_name"],
                    entrypoint_data
                )
                for context_name in to_tag:
                    await dbi.tag_entrypoint(
                        conn,
                        user,
                        entrypoint_data["entrypoint_name"],
                        context_name
                    )
                for context_name in to_untag:
                    await dbi.untag_entrypoint(
                        conn,
                        user,
                        entrypoint_data["entrypoint_name"],
                        context_name
                    )
            self.write({"result": True, "message": "Entrypoint updated"})
        except EntrypointValidationError:
            self.log.error(f"Validation error: {entrypoint_data}")
            self.write({"result": False, "message": "Validation error"})
        except Exception as e:
            self.log.error(f"Error ({e}): {entrypoint_data}")
            self.write({"result": False, "message": "Error"})

    async def validate_entrypoint_data(
        self,
        user,
        entrypoint_type_name,
        entrypoint_data
    ):
        """Validate request and run appropriate validator on entrypoint data.

        Raises:
            EntrypointValidationError: If the user field doesn't match the
            authenticated user, or the entrypoint type cannot be identified.

        """

        entrypoint_type = self.entrypoint_types.get(entrypoint_type_name)
        if isinstance(entrypoint_type, EntrypointType):
            await entrypoint_type.validate(entrypoint_data)
            return
        raise EntrypointValidationError

    def validate_context_names(self, context_names):
        for name in context_names:
            if name not in self.context_names:
                raise EntrypointValidationError

    @authenticated
    async def delete(self, entrypoint_name):
        """TBD"""

        user = self.get_current_user().get("name")

        async with self.engine.begin() as conn:
            await dbi.delete_entrypoint(conn, user, entrypoint_name)
        self.write({})


class SelectionAPIHandler(EntrypointHandler):
    """Updates user entrypoint selections."""

    @authenticated
    async def put(self, entrypoint_name, context_name):
        """TBD"""

        user = self.get_current_user().get("name")

        async with self.engine.begin() as conn:
            await dbi.update_selection(conn, user, entrypoint_name, context_name)
        self.write({})

    @authenticated
    async def delete(self, entrypoint_name, context_name):
        """TBD"""

        user = self.get_current_user().get("name")

        # FIXME entrypoint_name isn't doing anything here, maybe don't need it
        async with self.engine.begin() as conn:
            await dbi.delete_selection(conn, user, context_name)
        self.write({})


class HubSelectionAPIHandler(BaseHandler):
    """Gives the hub and endpoint to contact to find out a user's selection."""

    def initialize(self):
        """TBD"""

        super().initialize()
        self.entrypoint_api_token = os.environ["ENTRYPOINT_API_TOKEN"]
        self.entrypoint_types = self.settings["entrypoint_types"]

    async def get(self, user, context_name):
        """TBD"""

        if not self.validate_token():
            raise HTTPError(403)

        try:
            async with self.engine.begin() as conn:
                result = await dbi.retrieve_selection(
                    conn,
                    user,
                    context_name
                )
        except ValueError:
            raise HTTPError(404)
        entrypoint_type_name, entrypoint_data = result
        entrypoint_type = self.entrypoint_types.get(entrypoint_type_name)

        spawner_args = dict()
        if isinstance(entrypoint_type, EntrypointType):
            kwargs = self.parse_query_arguments()
            spawner_args = entrypoint_type.spawner_args(
                entrypoint_data,
                **kwargs
            )
        self.write(spawner_args)

    def parse_query_arguments(self):
        """TBD"""

        kwargs = dict()

        batchspawner = self.get_query_argument("batchspawner", "false").lower()
        kwargs["batchspawner"] = batchspawner in ["true", "yes", "1"]

        return kwargs

    def validate_token(self):
        """TBD"""

        return (
            self.request.headers["Authorization"] ==
            f"token {self.entrypoint_api_token}"
        )
