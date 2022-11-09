from tapiriik.database import db
from tapiriik.settings import _GLOBAL_LOGGER
from datetime import datetime
from pymongo.read_preferences import ReadPreference
from tapiriik.helper.sqs.manager import SqsManager, SQSMessageSendingError
import time
import uuid
import json
import logging


logger = logging.getLogger('Sync Scheduler')
logger = _GLOBAL_LOGGER
logger.info("-----[ INITIALIZE SYNC_SCHEDULER ]-----")
sqsManager = SqsManager()
sqsManager.get_queue()

while True:
    generation = str(uuid.uuid4())
    queueing_at = datetime.utcnow()
    users = list(db.users.with_options(read_preference=ReadPreference.PRIMARY).find(
                {
                    "NextSynchronization": {"$lte": datetime.utcnow()},
                    "QueuedAt": {"$exists": False}
                },
                {
                    "_id": True,
                    "SynchronizationHostRestriction": True
                }
            ).limit(10))

    scheduled_ids = [x["_id"] for x in users]
    #print("[Sync_scheduler]--- Found %d users at %s" % (len(scheduled_ids), datetime.utcnow()))
    if len(scheduled_ids) > 0 :
        logger.info("Found %d users" % (len(scheduled_ids)))

    db.users.update_many({"_id": {"$in": scheduled_ids}}, {"$set": {"QueuedAt": queueing_at, "QueuedGeneration": generation}, "$unset": {"NextSynchronization": True}}, upsert=False)
    #print("[Sync_scheduler]--- Marked %d users as queued at %s" % (len(scheduled_ids), datetime.utcnow()))
    if len(scheduled_ids) > 0 :
        logger.info("Marked %d users as queued" % (len(scheduled_ids)))

    now = datetime.now()
    messages = []
    for user in users:
        # build user message body
        # user_generation is used to set ID message, ID message is an identifier for a message in a batch, and used to communicate the result
        user_generation = str(uuid.uuid4()) + '-' + str(user["_id"])
        body = {
            'user_id': str(user["_id"]),
            'datetime': now.strftime("%Y-%m-%d %H:%M:%S %Z"),
            'message_generator': 'sync_scheduler',
            'generation': generation
        }

        # If not empty, add synchronization host restriction
        if "SynchronizationHostRestriction" in user and user["SynchronizationHostRestriction"]:
            body['routing_key'] = {
                'StringValue': user["SynchronizationHostRestriction"],
                'DataType': 'String'
            }
        # transform body into JSON format
        parsed_body = json.dumps(body)

        user_message = {
            'Id': user_generation,
            'MessageBody': parsed_body
        }

        # append user message into list (it will be send as a batch into queue)
        messages.append(user_message)

    # publish all message
    try:
        sqsManager.send_messages(messages)
    except SQSMessageSendingError:
        logger.error(f"Failed to send SQS message for generation {generation}")

    except Exception as e:
        raise e

    else:
        for user in users:
            logger.info(f"[SYNC SCHEDULE] Synchronization planned for hub user id {user['_id']}")
    #print("[Sync_scheduler]--- Scheduled %d users at %s" % (len(scheduled_ids), datetime.utcnow()))
    #if len(scheduled_ids) > 0 :
    #    logger.info("Scheduled %d users" % (len(scheduled_ids)))

    time.sleep(2)
