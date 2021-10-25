# Configuration file for application.

#------------------------------------------------------------------------------
# Application(SingletonConfigurable) configuration
#------------------------------------------------------------------------------
## This is an application.

## The date format used by logging formatters for %(asctime)s
#  Default: '%Y-%m-%d %H:%M:%S'
# c.Application.log_datefmt = '%Y-%m-%d %H:%M:%S'

## The Logging format template
#  Default: '[%(name)s]%(highlevel)s %(message)s'
# c.Application.log_format = '[%(name)s]%(highlevel)s %(message)s'

## Set the log level by value or name.
#  Choices: any of [0, 10, 20, 30, 40, 50, 'DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL']
#  Default: 30
# c.Application.log_level = 30

## Instead of starting the Application, dump configuration to stdout
#  Default: False
# c.Application.show_config = False

## Instead of starting the Application, dump configuration to stdout (as JSON)
#  Default: False
# c.Application.show_config_json = False

#------------------------------------------------------------------------------
# EntrypointService(Application, Configurable) configuration
#------------------------------------------------------------------------------
## This is an application.

## Config file to load
#  Default: 'entrypoint_config.py'
# c.EntrypointService.config_file = 'entrypoint_config.py'

## SQLAlchemy engine database URL
#  Default: 'sqlite+aiosqlite:///:memory:'
# c.EntrypointService.database_url = 'sqlite+aiosqlite:///:memory:'

## Name of default context, if unset, uses the first context defined
#  Default: ''
# c.EntrypointService.default_context_name = ''

## Secret token to access JupyterHub as an API
#  Default: None
# c.EntrypointService.entrypoint_api_token = None

## Generate default config file
#  Default: False
# c.EntrypointService.generate_config = False

## The date format used by logging formatters for %(asctime)s
#  See also: Application.log_datefmt
# c.EntrypointService.log_datefmt = '%Y-%m-%d %H:%M:%S'

## The Logging format template
#  See also: Application.log_format
# c.EntrypointService.log_format = '[%(name)s]%(highlevel)s %(message)s'

## Set the log level by value or name.
#  See also: Application.log_level
# c.EntrypointService.log_level = 30

## Logo path, can be used to override JupyterHub one
#  Default: ''
# c.EntrypointService.logo_file = ''

## Port this service will listen on
#  Default: 8889
# c.EntrypointService.port = 8889

## Entrypoint service prefix
#  Default: '/services/entrypoint/'
# c.EntrypointService.service_prefix = '/services/entrypoint/'

## Instead of starting the Application, dump configuration to stdout
#  See also: Application.show_config
# c.EntrypointService.show_config = False

## Instead of starting the Application, dump configuration to stdout (as JSON)
#  See also: Application.show_config_json
# c.EntrypointService.show_config_json = False

## List of contexts
#  Default: []
# c.EntrypointService.contexts = []
c.EntrypointService.contexts = [{
    "context_name": "multivac",
    "display_name": "Multivac",
}, {
    "context_name": "hal",
    "display_name": "HAL",
}, {
    "context_name": "m5",
    "display_name": "M-5",
}]

## Search paths for jinja templates, coming before default ones
#  Default: []
# c.EntrypointService.template_paths = []

## TBD
#  Default: []
# c.EntrypointService.types = []
c.EntrypointService.types = [(
    "jupyterhub_entrypoint.types.TrustedScriptEntrypointType",
    ["/usr/local/bin/example-entrypoint.sh"],
), (
    "jupyterhub_entrypoint.types.ShifterEntrypointType",
    ["http://127.0.0.1:8890/services/images/", "blah"]
)]

## Turns on SQLAlchemy echo for verbose output
#  Default: False
# c.EntrypointService.verbose_sqlalchemy = False
