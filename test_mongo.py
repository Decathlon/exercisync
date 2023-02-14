
from pymongo import ReadPreference
from pymongo.cursor import Cursor
from tapiriik.database import db
import json


PARTNER_WHITELIST = ("decathlon", "polarflow", "garminhealth",
                     "suunto", "coros", "fitbit", "strava")


def generate_pipeline(skip):
    return [
        {
            "$sort": {
                "_id": 1
            }
        },
        {
            "$skip": skip
        },
        {
            "$limit": 1500
        },
        {
            "$project": {
                "_id": 1,
                "ConnectedServices": {
                    "$filter": {
                        "input": "$ConnectedServices",
                        "as": "connectedService",
                        "cond": {
                            "$in": [
                                "$$connectedService.Service",
                                PARTNER_WHITELIST
                            ]
                        }
                    }
                }
            }
        },
        {
            "$match": {
                "ConnectedServices": {
                    "$elemMatch": {
                        "Service": "decathlon"
                    }
                }
            }
        },
        {
            "$lookup": {
                "from": "connections",
                "localField": "ConnectedServices.ID",
                "foreignField": "_id",
                "as": "decathlon_connection",
            }
        },
        {
            "$project": {
                "_id": 1,
                "ConnectedServices": 1,
                "decathlon_connection": {
                    "$filter": {
                        "input": "$decathlon_connection",
                        "as": "connection",
                        "cond": {
                            "$eq": [
                                "$$connection.Service",
                                "decathlon"
                            ]
                        }
                    }
                }
            }
        },
        {
            "$unwind": "$decathlon_connection"
        },
        {
            "$project": {
                "_id": 1,
                "ConnectedServices": 1,
                "decathlon_connection.Authorization.AccessTokenDecathlonLogin": 1
            }
        },
        {
            "$lookup": {
                "from": "connections",
                "localField": "ConnectedServices.ID",
                "foreignField": "_id",
                "as": "connections"
            }
        },
        {
            "$unwind": "$connections"
        },
        {
            "$project": {
                "_id": 1,
                "decathlon_connection.Authorization.AccessTokenDecathlonLogin": 1,
                "connections": {
                    "_id": 1,
                    "Authorization": 1,
                    "ExternalID": 1,
                    "Service": 1
                }
            }
        }
    ]


skip_val = 0


def get_users_with_connections() -> Cursor:
    return db.users.aggregate(
        generate_pipeline(0),
        # allowDiskUse=True
    )



cursor = get_users_with_connections()

for conn in cursor:
    print(json.dumps(conn, indent=4, default=str))
    break

cursor.close()
