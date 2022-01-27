
import os

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

# Define pre-spawn hook to rewrite Spawner.cmd before start()
# May need to look a bit different if options_form is defined!
#
# If there are multiple tags defined in the entrypoint service, the pre-spawn
# hook needs to know how to figure out which one should be requested. One way
# to do this would be to leverage named servers and read the "name" spawner
# attribute.

async def pre_spawn_hook(spawner):
    user = spawner.user.name
    client = AsyncHTTPClient()
    try:
        args = {
            "batchspawner": "no"
        }
        url = url_concat(
            f"http://127.0.0.1:8889/services/entrypoint/api/users/{user}/selections/hal",
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
        with spawner.hold_trait_notifications():
            for key, value in data.items():
                if spawner.has_trait(key):
                    setattr(spawner, key, value)

c.Spawner.pre_spawn_hook = pre_spawn_hook
