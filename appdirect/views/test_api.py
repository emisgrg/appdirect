import logging
import requests
import uuid


from flask import jsonify, make_response, request
from flask.views import MethodView
from FreshUtils.logger import set_request_logging_context
from werkzeug.exceptions import ServiceUnavailable


from partner_sync.config import read_config
from partner_sync.constants import RESELLER_UUID_APPDIRECT
from partner_sync.oauth import require_oauth
from .helpers import get_token
from .auth import auth

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class TestApiMethodView(MethodView):
    decorators = [auth.login_required]

    def __init__(self, config: dict = read_config()) -> None:
        self.appdirect_uuid = RESELLER_UUID_APPDIRECT
        self.token_addon = get_token(
            config["appdirect"]["addon_client_id"], config["appdirect"]["addon_client_secret"]
        )
        self.token_subscription = get_token(
            config["appdirect"]["subscription_client_id"], config["appdirect"]["subscription_client_secret"]
        )

    @set_request_logging_context()
    def get(self):
        eventUrl = request.args.get("eventUrl")
        headers = {"Accept": "application/json", "Authorization": f"Bearer {self.token_addon}"}

        response = requests.get(eventUrl, headers=headers)
        if response.status_code == 401:
            headers = {"Accept": "application/json", "Authorization": f"Bearer {self.token_subscription}"}
            response = requests.get(eventUrl, headers=headers)

        if response.status_code == 200:
            log.error(f"Request to {eventUrl} was successful.")
            # Try to parse the response as JSON
            try:
                response_json = response.json()
                log.error(f"Response event json: {response_json}")
                account_idenitifier = uuid.uuid4()
                if response_json["payload"]["account"]:
                    account_idenitifier = response_json["payload"]["account"]["accountIdentifier"]
                return make_response(
                    jsonify(
                        {
                            "success": "True",
                            "accountIdentifier": account_idenitifier,
                        }
                    ),
                    200,
                    headers,
                )
            except ValueError:
                # If parsing as JSON fails, log and return the text response
                response_text = response.text
                log.error(f"Response event txt: {response_text}")
                return make_response(jsonify({"status": "sucesfful"}), 200, headers)
        else:
            # If the status code is not 200, log an error and return the status code and text response
            log.error(f"Error with geting data from event status code {response.status_code}: {response.text}")
            return make_response(jsonify({"status": "unsucesfful"}), response.status_code, headers)
