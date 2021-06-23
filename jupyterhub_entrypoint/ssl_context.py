#########################################################################
# @author Rollin Thomas
# Helper class used to create Jupyter ssl cert
#########################################################################

import os
from traitlets.config import Configurable, Unicode
from jupyterhub.utils import make_ssl_context


class SSLContext(Configurable):
    """Class used to create an SSL cert to authenticate the service with Jupyter"""

    keyfile = Unicode(
        os.getenv("JUPYTERHUB_SSL_KEYFILE", ""),
        help="SSL key, use with certfile"
    ).tag(config=True)

    certfile = Unicode(
        os.getenv("JUPYTERHUB_SSL_CERTFILE", ""),
        help="SSL cert, use with keyfile"
    ).tag(config=True)

    cafile = Unicode(
        os.getenv("JUPYTERHUB_SSL_CLIENT_CA", ""),
        help="SSL CA, use with keyfile and certfile"
    ).tag(config=True)

    def ssl_context(self):
        if self.keyfile and self.certfile and self.cafile:
            return make_ssl_context(self.keyfile, self.certfile,
                                    cafile=self.cafile, check_hostname=False)
        else:
            return None
