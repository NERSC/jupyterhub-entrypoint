#########################################################################
# @author Josh Geden
# Defines classes for the request handlers used in EntrypointService app
#########################################################################

import warnings
from tornado import escape, web
from jupyterhub.services.auth import HubAuthenticated
from traitlets.config import Configurable, Application
from traitlets import Instance, Unicode


class BaseValidator:
    """Base class used to handle validation. Should be configured in entrypoint_config.py"""

    async def validate(self, user, path, entrypoint_type, host):
        warnings.warn('No validator set in entrypoint_config.py', UserWarning)
        return True, 'Warning: No validator set in entrypoint_config.py'


class APIBaseHandler(HubAuthenticated, web.RequestHandler, Application, Configurable):
    """Parent handler class that initializes env variables and handles user authentication"""

    config_file = Unicode(
        "entrypoint_config.py",
        help="Config file to load"
    ).tag(config=True)

    # Instance of validation object
    # The only requirement is that the object inherit from BaseValidator (above)
    # and have an async def validate() method
    validator = Instance(
        default_value=BaseValidator(),
        klass=BaseValidator,
        help="Class used to handle validation for environment paths"
    ).tag(config=True)

    def initialize(self):
        super().initialize()

        # loads the config file to set the validator
        if self.config_file:
            self.load_config_file(self.config_file)

        # retrieve needed variables from the EntrypointService app settings
        self.storage = self.settings['storage']
        self.service_prefix = self.settings['service_prefix']
        self.service_url = self.settings['service_url']
        self.api_token = self.settings['entrypoint_api_token']

    # ensures the logged in user is authorized to view/edit settings
    def verify_user(self, user):
        current_user = self.get_current_user()
        if not current_user.get('admin', False) and current_user['name'] != user:
            raise web.HTTPError(403)


class APIPathHandler(APIBaseHandler):
    """Handler used to fetch a user's available paths for a given entrypoint type for a given system"""

    def initialize(self, entrypoint_type):
        super().initialize()
        self.entrypoint_type = entrypoint_type

    # returns all entrypoints for the given type (conda, script, etc)
    # requires a system url parameter
    @web.authenticated
    def get(self, user):
        self.verify_user(user)

        system = self.get_argument('system', '', True)

        if system != '':
            info = self.storage.read(user, self.entrypoint_type, system)
            if info:
                self.write(info)
        else:
            self.write('APIError: system parameter not specified')
            raise Exception('APIError: system parameter not specified')


class APIUserValidationHandler(APIBaseHandler):
    """Handler used to validate a user's current selected entrypoint"""

    # initializes with the system name (i.e. 'cori') and the system's hostname (i.e. 'cori.nersc.gov')
    def initialize(self, system, host):
        super().initialize()
        self.system = system
        self.host = host

    # calls the validator to ensure the current entrypoint is valid
    @web.authenticated
    async def get(self, user):
        self.verify_user(user)

        # get the current selected entrypoint for the user for the given system from storage
        info = self.storage.read(user, self.system, self.system)
        if info:
            path = info[user][0]['entrypoint']
            entrypoint_type = info[user][0]['type']

            # validate using the validator set in entrypoint_config.py
            result, message = await self.validator.validate(user, path, entrypoint_type, self.host)
            self.write({'result': result, 'message': message})
        else:
            self.write(
                {'result': False, 'message': f'Error: No entrypoint set for {user} on {self.system}'})


class APIUserSelectionHandler(APIBaseHandler):
    """Handles the users current selected entrypoint for a given system"""

    def initialize(self, system):
        super().initialize()
        self.system = system

    # returns a user's current selected entrypoint for the given system
    @web.authenticated
    def get(self, user):
        self.verify_user(user)
        info = self.storage.read(user, self.system, self.system)

        if info:
            self.write(info)

    # deletes an entrypoint from the list of possible entrypoints
    # the request's body must have a "type" and "id" field
    @web.authenticated
    def delete(self, user):
        self.verify_user(user)
        doc = escape.json_decode(self.request.body)
        entrypoint_type = doc["type"]
        id = doc["id"]

        self.storage.delete(user, entrypoint_type, id)
        self.write({'result': True})

    # handles adding or selecting an entrypoint
    # the requests body must have an "action" field (either 'add' or 'select')
    # requests to 'add' must also have "entrypoint" (the path), "name", "type" (conda, script, etc.), "systems", and "host"
    # requests to 'select' must also have "entrypoint", "name", "type", and "id"
    @web.authenticated
    async def post(self, user):
        self.verify_user(user)

        doc = escape.json_decode(self.request.body)
        print(f'Doc: {doc}')

        # add a new entrypoint as an option
        name = doc["name"]
        path = doc["entrypoint"]
        entrypoint_type = doc["type"]
        systems = doc["systems"]
        host = doc["host"]

        # validate the entrypoint to be added
        result, message = await self.validator.validate(user, path, entrypoint_type, host)

        if result is True:
            print('Validation successful')
            self.storage.create(user,  name, path,
                                entrypoint_type, systems)
            self.write(
                {'result': True, 'message': 'Path successfully added'})
        else:
            print('Validation failed')
            self.write({'result': False, 'message': message})

    @web.authenticated
    async def put(self, user):
        doc = escape.json_decode(self.request.body)
        print(f'Doc: {doc}')
        
        entrypoint_id = doc["id"]
        entrypoint_type = doc["type"]
        path = doc["entrypoint"]
        name = doc["name"]
        result = self.storage.update(user, name, path, entrypoint_id,
                                     entrypoint_type, self.system)
        print('Finished selecting')

        if result:
            self.write(
                {'result': True, 'message': 'Entrypoint successfully updated'})
        else:
            self.write({'result': False, 'message': 'Error: invalid path'})
