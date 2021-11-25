# Synchronization module for SUUNTO
from tapiriik.settings import WEB_ROOT, SUUNTO_CLIENT_SECRET, SUUNTO_CLIENT_ID, SUUNTO_SUBSCRIPTION_KEY
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.interchange import UploadedActivity, ActivityType, ActivityStatisticUnit, ActivityStatistic, Lap
from tapiriik.services.api import APIException, UserException, UserExceptionType, APIExcludeActivity
from tapiriik.services.fit import FITIO
from tapiriik.database import db, redis


from datetime import datetime, timedelta
from django.core.urlresolvers import reverse
from urllib.parse import urlencode, parse_qsl

import logging
import pytz
import requests
import time
import json

logger = logging.getLogger(__name__)


class SuuntoService(ServiceBase):
    ID = "suunto"
    DisplayName = "Suunto"
    DisplayAbbreviation = "SUN"
    AuthenticationType = ServiceAuthenticationType.OAuth
    AuthenticationNoFrame = True  # Because all services does that
    PartialSyncRequiresTrigger = True

    # Does it?
    ReceivesActivities = True  # Any at all?
    ReceivesStationaryActivities = True  # Manually-entered?
    SuppliesActivities = True

    SupportsActivityDeletion = False

    _activityTypeMappings = {
        ActivityType.Other: 9,
        ActivityType.Wheelchair: 9,
        ActivityType.RollerSkiing: 56,
        ActivityType.Running: 1,
        ActivityType.Cycling: 2,
        ActivityType.MountainBiking: 10,
        ActivityType.Elliptical: 55,
        ActivityType.Swimming: 21,
        ActivityType.Gym: 20,
        ActivityType.StrengthTraining: 17,
        ActivityType.Walking: 0,
        ActivityType.CrossCountrySkiing: 12,
        ActivityType.DownhillSkiing: 13,
        ActivityType.Snowboarding: 30,
        ActivityType.Rowing: 15,
        ActivityType.Hiking: 11,
        ActivityType.Skating: 49,
        ActivityType.StandUpPaddling: 61,
        ActivityType.Climbing: 29
    }

    _reverseActivityTypeMappings = {
        0: ActivityType.Walking,
        1: ActivityType.Running,
        2: ActivityType.Cycling,
        3: ActivityType.CrossCountrySkiing,
        4: ActivityType.Other,
        5: ActivityType.Other,
        6: ActivityType.Other,
        7: ActivityType.Other,
        8: ActivityType.Other,
        9: ActivityType.Other,
        10: ActivityType.MountainBiking,
        11: ActivityType.Hiking,
        12: ActivityType.CrossCountrySkiing,
        13: ActivityType.DownhillSkiing,
        14: ActivityType.Other,
        15: ActivityType.Rowing,
        16: ActivityType.Other,
        17: ActivityType.StrengthTraining,
        18: ActivityType.Other,
        19: ActivityType.Other,
        20: ActivityType.Gym,
        21: ActivityType.Swimming,
        22: ActivityType.Running,
        23: ActivityType.StrengthTraining,
        24: ActivityType.Walking,
        25: ActivityType.Other,
        26: ActivityType.Other,
        27: ActivityType.Other,
        28: ActivityType.Swimming,
        29: ActivityType.Climbing,
        30: ActivityType.Snowboarding,
        31: ActivityType.CrossCountrySkiing,
        32: ActivityType.Gym,
        33: ActivityType.Other,
        34: ActivityType.Other,
        35: ActivityType.Other,
        36: ActivityType.Other,
        37: ActivityType.Other,
        38: ActivityType.Other,
        39: ActivityType.Other,
        40: ActivityType.Other,
        41: ActivityType.Other,
        42: ActivityType.Other,
        43: ActivityType.Other,
        44: ActivityType.Other,
        45: ActivityType.Other,
        46: ActivityType.Other,
        47: ActivityType.Other,
        48: ActivityType.Other,
        49: ActivityType.Skating,
        50: ActivityType.Other,
        51: ActivityType.Other,
        52: ActivityType.Other,
        53: ActivityType.Other,
        54: ActivityType.StrengthTraining,
        55: ActivityType.Elliptical,
        56: ActivityType.RollerSkiing,
        57: ActivityType.Rowing,
        61: ActivityType.StandUpPaddling,
        69: ActivityType.StrengthTraining,
        81: ActivityType.Gym,
        85: ActivityType.Swimming
    }

    SupportedActivities = list(_activityTypeMappings.keys())

    def WebInit(self):
        params = {
            'client_id': SUUNTO_CLIENT_ID,
            'redirect_uri': WEB_ROOT + reverse("oauth_return", kwargs={"service": "suunto"}),
            'response_type': 'code'
        }
        self.UserAuthorizationURL = "https://cloudapi-oauth.suunto.com/oauth/authorize?" + \
            urlencode(params)

    def RetrieveAuthorizationToken(self, req, level):
        code = req.GET.get("code")
        params = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": SUUNTO_CLIENT_ID,
            "client_secret": SUUNTO_CLIENT_SECRET,
            "redirect_uri": WEB_ROOT + reverse("oauth_return", kwargs={"service": "suunto"})
        }

        # TODO Implement this
        # self._rate_limit()

        response = requests.post(
            "https://cloudapi-oauth.suunto.com/oauth/token", data=params)
        if response.status_code != 200:
            raise APIException("Invalid code")
        data = response.json()

        authorizationData = {
            "AccessToken": data["access_token"],
            "AccessTokenExpiresAt": time.time()+data["expires_in"],
            "RefreshToken": data["refresh_token"]
        }
        return (data["user"], authorizationData)

    def DeleteCachedData(self, serviceRecord):
        pass

    def RevokeAuthorization(self, serviceRecord):
        resp = self._requestWithAuth(lambda session: session.get(
            "https://cloudapi-oauth.suunto.com/oauth/deauthorize?"+urlencode({'client_id': SUUNTO_CLIENT_ID})), serviceRecord)
        if resp.status_code != 200:
            raise APIException("Unable to deauthorize Suunto auth token, status " +
                str(resp.status_code) + " resp " + resp.text)

    def _requestWithAuth(self, reqLambda, serviceRecord):
        session = requests.Session()
        # TODO Implement this
        # self._rate_limit()

        # If the token expires in 60 seconds or it is expired
        if time.time() > serviceRecord.Authorization.get("AccessTokenExpiresAt", 0) - 60:
            # We ask for refreshement
            response = requests.post("https://cloudapi-oauth.suunto.com/oauth/token", data={
                'client_id': SUUNTO_CLIENT_ID,
                'client_secret': SUUNTO_CLIENT_SECRET,
                'grant_type': "refresh_token",
                'refresh_token': serviceRecord.Authorization.get("RefreshToken")
            })

            if response.status_code != 200:
                if response.status_code == 401 or response.status_code == 403:
                    raise APIException("%i - No authorization to refresh token for the user with SUUNTO ID : %s" %(response.status_code, serviceRecord.ExternalID), block=True,
                                        user_exception=UserException(UserExceptionType.Authorization,
                                        intervention_required=True))
                else: 
                    raise APIException("%i - Can't refresh token (for an undefined reason) for the user with SUUNTO ID : %s" %(response.status_code, serviceRecord.ExternalID))


            data = response.json()

            # We update the new token info in mongo
            authorizationData = {
                "AccessToken": data["access_token"],
                # Adding 30 days in sec as specified in the coros API doc
                "AccessTokenExpiresAt": time.time()+data["expires_in"],
                "RefreshToken": data["refresh_token"]
            }
            serviceRecord.Authorization.update(authorizationData)
            db.connections.update({"_id": serviceRecord._id}, {
                                  "$set": {"Authorization": authorizationData}})

        session.headers.update({
            "Authorization": "Bearer %s" % serviceRecord.Authorization["AccessToken"],
            "Ocp-Apim-Subscription-Key": SUUNTO_SUBSCRIPTION_KEY
        })
        return reqLambda(session)

    def DownloadActivityList(self, svcRecord, exhaustive=False):
        activities = []
        exclusions = []

        redis_key = "suunto:webhook:"+str(svcRecord.ExternalID)
        activity_ids_list = redis.lrange(redis_key, 0, -1)

        for act_id in activity_ids_list:
            # We delete it from the redis list to avoid syncing a second time
            # For an strange reason we have to do :
            #       redis.lrem(key, value)
            # Even if redis, redis-py docs and the signature of the function in the container ask to do
            #       redis.lrem(key, count ,value)
            result = redis.lrem(redis_key, act_id)
            if result == 0:
                logger.warning("Cant delete the activity id from the redis key %s" % (redis_key))
            elif result > 1 :
                logger.warning("Found more than one time the activity id from the redis key %s" % (redis_key))

            response = self._requestWithAuth(lambda session: session.get("https://cloudapi.suunto.com/v2/workout/exportFit/"+act_id.decode('utf-8')), svcRecord)
            if response.status_code == 404:
                raise APIException("Suunto can't find the activity : %s" % act_id, user_exception=UserException(UserExceptionType.DownloadError))
            elif response.status_code == 403:
                raise APIException("Access forbiden to Sunnto activity : %s" % act_id, user_exception=UserException(UserExceptionType.DownloadError))
            elif response.status_code == 400:
                raise APIException("Apparently a bad request has been made to suunto this must be examined", user_exception=UserException(UserExceptionType.DownloadError))

            activity = FITIO.Parse(response.content)
            activity.SourceServiceID = self.ID
            activity.ServiceData = {"ActivityID": act_id}

            activities.append(activity)
        return activities, exclusions

    def DownloadActivity(self, svcRecord, activity):
        return activity

    def UploadActivity(self, svcRecord, activity):
        # Forcing a TimerTime mostly for manual activities. If it's None Suunto will not read the Fit File
        if activity.Stats.TimerTime.asUnits(ActivityStatisticUnit.Seconds).Value == None:
            activity.Stats.TimerTime = ActivityStatistic(ActivityStatisticUnit.Seconds, value=(activity.EndTime - activity.StartTime))

        initParams = {
            "description": activity.Name,
            "comment": "",
            "notifyUser": False
        }

        # Initialisation of the upload. Basically suunto send an unique URL for upload?
        initResp = self._requestWithAuth(lambda session: session.post("https://cloudapi.suunto.com/v2/upload/", data=json.dumps(initParams), headers={'Content-Type': 'application/json'}), svcRecord)

        # Suunto ask for some headers to be set for the PUT request
        putHeaders = initResp.json()["headers"]
        putHeaders["Content-Type"] = "application/octet-stream"

        # Here we have to simulate a file buffer with the activity bytes
        # because all my attempts to pass through the "data=" parameter have failed
        # But passing activity bytes through "files=" parameter works ¯\_(ツ)_/¯
        from io import BytesIO
        file_like = BytesIO(FITIO.Dump(activity))
        files = {'act1.fit': file_like}

        # We send the activity through the link sent by suunto.
        putResp = requests.request("PUT", initResp.json()["url"], files=files, headers=putHeaders)
        if putResp.status_code != 201:
            raise APIException("Unable to upload activity " + activity.UID + " response " + putResp.text + " status " + str(putResp.status_code))

        # We must sleep because the status that bring the workout ID might not be instantaneous
        # During test 1 sec is enough so we try this
        time.sleep(1)
        response = self._requestWithAuth(lambda session: session.get("https://cloudapi.suunto.com/v2/upload/"+initResp.json()["id"]), svcRecord)
        try:
            uploadStatus = response.json()
        except ValueError:
            raise APIException("Failed parsing suunto upload response %s - %s" % (response.status_code, response.text), trigger_exhaustive=False)
        
        max_retry_count = 4


        # But suunto might be busy so we add a retry mechanism
        for retries in range(max_retry_count):
            if uploadStatus.get("workoutKey","") != "":
                # If we have the expected answer we return it
                return uploadStatus.get("workoutKey")
            
            if uploadStatus.get("status") == "ERROR":
                # If there is an error we raise en exception
                raise APIException("Error: Suunto can't process the activity " + activity.UID + " response " + response.text)

            if retries == max_retry_count - 1:
                # If the max_retry_count is reached and we have nothing, it raises an exception
                raise APIException("Initialisation OK but the data was not sent after %i tries. UID : %s Response : %s" % (max_retry_count, activity.UIDuploadStatus.text))

            # Else it makes a little break to let the time to Suunto to process and then we retry
            logger.info("SUUNTO call updload activity SLEEP 8SEC")
            time.sleep(8)
            response = self._requestWithAuth(lambda session: session.get("https://cloudapi.suunto.com/v2/upload/"+initResp.json()["id"]), svcRecord)
            try:
                uploadStatus = response.json()
            except ValueError:
                raise APIException("Failed parsing suunto upload response %s - %s" % (response.status_code, response.text), trigger_exhaustive=False)


    def SubscribeToPartialSyncTrigger(self, serviceRecord):
        # There is no per-user webhook subscription with Suunto.
        serviceRecord.SetPartialSyncTriggerSubscriptionState(True)

    def UnsubscribeFromPartialSyncTrigger(self, serviceRecord):
        # As above.
        serviceRecord.SetPartialSyncTriggerSubscriptionState(False)


    def ExternalIDsForPartialSyncTrigger(self, req):
        # Parsing the urlencoded string to python dict.
        data = dict(parse_qsl(req.body.decode('UTF-8')))

        # Checking the values even if nothing in Suunto API documentation says it is possible to have None values.
        if data.get('username') == None:
            logger.warning("Suunto has sent a notification without username")
            return []
        elif data.get('workoutid') == None:
            logger.warning("Suunto has sent a notification without workoutid for %s the trigger will not be activated" % data.get('username'))
            return []

        # It should not have error management here as it has been done in the first condition.
        redis.rpush("suunto:webhook:%s" % data['username'], data["workoutid"])
        logger.info("\tSUUNTO CALLBACK user to sync "+ data['username'])
        return [data['username']]