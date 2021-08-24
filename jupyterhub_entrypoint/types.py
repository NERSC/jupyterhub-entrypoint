
import os
from textwrap import dedent
import re

from jsonschema import validate as json_validate
from jsonschema.exceptions import ValidationError
from tornado.escape import json_decode
from tornado.httpclient import AsyncHTTPClient


class EntrypointValidationError(Exception):
    """Exception raised if entrypoint data validation fails.

    If either basic or extended validation of entrypoint data fails, this
    exception is to be raised. No detailed explanatory text, especially
    incorporating user input, should be returned to the user if validation
    fails.

    """

    pass


class EntrypointType:
    """Base entrypoint type class.

    Subclass this and override the following methods:

    - cmd               implementation required
    - get_type_name     optional, default is based on class name
    - get_display_name  optional, default is get_type_name()
    - form_hook         optional, coroutine
    - validation_hook   optional, coroutine

    An `EntrypointType` has the following responsibilities:

    - Converting entrypoint data into a replacement for the hub `Spawner.cmd`
    - Providing contents for a form used to manage a type of entrypoint
    - Validating input entrypoint data in an extensible way

    Validation: Basic validation of submitted entrypoint data via JSON Schema
    plus arbitrary type-specific validation. JSON Schema validation is to
    ensure that properties have the right types and that entrypoint data has
    the exact right number of properties. We assume that if a property is
    defined in the schema, it is required.

    Subclasses of `EntrypointType` can extend the JSON Schema easily to expand
    property type and count validation. They can also provide additional
    type-specific validation to ensure that entrypoint data is correct. For
    instance, a subclass that needs to verify that a "path" property looks like
    a proper Unix path can do so by extending the `validation_hook` method.

    """

    def __init__(self):
        self.schema = {
            "type": "object",
            "properties": {
                "user": {"type": "string"},
                "entrypoint_name": {"type": "string"},
                "entrypoint_type": {"type": "string"},
            },
            "required": [
                "user", "entrypoint_name", "entrypoint_type"
            ]
        }

    def extend_schema(self, properties):
        """Extend the base schema used for validating user entrypoint data.

        For example, to extend the schema to verify that a "path" field is
        included and has the right type, call this method this way:

            self.extend_schema({"path": {"type": "string"}})

        The specified properties will be added to the list of base entrypoint
        data properties, included as required properties, and the min/max
        property constraint will be updated to take into account the additional
        properties.

        Args:
            properties (dict): JSON Schema property specification

        """

        self.schema["properties"].update(properties)
        self.schema["required"] += properties.keys()
        self.schema["minProperties"] = len(self.schema["properties"])
        self.schema["maxProperties"] = self.schema["minProperties"]

    @property
    def type_name(self):
        """str: Rendering of entrypoint type suitable for use as a dict key"""
        return self.get_type_name()

    @property
    def display_name(self):
        """str: Human-readable rendering of entrypoint type"""
        return self.get_display_name()

    async def form(self):
        """Return entire HTML form for managing this type of entrypoint.

        Returns:
            str: HTML form for managing entrypoint

        """
        content = self.form_input_name()
        content += await self.form_hook()
        return content

    def form_input_name(self):
        """Return required form element for managing entrypoint name.

        Returns:
            str: Input form control text for HTML form

        """

        return dedent(f"""<input
            name="entrypoint_name"
            class="form-control small-form"
            autocomplete="off"
            placeholder="New {self.display_name} entrypoint name"
        >""")

    async def validate(self, entrypoint_data):
        """Validate entrypoint data, both basic and extended by hook."""
        self.validate_schema(entrypoint_data)
        await self.validation_hook(entrypoint_data)

    def validate_schema(self, entrypoint_data):
        """Perform basic entrypoint data validation using JSON Schema.

        Raises:
            EntrypointValidationError: If schema-based validation fails

        """

        try:
            json_validate(entrypoint_data, self.schema)
        except ValidationError:
            raise EntrypointValidationError

    def cmd(self, entrypoint_data):
        """Return replacement `Spawner.cmd` suitable for hub use.

        Subclasses are required to provide an implementation of this method.
        This value is used to rewrite `Spawner.cmd` typically by the hub's
        `Spawner.pre_spawn_hook` configuration callback.

        Args:
            entrypoint_data (dict): Entrypoint data

        Returns:
            list: Arguments like `Spawner.cmd` used during hub `start()`

        """

        raise NotImplementedError

    def get_type_name(self):
        """Render the entrypoint type for use as a dict key.

        By default, an entrypoint type's class name is converted to a type name
        by removing "EntrypointType" from the end of the class name and then
        returning the remainder in lower case. Subclasses may override this
        behavior to map the entrypoint type to a string suitable for use as a
        dictionary key.

        This method is used by the `type_name` property, which is the way that
        forms should render an entrypoint type name when templating.

        Returns:
            str: Entrypoint type name in a form usable as a dict key

        """

        return re.sub("EntrypointType$", "", self.__class__.__name__).lower()

    def get_display_name(self):
        """Render the entrypoint type in a human-friendly string.

        By default this just uses `get_type_name()` assuming that the type name
        constructed that way is basically human-friendly enough, in particular,
        during template rendering. This may not be desirable, so this method
        can be overridden by subclasses to use an alternate scheme.

        This is used by the `display_name` property, which is how forms should
        render an entrypoint types's human-friendly name when templating.

        Returns:
            str: Entrypoint type name in a human-friendly strong format.

        """

        return self.get_type_name()

    async def form_hook(self):
        """Return form elements needed to manage an entrypoint type.

        Most entrypoint type subclasses have elements that need to be managed
        or configured when an entrypoint is being added or updated. Subclasses
        must provide an implementation of this method to provide the required
        form elements. By default, this methods just returns an empty string.

        This is a coroutine because rendering the form may require non-blocking
        interaction with external services. For instance, a registry service
        that describes suitable Docker containers to choose from in a select
        list.

        Called by the `form` method when the entrypoint type form is rendered.
        The `form` method provides a "name" input element that is required for
        all entrypoint types.

        Returns:
            str: Form elements needed to manage an entrypoint type

        """

        return ""

    async def validation_hook(self, entrypoint_data):
        """Perform extended validation on user input entrypoint data.

        The base `EntrypointType` class provides basic JSON Schema validation
        of entrypoint data, but most subclasses will need to perform additional
        arbitrary validation to ensure that the inputs are sane and secure.

        For instance, if an entrypoint type uses a file path, it is wise to
        ensure that the proposed file path (a) contains no suspicious
        formatting like HTML tags, (b) actually looks like a valid POSIX path,
        and (c) actually exists and has suitable permissions.

        Another possibility is that an entrypoint type could be configured to
        allow only a limited set of entrypoints, governed by configuration and
        managed by the operator/administrator. In this case, validation should
        ensure that users are selecting valid choices from that set, and not
        other choices that don't exist. This way we mitigate user input through
        UI as a vector.

        This is a coroutine because validating entrypoint data may require
        non-blocking interaction with external services.  For instance,
        interacting with a service that can validate that a path exists on the
        file-system.

        Raises:
            EntrypointValidationError: If extended validation fails, subclasses
            should raise EntrypointValidationError with no/minimal additional
            details about how validation failed, and **especially** should not
            respond with **any** of the user's input **at all, never, ever**.

        """

        pass


class TrustedScriptEntrypointType(EntrypointType):
    """Entrypoint type based on scripts managed by an administrator.

    This entrypoint type is configured with a list of absolute script paths
    that users may choose from, to use as entrypoints. These scripts should be
    managed by the administrator or trusted designee.

    This is a usable reference implementation of `EntrypointType`. It shows how
    the entrypoint command is formatted from entrypoint data, how basic
    validation via JSON schema is extended, how type and display names are
    customized, how the form hook is used to extend the entrypoint management
    form, and demonstrates extended server-side validation of user input.

    An entrypoint script in this case might look like:

        #!/bin/bash
        export SOME_VARIABLE=123
        module load vasp
        exec "$@"

    """

    def __init__(self, *args):
        """Initialize the trusted script entrypoint type.

        Args:
            *args (list): List of trusted entrypoint scripts

        """

        super().__init__()
        self.scripts = args
        self.extend_schema({"script": {"type": "string"}})

    def cmd(self, entrypoint_data):
        """Return replacement `Spawner.cmd` using the script entrypoint.

        Args:
            entrypoint_data (dict): Entrypoint data

        Returns:
            list: Arguments prefixed to include trusted entrypoint script

        """

        return [
            entrypoint_data["script"],
            "jupyter-labhub"
        ]

    def get_type_name(self):
        """Override default type name behavior."""
        return "trusted_script"

    def get_display_name(self):
        """Override default display name behavior."""
        return "trusted script"

    async def form_hook(self):
        """Extend form to include list of trusted entrypoint scripts.

        Returns:
            str: Form content for script select field

        """

        content = dedent(f"""<select
            name="script"
            class="small-form form-control"
        >
        <option disabled selected value>-- select script --</option>
        """)
        for script in self.scripts:
            content += f"<option>{script}</option>"
        content += "</select>"

        return content

    async def validation_hook(self, entrypoint_data):
        """Validate that the chosen script is in the list of scripts.

        Raises:
            EntrypointValidationError: If the script is unknown.

        """

        if entrypoint_data["script"] not in self.scripts:
            raise EntrypointValidationError


class TrustedPathEntrypointType(EntrypointType):
    """Entrypoint type based on a path managed by an administrator.

    This entrypoint type is configured with a list of directory paths that
    users may choose from, to use as entrypoints. These paths should be managed
    by the administrator or trusted designee.

    This is a usable reference implementation of `EntrypointType`. It shows how
    the entrypoint command is formatted from entrypoint data, how basic
    validation via JSON schema is extended, how type and display names are
    customized, how the form hook is used to extend the entrypoint management
    form, and demonstrates extended server-side validation of user input.

    Example: An entrypoint path could be the full absolute path to a bin
    directory of a conda environment.

    """

    def __init__(self, *args):
        """Initialize the trusted path entrypoint type.

        Args:
            *args (list): List of trusted directory paths

        """

        super().__init__()
        self.paths = args
        self.extend_schema({"path": {"type": "string"}})

    def cmd(self, entrypoint_data):
        """Return replacement `Spawner.cmd` using the script entrypoint.

        Args:
            entrypoint_data (dict): Entrypoint data

        Returns:
            list: Absolute path to the Jupyter executable

        """

        return [
            os.path.join(entrypoint_data["path"], "jupyter-labhub")
        ]

    def get_type_name(self):
        """Override default type name behavior."""
        return "trusted_path"

    def get_display_name(self):
        """Override default display name behavior."""
        return "trusted path"

    async def form_hook(self):
        """Extend form to include list of trusted paths.

        Returns:
            str: Form content for path select field

        """

        content = dedent(f"""<select
            name="path"
            class="small-form form-control"
        >
        <option disabled selected value>-- select path --</option>
        """)
        for path in self.paths:
            content += f"<option>{path}</option>"
        content += "</select>"

        return content

    async def validation_hook(self, entrypoint_data):
        """Validate that the chosen path is in the list paths.

        Raises:
            EntrypointValidationError: If the path is unknown.

        """

        if entrypoint_data["path"] not in self.paths:
            raise EntrypointValidationError


class ShifterEntrypointType(EntrypointType):
    """Entrypoint type for Shifter, a Docker container runtime.

    This entrypoint type leverages an external services that manages a list of
    Shifter images available for running Jupyter, that users may select from to
    use as entrypoints. These images should be managed by the administrator or
    trusted designee.

    A usable reference implementation of `EntrypointType`, this class shows all
    the same kinds of customizations as `TrustedScriptEntrypointType`, but it
    includes a non-blocking call to an external service during both form and
    validation hook execution.

    """

    def __init__(self, shifter_api_url, shifter_api_token=None):
        """Initialize the Shifter entrypoint type.

        Args:
            shifter_api_url (str): URL for Shifter image service
            shifter_api_token (str): API token for Shifter image service

        """

        super().__init__()
        self.shifter_api_url = shifter_api_url
        self.shifter_api_token = (
            shifter_api_token or os.environ["SHIFTER_API_TOKEN"]
        )
        self.extend_schema({"image": {"type": "string"}})

    def cmd(self, entrypoint_data):
        """Return replacement `Spawner.cmd` using a Shifter entrypoint.

        Args:
            entrypoint_data (dict): Entrypoint data

        Returns:
            list: Arguments prefixed to include Shifter image

        """

        return [
            "shifter",
            f"--image={entrypoint_data['image']}",
            "jupyter-labhub"
        ]

    async def form_hook(self):
        """Extend form to include list of Shifter images.

        Returns:
            str: Form content for image select field

        """

        try:
            images = await self.get_images()
            message = "select image"
        except:
            images = list()
            message = "image lookup failed, try later"
        content = dedent(f"""<select
            name="image"
            class="small-form form-control entrypoint-data"
        >
        <option disabled selected value>-- {message} --</option>
        """)
        for image in images:
            content += f"<option>{image}</option>"
        content += "</select>"

        return content

    async def validation_hook(self, entrypoint_data):
        """Validate that the chosen image is known to Shifter.

        Raises:
            EntrypointValidationError: If the image is unknown.

        """

        try:
            images = await self.get_images()
        except:
            # FIXME log message would be good here...
            raise EntrypointValidationError
        if entrypoint_data["image"] not in images:
            raise EntrypointValidationError

    async def get_images(self):
        """Gets images from the Shifter image service."""

        client = AsyncHTTPClient()
        response = await client.fetch(
            self.shifter_api_url,
            headers={"Authorization": self.shifter_api_token}
        )
        result = json_decode(response.body)
        return result["images"]
