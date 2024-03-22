from marshmallow import fields, validate, post_load, pre_load
from marshmallow.exceptions import ValidationError
from partner_sync.resellers.schemas.base_schema import BaseSchema
from partner_sync.constants import APP_DIRECT_NOTICES
from partner_sync.config import read_config


config = read_config()


class AddonOrderItemsSchema(BaseSchema):
    quantity = fields.Integer(required=True)


class AddonPayloadOrderSchema(BaseSchema):
    edition_code = fields.String(data_key="editionCode", required=True)
    pricing_duration = fields.String(data_key="pricingDuration", required=True)
    quantity = fields.Nested(
        AddonOrderItemsSchema(many=True), data_key="items", required=True
    )

    @post_load
    def format_quantity(self, data, **kwargs):
        data["quantity"] = data["quantity"][0]["quantity"] if data["quantity"] else None
        return data


class AddonPayloadOrderItemSchema(BaseSchema):
    edition_code = fields.String(data_key="editionCode", required=True)
    pricing_duration = fields.String(data_key="pricingDuration", required=True)


class OrderItemsSchema(BaseSchema):
    quantity = fields.Integer(required=True)
    unit = fields.String(requierd=True)

    @post_load
    def format_quantity(self, data, **kwargs):
        data = {data["unit"]: data["quantity"]}
        return data


class PayloadOrderSchema(BaseSchema):
    edition_code = fields.String(data_key="editionCode", required=True)
    pricing_duration = fields.String(data_key="pricingDuration", required=True)
    items = fields.Nested(OrderItemsSchema(many=True), required=True)

    @post_load
    def format_quantity(self, data, **kwargs):
        plan_id = config["appdirect"]["plan_id_mapping"].get(
            f"{data['edition_code']}_{data['pricing_duration']}".upper()
        )
        if not plan_id:
            raise ValidationError("Not supported edition code")
        extra_staff_id = config["appdirect"]["extra_staff_addon_id_mapping"].get(
            plan_id
        )
        advanc_payment_id = config["appdirect"]["advance_payment_addon_id_mapping"].get(
            plan_id
        )
        addons = {advanc_payment_id: 1}
        for item in data["items"]:
            if "ADDITIONAL_USER" in item:
                addons.update({extra_staff_id: item["ADDITIONAL_USER"]})
        data["items"] = addons
        data["plan_id"] = plan_id
        return data


class PayloadOrderItemSchema(BaseSchema):
    edition_code = fields.String(data_key="editionCode", required=True)
    pricing_duration = fields.String(data_key="pricingDuration", required=True)


class PayloadCompanySchema(BaseSchema):
    name = fields.String(required=True)


class SubscriptionPayloadSchema(BaseSchema):
    order = fields.Nested(PayloadOrderSchema, required=True)
    company = fields.Nested(PayloadCompanySchema, required=True, allow_none=True)


class SubscriptionCreatorSchema(BaseSchema):
    email = fields.Email(required=True)
    first_name = fields.String(data_key="firstName", required=True)
    last_name = fields.String(data_key="lastName", required=True)


class PayloadAccountSchema(BaseSchema):
    referral_uuid = fields.String(data_key="accountIdentifier", required=True)
    status = fields.String(data_key="status", required=True)


class AddonPayloadAccountSchema(BaseSchema):
    referral_uuid = fields.String(data_key="parentAccountIdentifier", required=True)
    addon_uuid = fields.String(
        data_key="accountIdentifier", required=False, allow_none=True
    )
    status = fields.String(data_key="status", required=True)


class PayloadNoticeSchema(BaseSchema):
    type = fields.String(required=True, validate=validate.OneOf(APP_DIRECT_NOTICES))
    message = fields.String(required=True, allow_none=True)


class SubscriptionPayloadAccountSchema(SubscriptionPayloadSchema):
    account = fields.Nested(PayloadAccountSchema, required=True)


class SubscriptionMarketplaceSchema(BaseSchema):
    partner = fields.String(required=True)
    base_url = fields.String(requierd=True, data_key="baseUrl")


class SubscriptionPayloadCancelSchema(BaseSchema):
    account = fields.Nested(PayloadAccountSchema, required=True)


class SubscriptionPayloadNoticeSchema(BaseSchema):
    account = fields.Nested(PayloadAccountSchema, required=True)
    notice = fields.Nested(PayloadNoticeSchema, required=True)


class AddonPayloadSchema(BaseSchema):
    account = fields.Nested(AddonPayloadAccountSchema, required=True)
    order = fields.Nested(AddonPayloadOrderSchema, required=True)


class AddonPayloadCancelSchema(BaseSchema):
    account = fields.Nested(AddonPayloadAccountSchema, required=True)


class SubscriptionBaseSchema(BaseSchema):
    development = fields.Boolean(required=True)

    @pre_load
    def format_development(self, data, **kwargs):
        if data.get("flag") and data.get("flag") == "DEVELOPMENT":
            data["development"] = True
        else:
            data["development"] = False
        return data
