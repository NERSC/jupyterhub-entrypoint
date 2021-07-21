from custom.image_handler import APIShifterImageHandler
from custom.validate import SSHValidator


c.EntrypointService.systems = [
    {
        'name': 'cori',
        'display_name': 'Cori',
        'hostname': 'cori'
    },
    {
        'name': 'perlmutter',
        'display_name': 'Perlmutter',
        'hostname': 'perlmutter'
    }
]

c.EntrypointService.entrypoint_types = [
    {
        'name': 'conda',
        'display_name': 'Conda',
        'mutable': True,
        'cmd_template': '{path}/bin/jupyterlab-hub',
        'help_link': 'http://localhost:8000/services/entrypoint/'
    },
    {
        'name': 'script',
        'display_name': 'Startup Script',
        'mutable': True,
        'cmd_template': '{path}',
        'help_link': 'http://localhost:8000/services/entrypoint/'
    },
    {
        'name': 'shifter',
        'display_name': 'Shifter Image',
        'mutable': False,
        'cmd_template': 'shifter --image={path}',
        'help_link': 'http://localhost:8000/services/entrypoint/'
    }
]

c.EntrypointService.additional_handlers = [
    (r"entrypoints/users/(.+)/type/shifter", APIShifterImageHandler)
]

c.APIBaseHandler.validator = SSHValidator()

c.EntrypointService.template_paths = [
    '/Users/josh/miniconda3/envs/test-hub/share/jupyterhub/entrypoint/templates']


# Configuration file for application.

# ------------------------------------------------------------------------------
# Application(SingletonConfigurable) configuration
# ------------------------------------------------------------------------------
# This is an application.

# The date format used by logging formatters for %(asctime)s
#  Default: '%Y-%m-%d %H:%M:%S'
# c.Application.log_datefmt = '%Y-%m-%d %H:%M:%S'

# The Logging format template
#  Default: '[%(name)s]%(highlevel)s %(message)s'
# c.Application.log_format = '[%(name)s]%(highlevel)s %(message)s'

# Set the log level by value or name.
#  Choices: any of [0, 10, 20, 30, 40, 50, 'DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL']
#  Default: 30
# c.Application.log_level = 30

# Instead of starting the Application, dump configuration to stdout
#  Default: False
# c.Application.show_config = False

# Instead of starting the Application, dump configuration to stdout (as JSON)
#  Default: False
# c.Application.show_config_json = False

# ------------------------------------------------------------------------------
# EntrypointService(Application, Configurable) configuration
# ------------------------------------------------------------------------------
# This is an application.

# A list of additional request handlers
#  Default: []
# c.EntrypointService.additional_handlers = []

# Config file to load
#  Default: 'entrypoint_config.py'
# c.EntrypointService.config_file = 'entrypoint_config.py'

# Secret token to access JupyterHub as an API
#  Default: None
# c.EntrypointService.entrypoint_api_token = None

# A list of tuples: (str entrypoint_name, bool editable)
#  Default: []
# c.EntrypointService.entrypoint_types = []

# Path for where file storage object saves files
#  Default: '{user[0]}/{user}/{type}/{uuid}.json'
# c.EntrypointService.file_storage_template_path = '{user[0]}/{user}/{type}/{uuid}.json'

# Generate default config file
#  Default: False
# c.EntrypointService.generate_config = False

# The date format used by logging formatters for %(asctime)s
#  See also: Application.log_datefmt
# c.EntrypointService.log_datefmt = '%Y-%m-%d %H:%M:%S'

# The Logging format template
#  See also: Application.log_format
# c.EntrypointService.log_format = '[%(name)s]%(highlevel)s %(message)s'

# Set the log level by value or name.
#  See also: Application.log_level
# c.EntrypointService.log_level = 30

# Logo path, can be used to override JupyterHub one
#  Default: ''
# c.EntrypointService.logo_file = ''

# Port this service will listen on
#  Default: 8888
# c.EntrypointService.port = 8888

# Entrypoint service prefix
#  Default: '/services/entrypoint/'
# c.EntrypointService.service_prefix = '/services/entrypoint/'

# Instead of starting the Application, dump configuration to stdout
#  See also: Application.show_config
# c.EntrypointService.show_config = False

# Instead of starting the Application, dump configuration to stdout (as JSON)
#  See also: Application.show_config_json
# c.EntrypointService.show_config_json = False

# Location for file storage
#  Default: '/data'
# c.EntrypointService.storage_path = '/data'

# A list of available systems
#  Default: []
# c.EntrypointService.systems = []

# Search paths for jinja templates, coming before default ones
#  Default: []
# c.EntrypointService.template_paths = []

# ------------------------------------------------------------------------------
# APIBaseHandler(HubAuthenticated, web.RequestHandler, Application, Configurable) configuration
# ------------------------------------------------------------------------------
# This is a RequestHandler.

# Instance of validation class, must inherit from jupyterhub_entrypoint.api.BaseValidator
# Default: BaseValidator()
# c.APIBaseHandler.validator = None
