from marshmallow import fields
from .subscription_base import SubscriptionPayloadNoticeSchema, SubscriptionBaseSchema


class SubscriptionNoticeSchema(SubscriptionBaseSchema):
    payload = fields.Nested(SubscriptionPayloadNoticeSchema, required=True)
