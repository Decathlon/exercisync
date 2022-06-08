# Note: the module name is psycopg, not psycopg3
import logging
from datetime import datetime
from typing import List

import psycopg

from migration.domain.user import User
from tapiriik.settings import POSTGRES_HOST_API

STATUS_CONNECTION_ACTIVE = "ACTIVE"
DEFAULT_REDIRECT_LOCATION = "account.decathlon.com"


def build_queries(user: User) -> List[tuple]:
    connection_queries = []

    for connection in user.connected_services:
        query = """
        INSERT INTO connection (
            redirect_location, creation_date, status, partner_id, member_id, access_token, refresh_token, expires_in, user_id
        ) 
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        val = (
            DEFAULT_REDIRECT_LOCATION,
            connection.connection_time or datetime.now(),
            STATUS_CONNECTION_ACTIVE,
            connection.partner_id,
            user.member_id,
            connection.authorization.access_token,
            connection.authorization.refresh_token,
            connection.authorization.access_token_expiration,
            connection.partner_user_id)

        connection_queries.append((query, val))

    return connection_queries


def insert_user_list(user_list: List[User]):
    # Connect to an existing database
    inserted_lines = 0

    with psycopg.connect(POSTGRES_HOST_API) as conn:

        # Open a cursor to perform database operations
        with conn.cursor() as cur:
            for user in user_list:
                logging.debug("Processing user with id %s" % user.hub_id)
                for connection_query in build_queries(user):
                    cur.execute(*connection_query)
                    inserted_lines += 1

            conn.commit()

    return inserted_lines
