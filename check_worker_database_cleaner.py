from tapiriik.database import db
import logging
from datetime import datetime, timedelta


total_document_count = db.sync_workers.count_documents({})
document_with_user_count = db.sync_workers.count_documents({"User":{"$ne":None}})
recent_document_without_user_count = db.sync_workers.count_documents(
    {
        "$and":[
            {"User":None},
            {"Heartbeat":{"$gt": datetime.now()-timedelta(days=7)}}
        ]
    })
document_to_delete_count = db.sync_workers.count_documents(
    {
        "$and":[
            {"User":None},
            {"Heartbeat":{"$lt": datetime.now()-timedelta(days=7)}}
        ]
    })


logging.info("There is a total of %s document in the sync_workers collection" % total_document_count)
logging.info("\t%s documents have the user field defined and will not be deleted" % document_with_user_count)
logging.info("\t%s document are too recent to be deleted" % recent_document_without_user_count)
logging.info("\t%s DOCUMENTS WILL BE DELETED BY THE worker_database_cleaner SCRIPT" % document_to_delete_count)
logging.info("\t%s + %s + %s = %s" % (document_with_user_count, recent_document_without_user_count, document_to_delete_count, (document_with_user_count + recent_document_without_user_count + document_to_delete_count)))
logging.info("After the delete, the number of document impacted might change a little bit as the DB continues to work")