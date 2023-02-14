from datetime import datetime

from migration.domain.connection import Connection
from migration.infrastructure.mongo_database import get_users_with_connections
from migration.infrastructure.postgre_database import insert_connection, get_partners_id_dict
from migration.infrastructure.migration_logger import MigrationLogger

from migration.domain.errors import DecathlonAuthorizationMappingError



if __name__ == "__main__":

    logger = MigrationLogger.init()

    logger.info("----- Starting HUBV1 to HUBV2 mapping -----")
    user_map_begin = datetime.now()

    partner_id_dict = get_partners_id_dict()

    inserted_lines = 0

    connection_list = []
    connection_push_times = []

    max_skip = 155000
    actual_skip = 0

    while actual_skip <= max_skip:
        try:
            user_with_connections_cursor = get_users_with_connections(actual_skip)

            while user_with_connections_cursor.alive:
                user_with_connection = user_with_connections_cursor.next()
                try :
                    connection_list.append(Connection.to_connection(user_with_connection))
                    if len(connection_list) == 3000 or not user_with_connections_cursor.alive:
                        connection_push_begin = datetime.now()
                        insert_connection(connection_list, partner_id_dict)

                        connection_push_end = datetime.now()
                        connection_push_delta = connection_push_end - connection_push_begin
                        connection_push_times.append(connection_push_delta.total_seconds())

                        inserted_lines += len(connection_list)
                        connection_list = []

                except DecathlonAuthorizationMappingError as e:
                        logger.debug(f"HUB user ID : {user_with_connection['_id']} - {e.message} - {e.authorization_dict}")
                        continue
                except Exception as e:
                    logger.error(f"Error: {e} Data: {user_with_connection}")
                    raise e
        except Exception as e:
            logger.error(f"Migration crashed the skip value was {actual_skip}")
        
        logger.info(f"Inserted {inserted_lines} connection")
        actual_skip += 1500

    user_map_end = datetime.now()
    user_map_delta = user_map_end - user_map_begin
    logger.info(f"Inserted {inserted_lines} connections in {user_map_delta.total_seconds()}s")
    logger.info(f"Made {len(connection_push_times)} commit in {sum(connection_push_times)/len(connection_push_times)}s")
