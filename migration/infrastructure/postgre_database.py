# Note: the module name is psycopg, not psycopg3
import logging
import psycopg
from migration.domain.authorization import Authorization
from migration.domain.user import User
import uuid
from datetime import datetime
from bson import ObjectId
from typing import List
from migration.domain.connection import Connection




def build_queries(user: User) -> List[tuple]:
    connection_queries = []

    for connection in user.connected_services:
        query = """INSERT INTO connection (redirect_location, correlation_id, creation_date, status, partner_id, member_id, access_token, refresh_token, expires_in, user_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
        val = (
            "localhost",
            "a9f91ab9-3951-4490-b21e-fdc058aedb2b",
            datetime.now(),
            "ACTIVE",
            "11d81990-8d7b-47e3-8126-5b279cc75702",
            user.member_id,
            connection.authorization.access_token,
            connection.authorization.refresh_token,
            connection.authorization.access_token_expiration,
            connection.partner_id)

        connection_queries.append((query, val))
    
    return connection_queries



def insert_user_list(user_list: List[User]):

    # Connect to an existing database
    with psycopg.connect("postgresql://sport_hub:[password]@localhost:5432/sport_hub") as conn:

        # Open a cursor to perform database operations
        with conn.cursor() as cur:
            for user in user_list:
                print(user.hub_id)
                for connection_query in build_queries(user):
                    cur.execute(*connection_query)


            cur.execute("""
                SELECT * FROM connection
                """)

            print(cur.rowcount)

            conn.commit()
