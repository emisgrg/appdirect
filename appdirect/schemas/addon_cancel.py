from marshmallow import fields, EXCLUDE
from partner_sync.resellers.schemas.base_schema import BaseSchema
from .subscription_base import AddonPayloadCancelSchema


class AddonCancelSchema(BaseSchema):
    payload = fields.Nested(AddonPayloadCancelSchema, required=True)

    class Meta:
        unknown = EXCLUDE
