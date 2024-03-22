from flask import Blueprint
from partner_sync.resellers.appdirect.views.subscription_create import SubscriptionCreateMethodView
from partner_sync.resellers.appdirect.views.subscription_change import SubscriptionChangeMethodView
from partner_sync.resellers.appdirect.views.subscription_cancel import SubscriptionCancelMethodView
from partner_sync.resellers.appdirect.views.subscription_notice import SubscriptionNoticeMethodView
from partner_sync.resellers.appdirect.views.addon_create import AddonCreateMethodView
from partner_sync.resellers.appdirect.views.addon_cancel import AddonCancelMethodView


from partner_sync.resellers.appdirect.views.test_api import TestApiMethodView
from partner_sync import PREFIX
from partner_sync.resellers.appdirect.views.helpers import AppDirectError

from marshmallow.exceptions import ValidationError
from requests.exceptions import HTTPError

import logging

log = logging.getLogger(__name__)

api_blueprint = Blueprint("appdirect", __name__, url_prefix="{}/resellers/appdirect".format(PREFIX))


@api_blueprint.errorhandler(Exception)
def handle_error(error):

    ret_error = None
    if isinstance(error, ValidationError):
        log.error(f"Problem with validating data: {error}")
        ret_error = AppDirectError("INVALID_RESPONSE", error_msg="Missing required parameter")
    elif isinstance(error, AppDirectError):
        ret_error = error

    elif isinstance(error, HTTPError):
        if error.response.status_code == 401:
            ret_error = AppDirectError("UNAUTHORIZED", error_msg="Failed to get token from AppDirect.")
        else:
            # Handle other HTTP error codes as needed
            ret_error = AppDirectError("SERVICE_UNAVAILABLE", error_msg="Http error")
    else:
        ret_error = AppDirectError("SERVICE_UNAVAILABLE", error_msg="Generic system failure.")
    return ret_error.response()


api_blueprint.add_url_rule(
    "/subscription_create", view_func=SubscriptionCreateMethodView.as_view(name="subscription_create")
)
api_blueprint.add_url_rule(
    "/subscription_change", view_func=SubscriptionChangeMethodView.as_view(name="subscription_change")
)
api_blueprint.add_url_rule(
    "/subscription_cancel", view_func=SubscriptionCancelMethodView.as_view(name="subscription_cancel")
)
api_blueprint.add_url_rule(
    "/subscription_notice",
    view_func=SubscriptionNoticeMethodView.as_view(name="subscription_notice"),
)
api_blueprint.add_url_rule("/addon_create", view_func=AddonCreateMethodView.as_view(name="addon_create"))
api_blueprint.add_url_rule("/addon_cancel", view_func=AddonCancelMethodView.as_view(name="addon_cancel"))
api_blueprint.add_url_rule("/test_api", view_func=TestApiMethodView.as_view(name="test_api"))
