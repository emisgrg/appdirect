import requests
from uuid import uuid4
from requests.auth import HTTPBasicAuth
from partner_sync.config import read_config
from partner_sync.models.referral import Referral
import logging
from flask import Response, make_response, jsonify

from http import HTTPStatus


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def get_token(client_id, client_secret):

    # URL to make the POST request to
    url = "https://marketplace.appdirect.com/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    body = {"grant_type": "client_credentials", "scope": "ROLE_APPLICATION"}

    # Making the POST request

    response = requests.post(
        url,
        auth=HTTPBasicAuth(client_id, client_secret),
        headers=headers,
        data=body,
    )

    # If the request was successful, return the JSON response
    if response.status_code == 200:
        try:
            response_json = response.json()
            log.error(f"Response token json: {response_json}")
            return response.json()["access_token"]
        except ValueError:
            # If parsing as JSON fails, log and return the text response
            response_text = response.text
            log.error(f"Response token txt: {response_text}")
            return response_text
    else:
        # Otherwise, raise an exception with the response text
        log.error(f"Error with geting token datastatus code {response.status_code}: {response.text}")
        response.raise_for_status()


class AppDirectError(Exception):
    ERROR_CODE_MAP = {
        "USER_ALREADY_EXISTS": (HTTPStatus.BAD_REQUEST, "User already exists."),
        "USER_NOT_FOUND": (HTTPStatus.NOT_FOUND, "User not found."),
        "ACCOUNT_NOT_FOUND": (HTTPStatus.NOT_FOUND, "Account not found."),
        "MAX_USERS_REACHED": (HTTPStatus.FORBIDDEN, "Maximum users reached."),
        "UNAUTHORIZED": (HTTPStatus.UNAUTHORIZED, "Unauthorized action."),
        "OPERATION_CANCELLED": (HTTPStatus.BAD_REQUEST, "Operation cancelled by user."),
        "CONFIGURATION_ERROR": (HTTPStatus.BAD_REQUEST, "Configuration error."),
        "INVALID_RESPONSE": (HTTPStatus.BAD_REQUEST, "Invalid response from vendor."),
        "PENDING": (HTTPStatus.OK, "Service under provisioning."),
        "FORBIDDEN": (HTTPStatus.FORBIDDEN, "Operation not allowed."),
        "BINDING_NOT_FOUND": (HTTPStatus.NOT_FOUND, "Binding not found."),
        "TRANSPORT_ERROR": (HTTPStatus.SERVICE_UNAVAILABLE, "Transport error, server unreachable."),
        "UNKNOWN_ERROR": (HTTPStatus.INTERNAL_SERVER_ERROR, "Unknown error occurred."),
    }

    def __init__(self, error_code: str, error_msg: str = None):
        self.error_code = error_code
        status, message = self.ERROR_CODE_MAP.get(
            error_code, (HTTPStatus.INTERNAL_SERVER_ERROR, "Unknown error code.")
        )
        self.status_code = status.value
        self.payload = {
            "success": "False",
            "accountIdentifier": None,
            "errorCode": error_code,
            "message": error_msg if error_msg else message,
        }

    def response(self) -> Response:
        return make_response(jsonify(self.payload), self.status_code)


class AppDirectSuccess:
    def __init__(self, identifier: uuid4):
        self.status_code = HTTPStatus.OK.value
        self.payload = {
            "success": "True",
            "accountIdentifier": identifier,
        }

    def response(self):
        return make_response(jsonify(self.payload), self.status_code)
