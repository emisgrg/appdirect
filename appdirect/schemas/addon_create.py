from marshmallow import fields, EXCLUDE
from partner_sync.resellers.schemas.base_schema import BaseSchema
from .subscription_base import AddonPayloadSchema


class AddonCreateSchema(BaseSchema):
    payload = fields.Nested(AddonPayloadSchema, required=True)

    class Meta:
        unknown = EXCLUDE
