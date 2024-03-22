from marshmallow import fields
from .subscription_base import (
    SubscriptionPayloadCancelSchema,
    SubscriptionCreatorSchema,
    SubscriptionBaseSchema,
)


class SubscriptionCancelSchema(SubscriptionBaseSchema):
    payload = fields.Nested(SubscriptionPayloadCancelSchema, required=True)
    creator = fields.Nested(SubscriptionCreatorSchema, required=True)
