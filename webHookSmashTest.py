from tapiriik.database import db
import requests
import json
import time


conn_id_list = [str(conn['ExternalID']) for conn in db.connections.find({"Service": {"$eq":"webhooksavage"}}, {"ExternalID": True})]

for conn_id in conn_id_list:
    time.sleep(0.5)
    requests.post("http://localhost:8000/sync/remote_callback/trigger_partial_sync/webhooksavage",data=json.dumps({"id":str(conn_id)}))