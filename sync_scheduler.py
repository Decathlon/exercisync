from tapiriik.database import db
from tapiriik.settings import _GLOBAL_LOGGER
from datetime import datetime
from pymongo.read_preferences import ReadPreference
from tapiriik.helper.sqs.manager import SqsManager
import time
import uuid
import json
import logging

from tapiriik.services import Service
from tapiriik.services.ratelimiting import RedisRateLimit
from tapiriik.settings import WITHDRAWN_SERVICES

logger = logging.getLogger('Sync Scheduler')
logger = _GLOBAL_LOGGER
logger.info("-----[ INITIALIZE SYNC_SCHEDULER ]-----")
sqsManager = SqsManager()
sqsManager.get_queue()

watched_rate_limited_svc = [svc for svc in Service.List() if svc.ID not in WITHDRAWN_SERVICES and svc.GlobalRateLimits != []]

while True:
    
    holding_message_sent = False
    was_on_hold = False

    while RedisRateLimit.IsOneRateLimitReached(watched_rate_limited_svc):
        was_on_hold = True
        if not holding_message_sent:
            logger.warning("ONE RATE LIMIT REACHED HOLDING THE SCHEDULER")
            holding_message_sent = True

    if was_on_hold:
        logger.info("Rate limits refreshed the scheduler is back to work !")

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
            ))

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
    sqsManager.send_messages(messages)
    #print("[Sync_scheduler]--- Scheduled %d users at %s" % (len(scheduled_ids), datetime.utcnow()))
    #if len(scheduled_ids) > 0 :
    #    logger.info("Scheduled %d users" % (len(scheduled_ids)))

    time.sleep(5)
