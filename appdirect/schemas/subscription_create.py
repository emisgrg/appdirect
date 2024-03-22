from marshmallow import fields
from .subscription_base import (
    SubscriptionPayloadSchema,
    SubscriptionCreatorSchema,
    SubscriptionMarketplaceSchema,
    SubscriptionBaseSchema,
)


class SubscriptionCreateSchema(SubscriptionBaseSchema):
    marketplace = fields.Nested(SubscriptionMarketplaceSchema, required=True)
    payload = fields.Nested(SubscriptionPayloadSchema, required=True)
    creator = fields.Nested(SubscriptionCreatorSchema, required=True)
