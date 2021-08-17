#########################################################################
# @author Josh Geden
# This class is a Tornado request handler that is used in entrypoint.py
# It returns a rendered jinja template when its GET method is called
#########################################################################

from jinja2 import Environment
from jupyterhub.utils import url_path_join
from jupyterhub.services.auth import HubAuthenticated
from tornado import web
from tornado.escape import json_decode

from jupyterhub_entrypoint import dbi


class BaseHandler(web.RequestHandler):

    def initialize(self):
        super().initialize()
        self.engine = self.settings["engine"]


class ViewHandler(HubAuthenticated, BaseHandler):

    def initialize(self, tag, entrypoint_types, loader):#, systems, entrypoint_types):
        super().initialize()

        self.tag = tag
        self.entrypoint_types = entrypoint_types

        # set variables used to load and render jinja template
        self.loader = loader
        self.env = Environment(loader=self.loader, enable_async=True)
        self.template_index = self.env.get_template('index.html')

    def render(self, template, *args, **kwargs):
        return self.env.get_template(template).render(*args, **kwargs)

    @web.authenticated
    async def get(self):
        user = self.get_current_user()
        username = user["name"]
        hub_auth = self.hub_auth
        base_url = hub_auth.hub_prefix

        async with self.engine.begin() as conn:
            entrypoints = await dbi.retrieve_many_entrypoints(conn, username, None, self.tag["tag_name"])

        selection = None
        for entrypoint_type in entrypoints:
            for entrypoint in entrypoints[entrypoint_type]:
                if entrypoint.selected:
                    selection = entrypoint
                    break
        print(selection)

        chunk = await self.template_index.render_async(
            user=user, 
            login_url=hub_auth.login_url,
            logout_url=url_path_join(base_url, "logout"),
            base_url=base_url,
            no_spawner_check=True,
            static_url=self.static_url,
            tag_name=self.tag["tag_name"],
            tags=self.settings["tags"],
            service_prefix=self.settings["service_prefix"],
            entrypoint_types=self.entrypoint_types,
            entrypoints=entrypoints,
            selection=selection,
        )
        self.write(chunk)


class EntrypointHandler(HubAuthenticated, BaseHandler):

    @web.authenticated
    async def post(self, user, _): #probably should be in own handler
        try:
            payload = json_decode(self.request.body)
            entrypoint_data = payload["entrypoint_data"]
            tag_names = payload["tag_names"] 
            # some validation happens...
            # make sure user is user
            entrypoint_name = entrypoint_data["entrypoint_name"]
            entrypoint_type = entrypoint_data["entrypoint_type"]
            async with self.engine.begin() as conn:
                await dbi.create_entrypoint(
                    conn,
                    user,
                    entrypoint_name,
                    entrypoint_type,
                    entrypoint_data,
                    tag_names
                )
            self.write({"result": True, "message": "Entrypoint added"})
        except:
            self.write({"result": False, "message": "SADNESS"})
    
    @web.authenticated
    async def delete(self, user, entrypoint_name):
        async with self.engine.begin() as conn:
            await dbi.delete_entrypoint(conn, user, entrypoint_name)
        self.write({})


class SelectionHandler(HubAuthenticated, BaseHandler):

    @web.authenticated
    async def put(self, user, entrypoint_name, tag_name):
        async with self.engine.begin() as conn:
            await dbi.update_selection(conn, user, entrypoint_name, tag_name)
        self.write({})

    @web.authenticated
    async def delete(self, user, entrypoint_name, tag_name):
        # FIXME entrypoint_name isn't doing anything here, maybe don't need it
        async with self.engine.begin() as conn:
            await dbi.delete_selection(conn, user, tag_name)
        self.write({})


class HubSelectionHandler(HubAuthenticated, BaseHandler):

    def initialize(self, entrypoint_types):
        super().initialize()
        self.entrypoint_types = entrypoint_types

    @web.authenticated
    async def get(self, user, tag_name):
        # need to verify API token

        async with self.engine.begin() as conn:
            entrypoint_data = await dbi.retrieve_selection(
                conn, 
                user, 
                tag_name
            )
       
        cmd = None
        for entrypoint_type in self.entrypoint_types:
            if entrypoint_type.type_name != entrypoint_data["entrypoint_type"]:
                continue
            cmd = entrypoint_type.cmd(entrypoint_data)
        self.write(dict(cmd=cmd))
