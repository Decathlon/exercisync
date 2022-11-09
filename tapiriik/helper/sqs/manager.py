# Synchronization module for decathloncoach.com
# (c) 2019 Anael Jourdain, anael.jourdain.partner@decathlon.com
from tapiriik.settings import AWS_REGION, AWS_SQS_QUEUE_NAME, _GLOBAL_LOGGER
import json
import boto3
import logging

class SQSMessageSendingError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

logger = logging.getLogger('Helper SQS')
class SqsManager():

    _AWS_REGION = AWS_REGION
    QUEUE_NAME = AWS_SQS_QUEUE_NAME
    _resource = None
    _queue = None
    _queue_url = None
    _messages = []

    def __init__(self):
        #logger.info("-----[ INITIALIZE A NEW SQS QUEUE MANAGER ]-----")
        self._AWS_REGION = AWS_REGION
        # Create SQS client resource
        self._resource = boto3.resource('sqs', region_name=self._AWS_REGION)
        self._client = boto3.client('sqs', region_name=self._AWS_REGION)
        #logger.info("Define SQS resource in AWS zone")
        #print("[Helper SQS]--- Define SQS resource in %s AWS zone" % self._AWS_REGION)

    # Function use to get a specific queue from AWS SQS, it uses self.QUEUE_NAME as parameter
    # Queue will be available in self._queue
    def get_queue(self, queue_name=None):

        if queue_name:
            self.QUEUE_NAME = queue_name
        #print("[Helper SQS]--- Get queue %s in %s resource" % (self.QUEUE_NAME, self._AWS_REGION))
        #logger.info("Get queue SQS")
        self._queue = self._resource.get_queue_by_name(QueueName=self.QUEUE_NAME)
        self._queue_url = self._queue.url

    def send_message(self, entry):
        self._queue.send_message(Entries=entry)
        #print('---[ Sending %i messages into queue' % len(entry))
        logger.info('Sending %i messages into queue' % len(entry))

    # Function use to send a list of message.
    # Messages are send to self._queue
    def send_messages(self, entries):
        if len(entries) > 0:
            #print('[Helper SQS]--- Trying to send %i users messages into queue' % len(entries))
            logger.info('Trying to send %i users messages into queue' % len(entries))
            response = self._queue.send_messages(Entries=entries)
            #if len(response.get('SuccessFull')):
                #print('---[ Sending %i messages into queue' % len(response.get('SuccessFull')))

            response_json = json.dumps(response)
            # TODO: These lines below are not working
            if 'SuccessFul' in response_json:
                #print('[Helper SQS]--- Sending %d messages into queue' % len(response['SuccessFul']))
                logger.info('Sending %d messages into queue' % len(response['SuccessFul']))
            if 'Failed' in response_json:
                raise SQSMessageSendingError()
                #print('[Helper SQS]--- Fail sending %d messages into queue' % len(response['Failed']))
                # logger.info('Fail sending %d messages into queue' % len(response['Failed']))

        else:
            #print('[Helper SQS]--- Nothing to send')
            #logger.info('Nothing to send')
            pass

    # Function use to get a message from self._queue
    # Message will be available in self._messages
    def get_message(self, attributes_names):
        self._messages = self._queue.receive_messages(AttributeNames=attributes_names, MaxNumberOfMessages=1, WaitTimeSeconds=20)
        if self._messages:
            #print("[Helper SQS]--- Getting message from queue")
            logger.info('Getting message from queue')
        else:
            #print("[Helper SQS]--- No message found. Queue is empty !")
            #logger.info('No message found. Queue is empty !')
            pass


    # Function use to get a list of 1 message (1 by default, 10 max) from self._queue
    # Messages will be available in self._messages
    def get_messages(self, attributes_names):
        self._messages = self._queue.receive_messages(AttributeNames=attributes_names, WaitTimeSeconds=20)
        if self._messages :
            #print("[Helper SQS]--- Getting some messages from queue")
            logger.info('Getitng message from queue')
        else:
            #print("[Helper SQS]--- No message found. Queue is empty !")
            logger.info('No message found. Queue is empty !')

    # Fonction use to remove a specific message in self._queue
    def delete_message(self, message):
        message.delete()
        #print("[Helper SQS]--- Deleting one message")
        logger.info('Deleting one message')

    # Function use to remove a specific message by receipt_handle, using default queue
    def delete_message_by_receipt_handle(self, receipt_handle, queue_url=None):
        self._client.delete_message(QueueUrl=(queue_url if queue_url is not None else self._queue.url), ReceiptHandle=receipt_handle)
        #print("[Helper SQS]--- Deleting one message by receipt handle (%s)" % receipt_handle)
        #logger.info("Deleting one message by receipt handle (%s)" % receipt_handle)

    # Function use to remove all message in queue
    # current_queue determine if we remove ALL message in queue or just current sample of message
    def clear_queue(self, current_queue=True, attributes_names=None):

        #print('[Helper SQS]--- Cleaning the queue')
        logger.info('Cleaning the queue')
        if attributes_names is None:
            attributes_names = ['all']

        while self._messages:
            for message in self._messages:
                self.delete_message(message)

            if current_queue is False:
                self.get_message(attributes_names)

    def process(self, entries, add=False, delete_message=True):
        self.get_queue()
        if add:
            self.send_messages(entries)
        self.get_message(['all'])

        while self._messages:
            for message in self._messages:
                # Print out the body and author (if set)
                print('Message ID : {0} / {1}'.format(message.message_id ,message.body))

                if delete_message is True:
                    self.delete_message(message)
            self.get_message(['all'])

        if delete_message is not True:
            self.clear_queue()
