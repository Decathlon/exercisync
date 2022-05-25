from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass


@dataclass
class Authorization:
    access_token: str
    refresh_token: str | None = None
    access_token_expiration: datetime | None = None

    @staticmethod
    def from_decathlon(authorization: dict):
        return Authorization(
            access_token=authorization["AccessTokenDecathlonLogin"],
            refresh_token=authorization["RefreshTokenDecathlonLogin"],
            access_token_expiration=datetime.fromtimestamp(authorization["AccessTokenDecathlonLoginExpiresAt"])
        )

    @staticmethod
    def from_polar(authorization: dict):
        return Authorization(
            access_token=authorization["OAuthToken"]
        )

    @staticmethod
    def from_garmin(authorization: dict):
        return Authorization(
            access_token=authorization["AccessToken"],
        )

    @staticmethod
    def from_fitbit(authorization: dict):
        return Authorization(
            access_token=authorization["AccessToken"],
            refresh_token=authorization["RefreshToken"],
            access_token_expiration=authorization["AccessTokenExpiresAt"]
        )

    @staticmethod
    def from_strava(authorization: dict):
        return Authorization.from_standard(authorization)

    @staticmethod
    def from_coros(authorization: dict):
        return Authorization.from_standard(authorization)

    @staticmethod
    def from_suunto(authorization: dict):
        return Authorization.from_standard(authorization)

    @staticmethod
    def from_standard(authorization: dict):
        return Authorization(
            access_token=authorization["AccessToken"],
            refresh_token=authorization["RefreshToken"],
            access_token_expiration=datetime.fromtimestamp(authorization["AccessTokenExpiresAt"])
        )
