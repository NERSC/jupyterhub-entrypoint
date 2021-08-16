
import os
from textwrap import dedent
import re

from jsonschema import validate as json_validate
from jsonschema.exceptions import ValidationError
from tornado.escape import json_decode
from tornado.httpclient import AsyncHTTPClient


class EntrypointValidationError:
    pass



class EntrypointType:
    """Base entrypoint type class

    Subclass this and override the following methods:

    - cmd               implementation required
    - get_type_name     optional, default is based on class name
    - get_display_name  optional, default is get_type_name()
    - form_hook         optional, coroutine
    - validation_hook   optional, coroutine
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
        self.schema["properties"].update(properties)
        self.schema["required"] += properties.keys()
        self.schema["minProperties"] = len(self.schema["properties"])
        self.schema["maxProperties"] = self.schema["minProperties"]

    @property
    def type_name(self):
        return self.get_type_name()

    @property
    def display_name(self):
        return self.get_display_name()

    async def form(self):
        content = self.form_input_name()
        content += await self.form_hook()
        return content

    def form_input_name(self):
        return dedent(f"""<input 
            name="entrypoint_name"
            class="form-control small-form"
            autocomplete="off"
            placeholder="New {self.display_name} entrypoint name"
        >""")

    async def validate(self, entrypoint_data):
        self.validate_schema(entrypoint_data)
        await self.validation_hook(entrypoint_data)

    def validate_schema(self, entrypoint_data):
        try:
            json_validate(entrypoint_data, self.schema)
        except ValidationError:
            raise EntrypointValidationError

    def cmd(self, entrypoint_data):
        raise NotImplementedError

    def get_type_name(self):
        return re.sub("EntrypointType$", "", self.__class__.__name__).lower()

    def get_display_name(self):
        return self.get_type_name()

    async def form_hook(self):
        return ""

    async def validation_hook(self, entrypoint_data):
        pass


class TrustedScriptEntrypointType(EntrypointType):
    """Scripts on the file system trusted by admin

    Assumption here is that an admin is maintaining a list scripts that users
    may decide to use. As such, users may only choose them from a select list.

    These scripts probably look something like

        #!/bin/bash
        export SOME_VARIABLE=123
        module load something
        exec "$@"
    """

    def __init__(self, *args):
        super().__init__()
        self.script_paths = args
        self.extend_schema({"path": {"type": "string"}})

    def cmd(self, entrypoint_data):
        return [
            entrypoint_data["path"],
            "jupyter-labhub"
        ]

    def get_type_name(self):
        return "trusted_script"

    def get_display_name(self):
        return "trusted script"

    async def form_hook(self):
        content = dedent(f"""<select
            name="path"
            class="small-form form-control"
        >
        <option disabled selected value>-- select path --</option>
        """)
        for path in self.script_paths:
            content += f"<option>{path}</option>"
        content += "</select>"

        return content


class ShifterEntrypointType(EntrypointType):

    def __init__(self, shifter_api_url, shifter_api_token=None):
        super().__init__()
        self.shifter_api_url = shifter_api_url
        self.shifter_api_token = (
            shifter_api_token or os.environ["SHIFTER_API_TOKEN"]
        )
        self.extend_schema({"image": {"type": "string"}})

    def cmd(self, entrypoint_data):
        return [
            "shifter", 
            f"--image={entrypoint_data['image']}",
            "jupyter-labhub"
        ]

    async def form_hook(self):
        images = await self.get_images()
        content = dedent(f"""<select
            name="image"
            class="small-form form-control entrypoint-data"
        >
        <option disabled selected value>-- select image --</option>
        """)
        for image in images:
            content += f"<option>{image}</option>"
        content += "</select>"

        return content

    async def validation_hook(self, entrypoint_data):
        images = await self.get_images()
        if entrypoint_data["image"] not in images:
            raise ValueError

    async def get_images(self):
        client = AsyncHTTPClient()
        try:
            response = await client.fetch(
                self.shifter_api_url,
                headers={"Authorization": self.shifter_api_token}
            )
        except Exception as e:
            print(f"Error: {e}")
            return []
        result = json_decode(response.body)
        return result["images"]
