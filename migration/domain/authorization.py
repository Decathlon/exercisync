from __future__ import annotations

from datetime import datetime, timedelta
from dataclasses import dataclass

PARTNERS_TOKEN_EXPIRES_IN_DICT = {
    "strava" : 21600,
    "decathlon" : 889,
    "fitbit" : 28800,
    "polarflow" : 315360000,
    "garminhealth" : None,
    "coros" : 2592000,
    "suunto" : 86400
}

@dataclass
class Authorization:
    access_token: str
    refresh_token: str | None = None
    token_fetch_date: datetime | None = None
    token_exipres_in: int | None = None
    oauthv1_token_secret: str | None = None

    @staticmethod
    def from_decathlon(authorization: dict):
        access_token_expiration=datetime.fromtimestamp(authorization["AccessTokenDecathlonLoginExpiresAt"])
        return Authorization(
            access_token=authorization["AccessTokenDecathlonLogin"],
            refresh_token=authorization["RefreshTokenDecathlonLogin"],
            token_fetch_date=access_token_expiration-timedelta(seconds=PARTNERS_TOKEN_EXPIRES_IN_DICT["decathlon"]),
            token_exipres_in=PARTNERS_TOKEN_EXPIRES_IN_DICT["decathlon"],
        )

    @staticmethod
    def from_polar(authorization: dict):
        return Authorization(
            access_token=authorization["OAuthToken"],
            token_exipres_in=PARTNERS_TOKEN_EXPIRES_IN_DICT["polarflow"],
            token_fetch_date=datetime.now()
        )

    @staticmethod
    def from_garmin(authorization: dict):
        return Authorization(
            access_token=authorization["AccessToken"],
            oauthv1_token_secret=authorization["AccessTokenSecret"]
        )

    @staticmethod
    def from_fitbit(authorization: dict):
        access_token_expiration=authorization["AccessTokenExpiresAt"]
        return Authorization(
            access_token=authorization["AccessToken"],
            refresh_token=authorization["RefreshToken"],
            token_fetch_date=access_token_expiration-timedelta(seconds=PARTNERS_TOKEN_EXPIRES_IN_DICT["fitbit"]),
            token_exipres_in=PARTNERS_TOKEN_EXPIRES_IN_DICT["fitbit"],
        )

    @staticmethod
    def from_strava(authorization: dict):
        return Authorization.from_standard(authorization,PARTNERS_TOKEN_EXPIRES_IN_DICT["strava"])

    @staticmethod
    def from_coros(authorization: dict):
        return Authorization.from_standard(authorization,PARTNERS_TOKEN_EXPIRES_IN_DICT["coros"])

    @staticmethod
    def from_suunto(authorization: dict):
        return Authorization.from_standard(authorization,PARTNERS_TOKEN_EXPIRES_IN_DICT["suunto"])

    @staticmethod
    def from_standard(authorization: dict, partner_default_expires_in: int):
        access_token_expiration=datetime.fromtimestamp(authorization["AccessTokenExpiresAt"])
        return Authorization(
            access_token=authorization["AccessToken"],
            refresh_token=authorization["RefreshToken"],
            token_fetch_date=access_token_expiration-timedelta(seconds=partner_default_expires_in),
            token_exipres_in=partner_default_expires_in,
        )
