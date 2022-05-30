import json
import logging
from dataclasses import asdict
from typing import List

from migration.domain.user import User
from migration.infrastructure.mongo_database import get_user_connected_to_decathlon, get_connection_by_id
from migration.infrastructure.postgre_database import insert_user_list

PARTNER_WHITELIST = ("decathlon", "polarflow", "garminhealth", "suunto", "coros", "fitbit", "strava")


def debug_user_list(users_list: List[User]):
    [logging.info(json.dumps(asdict(o), indent=4, sort_keys=True, default=str)) for o in users_list]


if __name__ == "__main__":
    users_dict_list = get_user_connected_to_decathlon()

    logging.info("starting export")
    users = []
    for user_dict in users_dict_list:
        user = User(hub_id=user_dict["_id"])

        for service in [connected_service for connected_service in user_dict["ConnectedServices"] if
                        connected_service["Service"] in PARTNER_WHITELIST]:

            connection_object = get_connection_by_id(service["ID"])

            if service["Service"] == "decathlon":
                user.member_id = connection_object.extract_member_id()
                connection_object.connection_time = connection_object.extract_auth_time()

            user.connected_services.append(connection_object)
        users.append(user)
        # debug_user_list(users)

    logging.info(f"user length {len(users)}")

    inserted_user_count = insert_user_list(users)
    logging.info("Inserted %s connections" % inserted_user_count)
