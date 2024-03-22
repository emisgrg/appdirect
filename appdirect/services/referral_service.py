import logging
import json
from typing import Optional
import uuid
from datetime import datetime
from operator import itemgetter

from partner_sync.config import read_config
from partner_sync.daos.reseller_dao import ResellerDao
from partner_sync.daos.referral_dao import ReferralDao
from partner_sync.database import db
from partner_sync.models.lead import Referral
from partner_sync.models.referral_identity import ReferralIdentity
from partner_sync.services.masterlock_service import MasterlockService
from partner_sync.services.billing_service import BillingService
from partner_sync.resellers.appdirect.views.helpers import AppDirectError
from partner_sync.resellers.appdirect.schemas.subscription_create import (
    SubscriptionCreateSchema,
)
from partner_sync.resellers.appdirect.schemas.subscription_change import (
    SubscriptionChangeSchema,
)
from partner_sync.resellers.appdirect.schemas.subscription_chancel import (
    SubscriptionCancelSchema,
)
from partner_sync.resellers.appdirect.schemas.subscription_notice import (
    SubscriptionNoticeSchema,
)
from partner_sync.resellers.appdirect.schemas.addon_create import AddonCreateSchema
from partner_sync.resellers.appdirect.schemas.addon_cancel import AddonCancelSchema
from partner_sync.constants import (
    REFERRAL_STATUS_CANCEL,
    REFERRAL_STATUS_COMMENT,
    REFERRAL_STATUS_ACTIVE,
)

log = logging.getLogger(__name__)


class ReferralService:
    META_PLAN_ID = "plan_id"
    META_PREVIOUSE_PLAN_ID = "previouse_plan_id"
    META_ADDONS = "addons"
    META_FIRST_NAME = "first_name"
    META_LAST_NAME = "last_name"
    META_ADDONS_MAPPING = "addons_mapping"
    META_PARTNER_ID = "partner_id"
    META_PARTNER_URL = "partner_url"

    def __init__(self, config: dict = read_config()) -> None:
        self.config = config
        self.reseller_dao = ResellerDao()
        self.referral_dao = ReferralDao()
        self.masterlock_service = MasterlockService(self.config["masterlock"])
        self.billing_service = BillingService()

    def create_subscription(
        self, reseller_uuid: uuid.UUID, payload: dict
    ) -> Optional[Referral]:
        schema = SubscriptionCreateSchema()
        referral = None

        try:
            reseller = self.reseller_dao.find_by_uuid(reseller_uuid)

            if not reseller:
                log.error(f"Reseller not found for uuid {reseller_uuid}")
                raise AppDirectError(
                    "UNKNOWN_ERROR", "System is down. Please try again later."
                )

            data = schema.load(payload)

            if data["development"]:
                name, domain = data["creator"]["email"].split("@")
                email = f'{name}+{datetime.now().strftime("%Y%m%d%H%M%S")}@{domain}'
            else:
                email = data["creator"]["email"]
            first_name = data["creator"]["first_name"]
            last_name = data["creator"]["last_name"]
            business_name = data["payload"]["company"]["name"]
            plan_id = data["payload"]["order"]["plan_id"]
            partner_id = data["marketplace"]["partner"]
            partner_url = data["marketplace"]["base_url"]

            register = self.masterlock_service.register_reseller(
                plan_id,
                email,
                reseller_uuid,
                partner_id,
                first_name,
                last_name,
                business_name,
                partner_url,
            )

            register_data = register["response"]

            referral_uuid = uuid.uuid4()

            # Create the referral
            referral = Referral(
                uuid=referral_uuid,
                business_name=business_name,
                reseller=reseller,
                business_uuid=uuid.UUID(register_data["freshbooks_business_uuid"]),
                system_id=register_data["freshbooks_system_id"],
            )
            referral["addons"] = {}

            # Create the referral identity
            referral_identity_uuid = uuid.uuid4()

            referral_identity = ReferralIdentity(
                uuid=referral_identity_uuid,
                email=email,
                email_preverified=True,
                is_admin=True,
                identity_uuid=uuid.UUID(register_data["freshbooks_identity_uuid"]),
            )

            referral_identity[ReferralService.META_FIRST_NAME] = first_name
            referral_identity[ReferralService.META_LAST_NAME] = last_name
            referral[ReferralService.META_PLAN_ID] = plan_id
            referral[ReferralService.META_ADDONS_MAPPING] = {}
            referral[ReferralService.META_PARTNER_ID] = partner_id
            referral[ReferralService.META_PARTNER_URL] = partner_url

            referral.identities.append(referral_identity)

            db.session.add(referral)

            addons = [
                {"plan_id": key, "quantity": value}
                for key, value in data["payload"]["order"]["items"].items()
            ]

            self.billing_service.update_reseller(
                data["payload"]["order"]["plan_id"],
                referral.system_id,
                addons,
            )

            referral[ReferralService.META_ADDONS] = json.dumps(
                sorted(addons, key=itemgetter("plan_id"))
            )

        except Exception as ex:
            log.exception(f"Unexpected error while creating referral {ex}")
            raise

        return referral.uuid

    def change_subscription(
        self, reseller_uuid: uuid.UUID, payload: dict
    ) -> Optional[Referral]:
        schema = SubscriptionChangeSchema()

        referral = None

        try:
            reseller = self.reseller_dao.find_by_uuid(reseller_uuid)

            if not reseller:
                log.error(f"Reseller not found for uuid {reseller_uuid}")
                raise AppDirectError(
                    "UNKNOWN_ERROR", "System is down. Please try again later."
                )

            data = schema.load(payload)

            referral = self.referral_dao.find_by_uuid(
                data["payload"]["account"]["referral_uuid"]
            )

            if referral is None:
                log.warning(
                    f'Not able to load referral for  {data["payload"]["account"]["referral_uuid"]}'
                )
                raise AppDirectError(
                    "ACCOUNT_NOT_FOUND", "Account with this uuid doesn't exist"
                )
            subscription = self.billing_service.get_subscription(referral.system_id)

            existing_addons = {
                addon["plan_id"]: addon["quantity"]
                for addon in subscription["response"]["addons"]
            }
            updated_addons = data["payload"]["order"]["items"]
            addons = []
            all_addons_id = set(existing_addons.keys()).union(updated_addons.keys())

            for addon_id in all_addons_id:
                quantity = updated_addons.get(addon_id, existing_addons.get(addon_id))
                if quantity != 0:
                    addons.append({"plan_id": addon_id, "quantity": quantity})

            self.billing_service.update_reseller(
                data["payload"]["order"]["plan_id"],
                referral.system_id,
                addons,
            )

            referral[ReferralService.META_PREVIOUSE_PLAN_ID] = referral["plan_id"]
            referral[ReferralService.META_PLAN_ID] = data["payload"]["order"]["plan_id"]
            referral[ReferralService.META_ADDONS] = json.dumps(
                sorted(addons, key=itemgetter("plan_id"))
            )

        except Exception as ex:
            log.exception(f"Unexpected error while getting referral {ex}")
            raise

        return referral.uuid

    def cancel_subscription(
        self, reseller_uuid: uuid.UUID, payload: dict
    ) -> Optional[Referral]:
        schema = SubscriptionCancelSchema()

        referral = None

        try:
            reseller = self.reseller_dao.find_by_uuid(reseller_uuid)

            if not reseller:
                log.error(f"Reseller not found for uuid {reseller_uuid}")
                raise AppDirectError(
                    "UNKNOWN_ERROR", "System is down. Please try again later."
                )

            data = schema.load(payload)

            referral = self.referral_dao.find_by_uuid(
                data["payload"]["account"]["referral_uuid"]
            )

            if referral is None:
                log.warning(
                    f'Not able to load referral for  {data["payload"]["account"]["referral_uuid"]}'
                )
                raise AppDirectError(
                    "ACCOUNT_NOT_FOUND", "Account with this uuid doesn't exist"
                )
            self.billing_service.cancel_reseller(
                REFERRAL_STATUS_CANCEL,
                REFERRAL_STATUS_COMMENT,
                referral.system_id,
            )

        except Exception as ex:
            log.exception(f"Unexpected error while getting referral {ex}")
            raise

        return referral.uuid

    def notice_subscription(
        self, reseller_uuid: uuid.UUID, payload: dict
    ) -> Optional[Referral]:
        schema = SubscriptionNoticeSchema()

        referral = None

        try:
            reseller = self.reseller_dao.find_by_uuid(reseller_uuid)

            if not reseller:
                log.error(f"Reseller not found for uuid {reseller_uuid}")
                raise AppDirectError(
                    "UNKNOWN_ERROR", "System is down. Please try again later."
                )

            data = schema.load(payload)

            referral = self.referral_dao.find_by_uuid(
                data["payload"]["account"]["referral_uuid"]
            )

            if referral is None:
                log.warning(
                    f'Not able to load referral for  {data["payload"]["account"]["referral_uuid"]}'
                )
                raise AppDirectError(
                    "ACCOUNT_NOT_FOUND", "Account with this uuid doesn't exist"
                )

            if data["payload"]["notice"]["type"] in ["DEACTIVATED", "CLOSED"]:
                self.billing_service.cancel_reseller(
                    REFERRAL_STATUS_CANCEL,
                    REFERRAL_STATUS_COMMENT,
                    referral.system_id,
                )
            elif data["payload"]["notice"]["type"] in ["REACTIVATED"]:
                self.billing_service.reactivate_reseller(
                    REFERRAL_STATUS_ACTIVE,
                    data["payload"]["notice"].get(
                        "message", "Subscription reactivated by user"
                    ),
                    referral.system_id,
                )

        except Exception as ex:
            log.exception(f"Unexpected error while getting referral {ex}")
            raise

        return referral.uuid

    def create_addon(
        self, reseller_uuid: uuid.UUID, payload: dict
    ) -> Optional[Referral]:
        schema = AddonCreateSchema()
        referral = None

        try:
            reseller = self.reseller_dao.find_by_uuid(reseller_uuid)

            if not reseller:
                log.error(f"Reseller not found for uuid {reseller_uuid}")
                raise AppDirectError(
                    "UNKNOWN_ERROR", "System is down. Please try again later."
                )

            data = schema.load(payload)

            referral = self.referral_dao.find_by_uuid(
                data["payload"]["account"]["referral_uuid"]
            )

            if referral is None:
                log.warning(
                    f'Not able to load referral for  {data["payload"]["account"]["referral_uuid"]}'
                )
                raise AppDirectError(
                    "ACCOUNT_NOT_FOUND", "Account with this uuid doesn't exist"
                )

            subscription = self.billing_service.get_subscription(referral.system_id)
            existing_addons = {
                addon["plan_id"]: addon["quantity"]
                for addon in subscription["response"]["addons"]
            }
            new_addon = {
                data["payload"]["order"]["edition_code"]: data["payload"]["order"][
                    "quantity"
                ]
            }

            existing_addons.update(new_addon)
            addons = [{key: value} for key, value in existing_addons.items()]

            self.billing_service.update_reseller(
                referral["plan_id"],
                referral.system_id,
                addons,
            )
            referral["addons"] = json.dumps(addons)
            addon_mappings = json.loads(referral["addons_mapping"])
            if data["payload"]["order"]["edition_code"] not in addon_mappings.keys():
                addon_uuid = uuid.uuid4()
                addon_mappings.update(
                    {data["payload"]["order"]["edition_code"]: addon_uuid}
                )
                referral["addons_mapping"] = addon_mappings
            else:
                addon_uuid = addon_mappings[data["payload"]["order"]["edition_code"]]
        except Exception as ex:
            log.exception(f"Unexpected error while getting referral '{ex}''")
            raise

        return addon_uuid

    def cancel_addon(
        self, reseller_uuid: uuid.UUID, payload: dict
    ) -> Optional[Referral]:
        schema = AddonCancelSchema()
        referral = None

        try:
            reseller = self.reseller_dao.find_by_uuid(reseller_uuid)

            if not reseller:
                log.error(f"Reseller not found for uuid {reseller_uuid}")
                raise AppDirectError(
                    "UNKNOWN_ERROR", "System is down. Please try again later."
                )

            data = schema.load(payload)

            referral = self.referral_dao.find_by_uuid(
                data["payload"]["account"]["referral_uuid"]
            )

            if referral is None:
                log.warning(
                    f'Not able to load referral for  {data["payload"]["account"]["referral_uuid"]}'
                )
                raise AppDirectError(
                    "ACCOUNT_NOT_FOUND", "Account with this uuid doesn't exist"
                )

            subscription = self.billing_service.get_subscription(referral.system_id)
            existing_addons = {
                addon["plan_id"]: addon["quantity"]
                for addon in subscription["response"]["addons"]
            }

            addons_mapping = json.loads(referral["addons_mapping"])
            addon_id = next(
                (
                    key
                    for key, value in addons_mapping.items()
                    if data["payload"]["account"]["addon_uuid"] in value
                ),
                None,
            )

            if addon_id is None:
                log.warning(
                    f'Not able to find addon reference for {data["payload"]["account"]["addon_uuid"]}'
                )
                raise AppDirectError(
                    "ACCOUNT_NOT_FOUND", "Account with this uuid doesn't exist"
                )

            if existing_addons:
                existing_addons.pop(addon_id)
                addons = [{key: value} for key, value in existing_addons.items()]
            else:
                addons = []
            self.billing_service.update_reseller(
                referral["plan_id"],
                referral.system_id,
                addons,
            )
            referral["addons"] = json.dumps(addons)

        except Exception as ex:
            log.exception(f"Unexpected error while getting referral '{ex}''")
            raise

        return data["payload"]["account"]["addon_uuid"]
