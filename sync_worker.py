from datetime import datetime
from tapiriik.settings import _GLOBAL_LOGGER
import os
import logging.handlers
import io
import sys

# I'm trying to track down where some missing seconds are going in the sync process
# Will grep these out of the log at some later date

import logging

def worker_message(state, now=datetime.now()):
    #print("[Sync_worker]--- PID: %d  | status: %s | at %s" % (os.getpid(), state, now.strftime("%Y-%m-%d %H:%M:%S %Z")))
    logging.info("PID: %d  | status: %s" % (os.getpid(), state))


logging.info("-----[ INITIALIZE SYNC_WORKER ]-----")
worker_message("booting")

from tapiriik.requests_lib import patch_requests_with_default_timeout, patch_requests_source_address
from tapiriik import settings
from tapiriik.database import db, close_connections
from pymongo import ReturnDocument
import sys
import subprocess
import socket

# Time spent rebooting workers < time spent wrangling Python memory management.
RecycleInterval = 2

oldCwd = os.getcwd()
WorkerVersion = subprocess.Popen(["git", "rev-parse", "HEAD"], stdout=subprocess.PIPE, cwd=os.path.dirname(os.path.abspath(__file__))).communicate()[0].strip()
os.chdir(oldCwd)

# Function use to update heartbeat (status) of sync_worker document
def sync_heartbeat(state, user=None):
	db.sync_workers.update_one({"_id": heartbeat_rec_id}, {"$set": {"Heartbeat": datetime.utcnow(), "State": state, "User": user}})

worker_message("initialized")

# Moved this flush before the sync_workers upsert for a rather convoluted reason:
# Some of the sync servers were encountering filesystem corruption, causing the FS to be remounted as read-only.
# Then, when a sync worker would start, it would insert a record in sync_workers then immediately die upon calling flush - since output is piped to a log file on the read-only FS.
# Supervisor would dutifully restart the worker again and again, causing sync_workers to quickly fill up.
# ...which is a problem, since it doesn't have indexes on Process or Host - what later lookups were based on. So, the database would be brought to a near standstill.
# Theoretically, the watchdog would clean up these records soon enough - but since it too logs to a file, it would crash removing only a few stranded records
# By flushing the logs before we insert, it should crash before filling that collection up.
# (plus, we no longer query with Process/Host in sync_hearbeat)

sys.stdout.flush()
heartbeat_rec = db.sync_workers.find_one_and_update(
	{
		"Process": os.getpid(),
		"Host": socket.gethostname()
	},
	{
		"$set": {
			"Process": os.getpid(),
			"Host": socket.gethostname(),
			"Heartbeat": datetime.utcnow(),
			"Startup":  datetime.utcnow(),
			"Version": WorkerVersion,
			"Index": settings.WORKER_INDEX,
			"State": "startup"
		}
	},
	upsert=True,
	return_document=ReturnDocument.AFTER
)
heartbeat_rec_id = heartbeat_rec["_id"]

patch_requests_with_default_timeout(timeout=60)

if isinstance(settings.HTTP_SOURCE_ADDR, list):
	settings.HTTP_SOURCE_ADDR = settings.HTTP_SOURCE_ADDR[settings.WORKER_INDEX % len(settings.HTTP_SOURCE_ADDR)]
	patch_requests_source_address((settings.HTTP_SOURCE_ADDR, 0))

# We defer including the main body of the application till here so the settings aren't captured before we've set them up.
# The better way would be to defer initializing services until they're requested, but it's 10:30 and this will work just as well.
from tapiriik.sync import Sync

sync_heartbeat("ready")

worker_message("ready")

Sync = Sync()
Sync.PerformGlobalSync(heartbeat_callback=sync_heartbeat, version=WorkerVersion)

worker_message("shutting down cleanly")
db.sync_workers.delete_one({"_id": heartbeat_rec_id})
close_connections()
worker_message("shut down")
logging.info("-----[ ENDING SYNC_WORKER ]-----")
sys.stdout.flush()
