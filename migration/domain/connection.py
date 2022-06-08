from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

import jwt
from bson import ObjectId

from migration.domain.authorization import Authorization

PARTNERS_NAME_TO_ID_MAPPING = {
    "decathlon": "178828e4-2ddc-401b-ac06-982273f96dd0",
    "polarflow": "11d81990-8d7b-47e3-8126-5b279cc75702",
    "garminhealth": "e8290b89-3c34-4bb2-a860-224c383077d0",
    "fitbit": "db29e30c-08b3-44d7-9112-c006bd4a85e4",
    "strava": "2d101565-703e-47bc-853b-b4a3f9de1e82",
    "coros": "e4600d73-da81-4495-86db-965a1aa25af9",
    "suunto": "dcf680aa-8148-4f93-a39a-62e0ab8135f1"
}


@dataclass
class Connection:
    hub_id: ObjectId
    partner_user_id: str
    partner_name: str
    authorization: Authorization | None = None
    connection_time: datetime | None = None

    @staticmethod
    def to_connection(connection_dict: dict) -> Connection:
        connection = Connection(
            connection_dict["_id"], connection_dict["ExternalID"], connection_dict["Service"])
        connection._convert_authorization_object(
            connection_dict["Authorization"])
        return connection

    @property
    def partner_id(self):
        return PARTNERS_NAME_TO_ID_MAPPING.get(self.partner_name)

    def _convert_authorization_object(self, authorization):
        if self.partner_name == "decathlon":
            self.authorization = Authorization.from_decathlon(authorization)
        elif self.partner_name == "polarflow":
            self.authorization = Authorization.from_polar(authorization)
        elif self.partner_name == "garminhealth":
            self.authorization = Authorization.from_garmin(authorization)
        elif self.partner_name == "fitbit":
            self.authorization = Authorization.from_fitbit(authorization)
        elif self.partner_name == "strava":
            self.authorization = Authorization.from_strava(authorization)
        elif self.partner_name == "coros":
            self.authorization = Authorization.from_coros(authorization)
        elif self.partner_name == "suunto":
            self.authorization = Authorization.from_suunto(authorization)
        else:
            logging.warning("unknown authorization type %s", self.partner_name)

    def extract_auth_time(self) -> datetime | None:
        auth_time_str = jwt.decode(
            self.authorization.access_token, algorithms=["RS256"],
            options={"verify_signature": False, "verify_exp": False}
        ).get('auth_time')

        if auth_time_str is None:
            return None

        return datetime.fromtimestamp(auth_time_str)

    def extract_member_id(self):
        return jwt.decode(
            self.authorization.access_token,
            algorithms=["RS256"],
            options={"verify_signature": False, "verify_exp": False}
        )['sub']
