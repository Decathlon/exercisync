from tapiriik.database import db
import logging
import jwt


def get_connection_by_partner_name(partner_name: str):
    """
    get connection and filter by partner name
    :return: list of connection
    """
    return [conn for conn in db.connections.find() if conn["Service"] == partner_name]


def decathlon_import(connections: list):
    """
    import connection type decathlon
    """

    for connection in connections:
        authorization_object = connection["Authorization"]
        token = authorization_object["AccessTokenDecathlonLogin"]
        headers = jwt.get_unverified_header(token)
        claim = jwt.decode(token, options={"verify_signature": False})
        logging.info(headers)
        logging.info(claim)


if __name__ == "__main__":
    users = db.users.find()
    decathlon_connections = get_connection_by_partner_name("decathlon")
    decathlon_import(decathlon_connections)
