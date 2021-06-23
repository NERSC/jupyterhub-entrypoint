#########################################################################
# @author Rollin Thomas, Josh Geden
# Custom request handler used in entrypoint_config.py
# Fetches available shifter images from an external API
#########################################################################

import os
import json

from aiocache import cached
from aiocache.serializers import NullSerializer

from tornado import escape, httpclient, web
from jupyterhub.services.auth import HubAuthenticated
from traitlets import Unicode
from traitlets.config import Configurable


def key_builder(func, self, user):
    return user


class ShifterImageHandler(HubAuthenticated, web.RequestHandler):
    """Base request handler that handles formatting and writing results"""

    # format the result of the returned image
    def format_image(self, image):
        return {"name": image, "entrypoint": image, "type": "shifter", "id": ""}
    allow_admin = True

    # validate user and call self._get(), returns formated dict of {user: [list of images]}
    @web.authenticated
    async def get(self, user):
        current_user = self.get_current_user()
        if current_user.get("admin", False) or current_user["name"] == user:
            images = await self._get(user)
            images = list(map(self.format_image, images))
            self.write_dict({user: images})
        else:
            raise web.HTTPError(403)

    def write_dict(self, *args, **kwargs):
        if args:
            if len(args) == 1 and type(args[0]) is dict:
                self.write_json(args[0])
            else:
                raise ValueError
        else:
            self.write_json(kwargs)

    def write_json(self, document):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(escape.utf8(json.dumps(document)))

    async def _get(self, user):
        raise NotImplementedError


class APIShifterImageHandler(ShifterImageHandler, Configurable):
    """Request handler that calls external shifter API"""

    shifter_api_host = Unicode(
        os.environ.get("SHIFTER_API_HOST"),
        help="Hostname of the shifter api"
    ).tag(config=True)

    shifter_api_token = Unicode(
        os.environ.get("SHIFTER_API_TOKEN"),
        help="Secret token to access shifter api"
    ).tag(config=True)

    # fetch available shifter images from the external API
    # returns list of images or empty list
    # cache results to limit to 1 request per 60 seconds
    @cached(60, key_builder=key_builder, serializer=NullSerializer())
    async def _get(self, user):
        client = httpclient.AsyncHTTPClient()
        try:
            response = await client.fetch(f"{self.shifter_api_host}/list/{user}",
                                          headers={"Authorization": self.shifter_api_token})
        except Exception as e:
            print("Error: %s" % e)
            return []
        else:
            doc = escape.json_decode(response.body)
            images = list()
            for entry in doc.get("images", []):
                env = entry.get("ENV", [])
                if env and "NERSC_JUPYTER_IMAGE=YES" in env:
                    images += entry.get("tag", [])
            return images
