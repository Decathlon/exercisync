from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

import jwt
from bson import ObjectId

from migration.domain.authorization import Authorization
from migration.domain.errors import DecathlonAuthorizationMappingError

HUBV1_TO_HUBV2_PARTNERS_NAME_MAPPING = {
    "decathlon": "DECATHLON",
    "polarflow": "POLAR",
    "garminhealth": "GARMIN",
    "fitbit": "FITBIT",
    "strava": "STRAVA",
    "coros": "COROS",
    "suunto": "SUUNTO"
}


@dataclass
class Connection:
    hub_id: ObjectId
    partner_user_id: str
    partner_name: str
    decoded_decathlon_token: dict
    authorization: Authorization | None = None


    @staticmethod
    def to_connection(user_with_connection: dict) -> Connection:
        connection_dict = user_with_connection["connections"]

        try:
            decoded_decathlon_jwt = jwt.decode(
                    user_with_connection["decathlon_connection"]["Authorization"]["AccessTokenDecathlonLogin"], algorithms=["RS256"],
                    options={"verify_signature": False, "verify_exp": False}
                )
        except KeyError as e:
            raise DecathlonAuthorizationMappingError(user_with_connection["decathlon_connection"]["Authorization"], "Can't map the Decathlon authorization dict to Authorization class")

        connection = Connection(
            connection_dict["_id"], 
            connection_dict["ExternalID"], 
            connection_dict["Service"],
            decoded_decathlon_jwt
            )

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
        

    def get_member_id(self) -> str:
        return self.decoded_decathlon_token["sub"]


    def get_connection_date(self) -> datetime:
        if self.partner_name == "decathlon":
            auth_time_from_jwt = self.decoded_decathlon_token.get("auth_time")
            if auth_time_from_jwt is not None:
                return datetime.fromtimestamp(auth_time_from_jwt)
        return datetime.now()

