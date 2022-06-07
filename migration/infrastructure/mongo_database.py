from __future__ import annotations

from typing import List

from bson import ObjectId

from migration.domain.connection import Connection
from tapiriik.database import db


def get_all_connections() -> List[Connection]:
    return [Connection.to_connection(conn) for conn in db.connections.find()]


def get_connections_by_partner_name(partner_name: str) -> List[Connection]:
    return [Connection.to_connection(conn) for conn in db.connections.find({"Service": partner_name})]


def get_connection_by_id(connection_id: ObjectId) -> Connection | None:
    connection_dict = db.connections.find_one({"_id": connection_id})
    if connection_dict is not None:
        return Connection.to_connection(connection_dict)
    else:
        return None


def get_all_users() -> list:
    return list(db.users.find())


def get_user_by_connection_id(connection_id: ObjectId) -> List[dict]:
    return list(db.users.aggregate(
        [
            {
                '$match': {
                    "ConnectedServices": {
                        '$elemMatch': {
                            'ID': connection_id
                        }
                    }
                }
            }
        ]
    ))


def get_user_connected_to_decathlon() -> List[dict]:
    return list(db.users.aggregate(
        [
            {
                '$match': {
                    "ConnectedServices": {
                        '$elemMatch': {
                            'Service': "decathlon"
                        }
                    }
                }
            }
        ]
    ))
