from tapiriik.database import db, close_connections
from tapiriik.sync import SyncStep
import os
import signal
import socket
from datetime import timedelta, datetime
import logging

logging.info("Sync watchdog run at %s" % datetime.now())

host = socket.gethostname()

for worker in db.sync_workers.find({"Host": host}):
    # Does the process still exist?
    alive = True
    try:
        os.kill(worker["Process"], 0)
    except os.error:
        logging.info("%s is no longer alive" % worker)
        alive = False

    # Has it been stalled for too long?
    if worker["State"] == SyncStep.List:
        timeout = timedelta(minutes=45)  # This can take a loooooooong time
    else:
        timeout = timedelta(minutes=10)  # But everything else shouldn't

    if alive and worker["Heartbeat"] < datetime.utcnow() - timeout:
        logging.warning("%s timed out" % worker)
        os.kill(worker["Process"], signal.SIGKILL)
        alive = False

    # Clear it from the database if it's not alive.
    if not alive:
        db.sync_workers.delete_one({"_id": worker["_id"]})
        # Unlock users attached to it.
        db.users.update_many({"SynchronizationWorker": worker["Process"], "SynchronizationHost": host}, {"$unset":{"SynchronizationWorker": True}})

db.sync_watchdogs.update_one({"Host": host}, {"$set":{"Host": host, "Timestamp": datetime.utcnow()}}, upsert=True)

close_connections()
