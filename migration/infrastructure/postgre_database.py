# Note: the module name is psycopg, not psycopg3
import logging
from datetime import datetime
from typing import List

import psycopg

from migration.domain.user import User
from migration.domain.connection import HUBV1_TO_HUBV2_PARTNERS_NAME_MAPPING
from migration.infrastructure.aes_gcm_encryption import AES_GCM_Engine
from tapiriik.settings import POSTGRES_HOST_API, AES_GCM_KEY

STATUS_CONNECTION_ACTIVE = "ACTIVE"
DEFAULT_REDIRECT_LOCATION = "account.decathlon.com"

def _execute_query(query, params):
    with psycopg.connect(POSTGRES_HOST_API) as conn:
        return conn.execute(query, params).fetchall()

def get_partners_id_dict():
    query = "SELECT id, name FROM partner"
    query_result = _execute_query(query, None)
    return {r[1]:r[0] for r in query_result}

def build_queries(user: User, partner_id_dict) -> List[tuple]:
    ag_engine = AES_GCM_Engine(AES_GCM_KEY)
    connection_queries = []

    for connection in user.connected_services:
        query = """
        INSERT INTO connection (
            redirect_location, creation_date, status, partner_id, member_id, access_token, refresh_token, expires_in, user_id
        ) 
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        if connection.authorization.access_token is None:
            connection_access_token = connection.authorization.access_token
        else :
            connection_access_token = ag_engine.encrypt(connection.authorization.access_token.encode())

        if connection.authorization.refresh_token is None:
            connection_refresh_token = connection.authorization.refresh_token
        else :
            connection_refresh_token = ag_engine.encrypt(connection.authorization.refresh_token.encode())

        if connection.authorization.access_token_expiration is None:        
            connection_access_token_expiration = connection.authorization.access_token_expiration
        else:
            connection_access_token_expiration = int(connection.authorization.access_token_expiration.timestamp())

        val = (
            DEFAULT_REDIRECT_LOCATION,
            connection.connection_time or datetime.now(),
            STATUS_CONNECTION_ACTIVE,
            partner_id_dict[HUBV1_TO_HUBV2_PARTNERS_NAME_MAPPING[connection.partner_name]],
            user.member_id,
            connection_access_token,
            connection_refresh_token,
            connection_access_token_expiration,
            connection.partner_user_id)

        connection_queries.append((query, val))

    return connection_queries


def insert_user_list(user_list: List[User]):
    partner_id_dict = get_partners_id_dict()
    # Connect to an existing database
    inserted_lines = 0

    with psycopg.connect(POSTGRES_HOST_API) as conn:

        # Open a cursor to perform database operations
        with conn.cursor() as cur:
            for user in user_list:
                logging.debug("Processing user with id %s" % user.hub_id)
                for connection_query in build_queries(user, partner_id_dict):
                    cur.execute(*connection_query)
                    inserted_lines += 1

            conn.commit()

    return inserted_lines
