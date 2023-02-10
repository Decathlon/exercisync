# Note: the module name is psycopg, not psycopg3
import logging
from datetime import datetime
from typing import List

import psycopg

from migration.domain.user import User
from migration.domain.connection import HUBV1_TO_HUBV2_PARTNERS_NAME_MAPPING, Connection
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

def _encrypt_if_not_none(encryption_engine :AES_GCM_Engine, str_to_encrypt: str | None) -> str | bytes | None:
    if str_to_encrypt is None:
        return str_to_encrypt
    else :
        return encryption_engine.encrypt(str_to_encrypt)

def build_queries(connection: Connection, partner_id_dict) -> tuple:
    ag_engine = AES_GCM_Engine(AES_GCM_KEY)

    query = """
    INSERT INTO connection (
        redirect_location, 
        creation_date, 
        status, 
        partner_id, 
        member_id, 
        access_token, 
        refresh_token, 
        expires_in, 
        user_id, 
        oauth_token_secret,
        tokens_fetch_date
    ) 
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    connection_access_token = _encrypt_if_not_none(ag_engine, connection.authorization.access_token)
    connection_refresh_token = _encrypt_if_not_none(ag_engine, connection.authorization.refresh_token)
    connection_oauthv1_token_secret = _encrypt_if_not_none(ag_engine, connection.authorization.oauthv1_token_secret)


    val = (
        DEFAULT_REDIRECT_LOCATION,
        connection.get_connection_date(),
        STATUS_CONNECTION_ACTIVE,
        partner_id_dict[HUBV1_TO_HUBV2_PARTNERS_NAME_MAPPING[connection.partner_name]],
        connection.get_member_id(),
        connection_access_token,
        connection_refresh_token,
        connection.authorization.token_exipres_in,
        connection.partner_user_id,
        connection_oauthv1_token_secret,
        connection.authorization.token_fetch_date
    )

    return (query, val)


def insert_connection(connections: List[Connection], partner_ids: dict):
    # Connect to an existing database

    with psycopg.connect(POSTGRES_HOST_API) as conn:

        # Open a cursor to perform database operations
        with conn.cursor() as cur:
            for connection in connections:
                try:
                    cur.execute(*build_queries(connection, partner_ids))
                except Exception as e:
                    logging.error(f"Failed to push connections from HUB v1 user id {connection.hub_id}, ERROR : {e}")

            conn.commit()



