from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass

import jwt
from bson import ObjectId

from migration.domain.authorization import Authorization


@dataclass
class Connection:
    hub_id: ObjectId
    partner_id: str
    partner_name: str
    authorization: Authorization | None = None
    connection_time: datetime.datetime | None = None

    @staticmethod
    def to_connection(connection_dict: dict) -> Connection:
        connection = Connection(
            connection_dict["_id"], connection_dict["ExternalID"], connection_dict["Service"])
        connection._convert_authorization_object(
            connection_dict["Authorization"])
        return connection

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

    def extract_auth_time(self):
        return jwt.decode(
            self.authorization.access_token, algorithms=["RS256"], options={
                "verify_signature": False,
                "verify_exp": False
            }
        ).get('auth_time')

    def extract_member_id(self):
        return jwt.decode(self.authorization.access_token,
                          algorithms=["RS256"],
                          options={
                              "verify_signature": False,
                              "verify_exp": False
                          }
                          )['sub']
