from flask_httpauth import HTTPBasicAuth
from partner_sync.config import read_config
from .helpers import AppDirectError

import logging

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


auth = HTTPBasicAuth()
config = read_config()
USER_DATA = {config["appdirect"]["username"]: config["appdirect"]["password"]}


@auth.verify_password
def verify(username, password):
    if not (username and password):
        raise AppDirectError("UNAUTHORIZED")
    if USER_DATA.get(username) != password:
        raise AppDirectError("UNAUTHORIZED")
    return True
