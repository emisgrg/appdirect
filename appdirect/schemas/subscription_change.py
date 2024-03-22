from marshmallow import fields
from .subscription_base import (
    SubscriptionPayloadAccountSchema,
    SubscriptionCreatorSchema,
    SubscriptionBaseSchema,
)


class SubscriptionChangeSchema(SubscriptionBaseSchema):
    payload = fields.Nested(SubscriptionPayloadAccountSchema, required=True)
    creator = fields.Nested(SubscriptionCreatorSchema, required=True)
