
import os
from textwrap import dedent

from tornado.escape import json_decode
from tornado.httpclient import AsyncHTTPClient
from tornado.httputil import url_concat

# For the demo, make it easy to get to the service

c.JupyterHub.default_url = "/hub/home"

# Run the entrypoint service, and the fake image server service

c.JupyterHub.services = [{
    "display": True,
    "name": "entrypoint",
    "command": ["python3", "-m", "jupyterhub_entrypoint"],
    "oauth_no_confirm": True,
    "url": "http://127.0.0.1:8889",
    "environment": {
        "ENTRYPOINT_API_TOKEN": os.environ["ENTRYPOINT_API_TOKEN"]
    }
}, {
    "display": False,
    "name": "images",
    "command": ["python3", "./image-server.py"],
    "url": "http://127.0.0.1:8890"
}]

# Role needed for user to access services in Hub 2.x

c.JupyterHub.load_roles = [{
    "name": "user",
    "scopes": ["access:services", "self"]
}]

# Set cmd to jupyter-labhub because it's awesome

c.Spawner.cmd = ['jupyter-labhub']

async def pre_spawn_hook(spawner):
    if data := spawner.user_options.get("spawner_args"):
        with spawner.hold_trait_notifications():
            for key, value in data.items():
                if spawner.has_trait(key):
                    setattr(spawner, key, value)

c.Spawner.pre_spawn_hook = pre_spawn_hook

async def options_form(spawner):

    user = spawner.user
    username = user.name

    client = AsyncHTTPClient()
    try:
        args = {
            "batchspawner": "no"
        }
        url = url_concat(
            f"http://127.0.0.1:8889/services/entrypoint/api/users/{username}/entrypoints/hal",
            args
        )
        headers = {
            "Authorization": f"token {os.environ['ENTRYPOINT_API_TOKEN']}"
        }
        response = await client.fetch(url, headers=headers)
    except Exception as e:
        spawner.log.error(f"{e}")
    else:
        data = json_decode(response.body)
        spawner.log.info(f"{data}")

    form = ""

    form += dedent("""\
        <label for="entrypoint">Entrypoint:</label>
        <select class="form-control" name="entrypoint" autofocus>
        <option value="">Default Entrypoint</option>
    """)

    for entrypoint in data["entrypoints"]:
        spawner.log.info(f"{entrypoint}")
        entrypoint_name = entrypoint["entrypoint_name"]
        form += dedent(f"""\
            <option value="{entrypoint_name}">
                {entrypoint_name}
            </option>"""
        )

    form += dedent("""\
        </select>
    """)

    return form

async def options_from_form(form_data, spawner):

    user = spawner.user
    username = user.name

    client = AsyncHTTPClient()
    try:
        args = {
            "batchspawner": "no"
        }
        url = url_concat(
            f"http://127.0.0.1:8889/services/entrypoint/api/users/{username}/entrypoints/hal",
            args
        )
        headers = {
            "Authorization": f"token {os.environ['ENTRYPOINT_API_TOKEN']}"
        }
        response = await client.fetch(url, headers=headers)
    except Exception as e:
        spawner.log.error(f"{e}")
    else:
        data = json_decode(response.body)
        spawner.log.info(f"{data}")

    entrypoint_name = form_data["entrypoint"][0]
    if entrypoint_name:
        for entrypoint in data["entrypoints"]:
            name = entrypoint["entrypoint_name"]
            if entrypoint_name == name:
                spawner.log.info(f"entrypoint is {name}")
                return dict(spawner_args=entrypoint["spawner_args"])
    else:
        return form_data

    raise ValueError # or something

c.Spawner.options_form = options_form
c.Spawner.options_from_form = options_from_form
