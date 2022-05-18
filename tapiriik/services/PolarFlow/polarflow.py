# Synchronization module for flow.polar.com
# (c) 2018 Anton Ashmarin, aashmarin@gmail.com
from tapiriik.settings import WEB_ROOT, POLAR_CLIENT_SECRET, POLAR_CLIENT_ID, POLAR_RATE_LIMITS
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.api import APIException, UserException, UserExceptionType, APIExcludeActivity
from tapiriik.services.interchange import UploadedActivity, ActivityType, ActivityStatistic, ActivityStatisticUnit
from tapiriik.services.fit import FITIO
from tapiriik.database import redis

from datetime import datetime, timedelta
from django.urls import reverse
from urllib.parse import urlencode
from requests.auth import HTTPBasicAuth
from io import StringIO

import uuid
import gzip
import logging
import lxml
import pytz
import requests
import isodate
import json

logger = logging.getLogger(__name__)

class PolarFlowService(ServiceBase):
    ID = "polarflow"
    DisplayName = "Polar Flow"
    DisplayAbbreviation = "PF"
    AuthenticationType = ServiceAuthenticationType.OAuth
    AuthenticationNoFrame = True # otherwise looks ugly in the small frame

    UserProfileURL = "https://flow.polar.com/training/profiles/{0}"
    UserActivityURL = "https://flow.polar.com/training/analysis/{1}"

    SupportsHR = SupportsCalories = SupportsCadence = SupportsTemp = SupportsPower = True

    ReceivesActivities = False # polar accesslink does not support polar data change.
    
    GlobalRateLimits = POLAR_RATE_LIMITS

    PartialSyncRequiresTrigger = True
    
    PartialSyncTriggerPollInterval = timedelta(minutes=1)

    # For mapping common->Polar Flow (text has no meaning due to upload unsupported)
    _activity_type_mappings = {
        ActivityType.Cycling: "Ride",
        ActivityType.MountainBiking: "Ride",
        ActivityType.Hiking: "Hike",
        ActivityType.Running: "Run",
        ActivityType.Walking: "Walk",
        ActivityType.Snowboarding: "Snowboard",
        ActivityType.Skating: "IceSkate",
        ActivityType.CrossCountrySkiing: "NordicSki",
        ActivityType.DownhillSkiing: "AlpineSki",
        ActivityType.Swimming: "Swim",
        ActivityType.Gym: "Workout",
        ActivityType.Rowing: "Rowing",
        ActivityType.RollerSkiing: "RollerSki",
        ActivityType.StrengthTraining: "WeightTraining",
        ActivityType.Climbing: "RockClimbing",
        ActivityType.Wheelchair: "Wheelchair",
        ActivityType.Other: "Other",
    }

    # Polar Flow -> common
    _reverse_activity_type_mappings = {
        "RUNNING": ActivityType.Running,
        "JOGGING": ActivityType.Running,
        "ROAD_RUNNING": ActivityType.Running,
        "TRACK_AND_FIELD_RUNNING": ActivityType.Running,
        "TRAIL_RUNNING": ActivityType.Running,
        "TREADMILL_RUNNING": ActivityType.Running,

        "CYCLING": ActivityType.Cycling,
        "ROAD_BIKING": ActivityType.Cycling,
        "INDOOR_CYCLING": ActivityType.Cycling,

        "MOUNTAIN_BIKING": ActivityType.MountainBiking,

        "WALKING": ActivityType.Walking,
        "HIKING": ActivityType.Hiking,
        "DOWNHILL_SKIING": ActivityType.DownhillSkiing,
        "CROSS-COUNTRY_SKIING": ActivityType.CrossCountrySkiing,
        "SNOWBOARDING": ActivityType.Snowboarding,
        "SKATING": ActivityType.Skating,

        "SWIMMING": ActivityType.Swimming,
        "OPEN_WATER_SWIMMING": ActivityType.Swimming,
        "POOL_SWIMMING": ActivityType.Swimming,

        "PARASPORTS_WHEELCHAIR": ActivityType.Wheelchair,
        "ROWING": ActivityType.Rowing,
        "INDOOR_ROWING": ActivityType.Rowing,
        "STRENGTH_TRAINING": ActivityType.StrengthTraining,

        "OTHER_INDOOR": ActivityType.Other,
        "OTHER_OUTDOOR": ActivityType.Other,

        "ROLLER_SKIING_CLASSIC": ActivityType.RollerSkiing,
        "ROLLER_SKIING_FREESTYLE": ActivityType.RollerSkiing,

        # not supported somehow
        #"": ActivityType.Elliptical,

        "FUNCTIONAL_TRAINING": ActivityType.Gym,
        "CORE": ActivityType.Gym,
        "GROUP_EXERCISE": ActivityType.Gym,
        "PILATES": ActivityType.Gym,
        "YOGA": ActivityType.Gym,

        "VERTICALSPORTS_WALLCLIMBING": ActivityType.Climbing,
    }

    SupportedActivities = list(_activity_type_mappings.keys())

    _api_endpoint = "https://www.polaraccesslink.com"


    def __init__(self):
        logging.getLogger('PolarFlow SVC')
        return None

    def _register_user(self, access_token):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer {}".format(access_token)
        }
        res = requests.post(self._api_endpoint + "/v3/users",
            json={"member-id": uuid.uuid4().hex},
            headers=headers)
        return res.status_code == 200

    def _delete_user(self, serviceRecord):
        res = requests.delete(self._api_endpoint + "/v3/users/{userid}".format(userid=serviceRecord.ExternalID),
            headers=self._api_headers(serviceRecord))

    def _api_headers(self, serviceRecord, headers={}):
        headers.update({"Authorization": "Bearer {}".format(serviceRecord.Authorization["OAuthToken"])})
        return headers

    def WebInit(self):
        params = {'response_type':'code',
                  'client_id': POLAR_CLIENT_ID,
                  'redirect_uri': WEB_ROOT + reverse("oauth_return", kwargs={"service": "polarflow"})}
        self.UserAuthorizationURL = "https://flow.polar.com/oauth2/authorization?" + urlencode(params)

    def RetrieveAuthorizationToken(self, req, level):
        code = req.GET.get("code")
        params = {"grant_type": "authorization_code",
                  "code": code,
                  "redirect_uri": WEB_ROOT + reverse("oauth_return", kwargs={"service": "polarflow"})}

        response = requests.post("https://polarremote.com/v2/oauth2/token", data=params, auth=HTTPBasicAuth(POLAR_CLIENT_ID, POLAR_CLIENT_SECRET))
        data = response.json()

        if response.status_code != 200:
            raise APIException(data["error"])

        authorizationData = {"OAuthToken": data["access_token"]}
        userId = data["x_user_id"]

        try:
            self._register_user(data["access_token"])
        except requests.exceptions.HTTPError as err:
            # Error 409 Conflict means that the user has already been registered for this client.
            # That error can be ignored
            if err.response.status_code != 409:
                raise APIException("Unable to link user", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))

        return (userId, authorizationData)

    def RevokeAuthorization(self, serviceRecord):
        self._delete_user(serviceRecord)

    def SubscribeToPartialSyncTrigger(self, serviceRecord):
        # There is no per-user webhook subscription with Polar Flow.
        serviceRecord.SetPartialSyncTriggerSubscriptionState(True)

    def UnsubscribeFromPartialSyncTrigger(self, serviceRecord):
        # As above.
        serviceRecord.SetPartialSyncTriggerSubscriptionState(False)

    def DownloadActivityList(self, serviceRecord, exhaustive=False):
        activities = []
        exclusions = []

        logging.info("\tPolar Start DownloadActivityList")

        redis_key = "polarflow:webhook:"+str(serviceRecord.ExternalID)
        activity_urls_list = redis.lrange(redis_key, 0, -1)

        for act_url in activity_urls_list:
            # We delete it from the redis list to avoid syncing a second time
            # For an strange reason we have to do :
            #       redis.lrem(key, value)
            # Even if redis, redis-py docs and the signature of the function in the container ask to do
            #       redis.lrem(key, count ,value)
            result = redis.lrem(redis_key, act_url)
            if result == 0:
                logger.warning("Cant delete the activity id from the redis key %s" % (redis_key))
            elif result > 1 :
                logger.warning("Found more than one time the activity id from the redis key %s" % (redis_key))

            response = requests.get(act_url.decode('utf-8')+"/fit", headers=self._api_headers(serviceRecord, {"Accept": "*/*"}))
            activity_id = act_url.decode('utf-8').split('/')[-1]

            if response.status_code == 404:
                # Activity not found
                exclusions.append(APIExcludeActivity("Can't find an activity for this user at this URL %s" % act_url.decode('utf-8'), activity_id=activity_id, user_exception=UserException(UserExceptionType.DownloadError)))
                logging.warning("Can't find an activity with ID %s for POLARFLOW user ID %s" % (activity_id, serviceRecord.ExternalID))
                continue
            elif response.status_code == 204:
                exclusions.append(APIExcludeActivity("FIT file does not exist for this user at this URL %s" % act_url.decode('utf-8'), activity_id=activity_id, user_exception=UserException(UserExceptionType.DownloadError)))
                logging.warning("FIT file does not exist for activity with ID %s for POLARFLOW user ID %s" % (activity_id, serviceRecord.ExternalID))
                continue
            elif response.status_code == 401 or response.status_code == 403:
                raise APIException("%i - No authorization to get activity for the user with POLARFLOW ID '%s' the user's token may have expired or been corrupted" %(response.status_code, serviceRecord.ExternalID), block=True,
                                        user_exception=UserException(UserExceptionType.Authorization,
                                        intervention_required=True))

            activity = FITIO.Parse(response.content)
            activity.SourceServiceID = self.ID
            activity.ServiceData = {"ActivityID": activity_id}

            activities.append(activity)
        
        logger.info("Successfully downloaded %i/%i activities for POLARFLOW user ID %s" % (len(activities),len(activity_urls_list),serviceRecord.ExternalID))
        return activities, exclusions

    def DownloadActivity(self, serviceRecord, activity):
        return activity

    def DeleteCachedData(self, serviceRecord):
        # Nothing to delete
        pass

    def DeleteActivity(self, serviceRecord, uploadId):
        # Not supported
        pass

    def UploadActivity(self, serviceRecord, activity):
        # Not supported
        pass

    def ExternalIDsForPartialSyncTrigger(self, req):
        data = json.loads(req.body.decode("UTF-8"))
        # Get user ids to sync
        external_user_ids = []
        if data.get("event") == "EXERCISE":
            # Pushing the callback url in redis that will be used in downloadActivityList
            redis.rpush("polarflow:webhook:%s" % data["user_id"], data["url"])
            external_user_ids.append(data["user_id"])

        logger.info("[WEBHOOK] POLAR CALLBACK for user id %s, and activity url %s" % (data["user_id"], data["url"]))
        return external_user_ids