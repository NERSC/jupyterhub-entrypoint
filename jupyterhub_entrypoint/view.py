#########################################################################
# @author Josh Geden
# This class is a Tornado request handler that is used in entrypoint.py
# It returns a rendered jinja template when its GET method is called
#########################################################################

from tornado import web
from jinja2 import Environment
from jupyterhub.utils import url_path_join
from jupyterhub.services.auth import HubAuthenticated


class ViewHandler(HubAuthenticated, web.RequestHandler):
    def initialize(self, loader, systems, entrypoint_types):
        super().initialize()

        # set variables used to load and render jinja template
        self.loader = loader
        self.env = Environment(loader=self.loader)
        self.template = self.env.get_template('index.html')

        # initialize lists of systems and entrypoint types
        self.systems = systems
        self.entrypoint_types = entrypoint_types

    @web.authenticated
    async def get(self):
        prefix = self.hub_auth.hub_prefix
        logout_url = url_path_join(prefix, 'logout')

        # set the current system to the ?system url parameter or default to first system in the list
        system = None
        if (len(self.systems) > 0):
            system = self.get_argument("system", self.systems[0]['name'], True)

        # compare the name of the system to the dict of systems to get other field variables about the system
        for sys in self.systems:
            if system == sys['name']:
                system = sys
                break

        # return the rendered jinja template
        self.write(self.template.render(user=self.get_current_user(),
                                        login_url=self.hub_auth.login_url,
                                        logout_url=logout_url,
                                        base_url=prefix,
                                        no_spawner_check=True,
                                        static_url=self.static_url,
                                        systems=self.systems,
                                        system=system,
                                        entrypoint_types=self.entrypoint_types))
