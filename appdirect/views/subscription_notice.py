import logging
import requests


from flask import request
from flask.views import MethodView
from FreshUtils.logger import set_request_logging_context


from partner_sync.config import read_config
from partner_sync.constants import RESELLER_UUID_APPDIRECT
from .helpers import get_token, AppDirectError, AppDirectSuccess
from ..services.referral_service import ReferralService
from .auth import auth

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class SubscriptionNoticeMethodView(MethodView):
    decorators = [auth.login_required]

    def __init__(self, config: dict = read_config()) -> None:
        self.appdirect_uuid = RESELLER_UUID_APPDIRECT
        self.service = ReferralService()
        self.token = get_token(
            config["appdirect"]["subscription_client_id"], config["appdirect"]["subscription_client_secret"]
        )

    @set_request_logging_context()
    def get(self):
        eventUrl = request.args.get("eventUrl")
        headers = {"Accept": "application/json", "Authorization": f"Bearer {self.token}"}

        response = requests.get(eventUrl, headers=headers)

        if response.status_code == 200:
            log.error(f"Request to {eventUrl} was successful.")
            log.error(f"Response event json: {response.json()}")
            subscription_uuid = self.service.notice_subscription(self.appdirect_uuid, response.json())
            success = AppDirectSuccess(subscription_uuid)
            return success.response()
        else:
            # If the status code is not 200, log an error and return the status code and text response
            log.error(f"Error with geting data from event status code {response.status_code}: {response.text}")
            raise AppDirectError("TRANSPORT_ERROR", "Error with geting data from event")
