from tapiriik.database import db
import logging
from datetime import datetime, timedelta

logging.info("Welcome to the sync_workers data cleaner")

if input("Type 'y' to confirm or anything else to cancel : ") == "y":
    delete_result = db.sync_workers.delete_many(
        {
            "$and":[
                {"User":None},
                {"Heartbeat":{"$lt": datetime.now()-timedelta(days=7)}}
            ]
        })
    
    logging.info("Deleted %s documents in the sync_workers collection" % delete_result.deleted_count)

else:
    logging.info("Delete canceled")