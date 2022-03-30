from tapiriik.settings import WEB_ROOT, GARMINHEALTH_KEY, GARMINHEALTH_SECRET
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.service_record import ServiceRecord
from tapiriik.database import cachedb, db
from tapiriik.services.interchange import UploadedActivity, ActivityType, ActivityStatistic, ActivityStatistics, ActivityStatisticUnit, Waypoint, WaypointType, Location, Lap
from tapiriik.services.api import APIException, UserException, UserExceptionType
from tapiriik.services.fit import FITIO
from fitparse.utils import FitEOFError
from django.urls import reverse
from datetime import date, datetime, timezone, timedelta
from urllib.parse import urlencode
from tapiriik.database import redis
from requests_oauthlib import OAuth1Session

import requests
import logging
import pytz
import json
from hashlib import sha1
import hmac
import base64
import string
import urllib.parse
from six.moves.urllib.parse import parse_qs
import random

logger = logging.getLogger(__name__)

class GarminHealthService(ServiceBase):

    API_URL = "https://healthapi.garmin.com/wellness-api/rest"
    # POST # URI to get a request token
    REQUEST_TOKEN_URL = "https://connectapi.garmin.com/oauth-service/oauth/request_token"
    # POST # URI to get user token/token_secret
    ACCESS_TOKEN_URL = "https://connectapi.garmin.com/oauth-service/oauth/access_token"
    # GET # URI to get user auth and verifier token
    OAUTH_TOKEN_URL ="http://connect.garmin.com/oauthConfirm"
    # GET # URI to get user ID
    URI_USER_ID = "https://healthapi.garmin.com/wellness-api/rest/user/id"
    # GET # URI to get user activities summary
    URI_ACTIVITIES_SUMMARY = "https://healthapi.garmin.com/wellness-api/rest/activities"
    URI_ACTIVITIES_DETAIL = "https://healthapi.garmin.com/wellness-api/rest/activityDetails"

    ID = "garminhealth"
    DisplayName = "Garmin Health"
    DisplayAbbreviation = "GH"

    AuthenticationType = ServiceAuthenticationType.OAuth
    AuthenticationNoFrame = True  # They don't prevent the iframe, it just looks really ugly.
    PartialSyncRequiresTrigger = False
    LastUpload = None

    SupportsHR = SupportsCadence = SupportsTemp = SupportsPower = False

    SupportsActivityDeletion = False

    ReceivesActivities = False

    _activityTypeMappings = {
        ActivityType.Running: "RUNNING",
        ActivityType.Cycling: "CYCLING",
        ActivityType.MountainBiking: "MOUNTAIN_BIKING",
        ActivityType.Walking: "WALKING",
        ActivityType.Hiking: "HIKING",
        ActivityType.DownhillSkiing: "DownhillSkiing",
        ActivityType.CrossCountrySkiing: "CROSS_COUNTRY_SKIING",
        ActivityType.Snowboarding: "RESORT_SKIING_SNOWBOARDING",
        ActivityType.Skating: "SKATE_SKIING",
        ActivityType.Swimming: "SWIMMING",
        #ActivityType.Wheelchair: "Wheelchair",
        ActivityType.Rowing: "ROWING",
        ActivityType.Elliptical: "ELLIPTICAL",
        ActivityType.Gym: "FITNESS_EQUIPMENT",
        ActivityType.Climbing: "MOUNTAINEERING",
        #ActivityType.RollerSkiing: "RollerSkiing",
        ActivityType.StrengthTraining: "STRENGTH_TRAINING",
        ActivityType.StandUpPaddling: "STAND_UP_PADDLEBOARDING",
        ActivityType.Yoga: "YOGA",
        ActivityType.Other: "UNCATEGORIZED"
    }

    _reverseActivityTypeMappings = {  # Removes ambiguities when mapping back to their activity types
        "ALL": ActivityType.Other,
        "UNCATEGORIZED": ActivityType.Other,
        #"SEDENTARY"
        "RUNNING": ActivityType.Running,
        "STREET_RUNNING": ActivityType.Running,
        "TRACK_RUNNING": ActivityType.Running,
        "TRAIL_RUNNING": ActivityType.Running,
        "TREADMILL_RUNNING": ActivityType.Running,
        "CYCLING": ActivityType.Cycling,
        "CYCLOCROSS": ActivityType.Cycling,
        "DOWNHILL_BIKING": ActivityType.MountainBiking,
        "INDOOR_CYCLING": ActivityType.Cycling,
        "MOUNTAIN_BIKING": ActivityType.MountainBiking,
        "RECUMBENT_CYCLING": ActivityType.Cycling,
        "ROAD_BIKING": ActivityType.Cycling,
        "TRACK_CYCLING": ActivityType.Cycling,
        "FITNESS_EQUIPMENT": ActivityType.Gym,
        "ELLIPTICAL": ActivityType.Elliptical,
        "INDOOR_CARDIO": ActivityType.Gym,
        #"INDOOR_ROWING"
        "STAIR_CLIMBING": ActivityType.Climbing,
        "STRENGTH_TRAINING": ActivityType.StrengthTraining,
        "HIKING": ActivityType.Hiking,
        "SWIMMING": ActivityType.Swimming,
        "LAP_SWIMMING": ActivityType.Swimming,
        "OPEN_WATER_SWIMMING": ActivityType.Swimming,
        "WALKING": ActivityType.Walking,
        "CASUAL_WALKING": ActivityType.Walking,
        "SPEED_WALKING": ActivityType.Walking,
        "TRANSITION": ActivityType.Other,
        "SWIMTOBIKETRANSITION": ActivityType.Other,
        "BIKETORUNTRANSITION": ActivityType.Other,
        "RUNTOBIKETRANSITION": ActivityType.Other,
        "OTHER": ActivityType.Other,
        #"BACKCOUNTRY_SKIING_SNOWBOARDING"
        "CROSS_COUNTRY_SKIING": ActivityType.CrossCountrySkiing,
        #"FLYING"
        #"GOLF"
        #"HORSEBACK_RIDING"
        #"INLINE_SKATING"
        "MOUNTAINEERING": ActivityType.Climbing,
        "PADDLING": ActivityType.StandUpPaddling,
        "RESORT_SKIING_SNOWBOARDING": ActivityType.Snowboarding,
        "ROWING": ActivityType.Rowing,
        #"SAILING"
        "SKATE_SKIING": ActivityType.Skating,
        "SKATING": ActivityType.Skating,
        "SNOW_SHOE": ActivityType.Walking,
        "STAND_UP_PADDLEBOARDING": ActivityType.StandUpPaddling,
        #"WHITEWATER_RAFTING_KAYAKING"
        #"WIND_KITE_SURFING"
        "YOGA": ActivityType.Yoga
    }

    SupportedActivities = list(_activityTypeMappings.keys())

    def UserUploadedActivityURL(self, uploadId):
        return "https://connect.garmin.com/modern/activity/" + str(uploadId)

    # Use this function to get Autorization URL
    def WebInit(self):
        self.UserAuthorizationURL = reverse("oauth_redirect", kwargs={"service": "garminhealth"})


    # Helper to initialize the Oauth v1 Session
    def _oauthSession(self, connection=None, **params):
        if connection:
            params["resource_owner_key"] = connection.Authorization["AccessToken"]
            params["resource_owner_secret"] = connection.Authorization["AccessTokenSecret"]
        return OAuth1Session(GARMINHEALTH_KEY, client_secret=GARMINHEALTH_SECRET, **params)

    def GenerateUserAuthorizationURL(self, session, level=None):
        # Generation of an Oauth v1 session (This should be empty at this point)
        oauthSession = self._oauthSession(callback_uri=WEB_ROOT + reverse("oauth_return", kwargs={"service": "garminhealth"}))
        # Fetching the tokens from the session
        tokens = oauthSession.fetch_request_token(self.REQUEST_TOKEN_URL)
        # The secret is saved in redis else it will be lost when we exit the function.
        redis_token_key = "garminhealth:oauth:%s" % tokens["oauth_token"]
        redis.setex(redis_token_key, tokens["oauth_token_secret"], timedelta(hours=24))
        return oauthSession.authorization_url(self.OAUTH_TOKEN_URL)


    # This function is used to set token info for a user, get expiration date, refresh and access token
    def RetrieveAuthorizationToken(self, req, level):
        # Retrieving the previously saved secret
        redis_token_key = "garminhealth:oauth:%s" % req.GET.get("oauth_token")
        secret = redis.get(redis_token_key)
        redis.delete(redis_token_key)

        # Now getting the access token
        oauthSession = self._oauthSession(resource_owner_secret=secret)
        oauthSession.parse_authorization_response(req.get_full_path())
        tokens = oauthSession.fetch_access_token(self.ACCESS_TOKEN_URL)

        # We are now ready to send auth request to the service so we get the user ID to save it in mongo
        userInfo = oauthSession.get(self.URI_USER_ID)
        OAuth_data = {
            "OAuthToken": req.GET.get("oauth_token"),
            "AccessToken": tokens["oauth_token"],
            "AccessTokenSecret": tokens["oauth_token_secret"],
            "AccessTokenRequestedAt": datetime.now(timezone.utc)
        }
        return (userInfo.json()["userId"], OAuth_data)


    # This function is used to revoke access token
    def RevokeAuthorization(self, serviceRecord):
        # Garmin has no revoke Auth endpoint. 
        # Their doc says that users have to disconnect the app directly in garmin connect.
        # https://connect.garmin.com/modern/account
        logging.info("Revoke Garmin Authorization")
        pass
  

    def DownloadActivityList(self, svcRecord, exhaustive=False):
        oauthSession = self._oauthSession(svcRecord)

        activities = []
        exclusions = []

        redis_key = "garminhealth:webhook:"+str(svcRecord.ExternalID)
        activity_file_urls_list = redis.lrange(redis_key, 0, -1)
        pre_download_counter = post_download_counter = 0

        for activity_file_url_and_name_and_id in activity_file_urls_list:
            # We delete it from the redis list to avoid syncing a second time
            # For an strange reason we have to do :
            #       redis.lrem(key, value)
            # Even if redis, redis-py docs and the signature of the function in the container ask to do
            #       redis.lrem(key, count ,value)
            result = redis.lrem(redis_key, activity_file_url_and_name_and_id)
            if result == 0:
                logger.warning("Cant delete the activity id from the redis key %s" % (redis_key))
            elif result > 1 :
                logger.warning("Found more than one time the activity id from the redis key %s" % (redis_key))
            
            # Spliting the URL from the Activity Name
            decoded_activity_file_url_and_name_and_id = activity_file_url_and_name_and_id.decode('UTF-8')
            logger.info("Garmin activity download parameters: %s" % decoded_activity_file_url_and_name_and_id)

            activity_download_parameters = decoded_activity_file_url_and_name_and_id.split("::")

            if len(activity_download_parameters) == 3:
                activity_file_url = activity_download_parameters[0]
                activity_file_name = activity_download_parameters[1]
                activity_id = activity_download_parameters[2]

                # Downlaoding the activity fit file
                resp = oauthSession.get(activity_file_url)
                if resp.status_code != 204 and resp.status_code != 200:
                    if resp.status_code == 401 or resp.status_code == 403:
                        raise APIException("%i - No authorization to refresh token for the user with GARMIN ID : %s" %(resp.status_code, svcRecord.ExternalID), 
                                            block=True,
                                            user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
                    else:
                        logger.warning("\tAn error occured while downloading Garmin Health activity, status code %s, content %s" % (
                            (str(resp.status_code), resp.content)))
                else:
                    pre_download_counter += 1
                    try:
                        activity = FITIO.Parse(resp.content)
                        activity.SourceServiceID = self.ID
                    except FitEOFError as e:
                        logger.warning("Can't parse the file from %s. Skipping this activity." % activity_file_url)
                        continue
                    # As the name can be None in the webhook we could have empty string as a fallback to avoid redis crash.
                    # In this case it's better to set the activity.Name to None as the FITIO.Parse have an activity name guess behaviour.
                    activity.Name = activity_file_name if activity_file_name != "" else None

                    activity.CalculateUID()
                    post_download_counter += 1
                    activities.append(activity)
                    logger.info("Garmin Activity with ID %s and Start date %s for user %s has been downloaded " % (activity_id, activity.StartTime.strftime("%Y-%m-%d %H:%M:%S") if activity.StartTime is not None else "UNKNOWN",svcRecord.ExternalID))

            else:
                logger.warning("[GARMIN error] User with GARMIN ID %s, has a wrong value. Value ignored : %s" % (svcRecord.ExternalID, decoded_activity_file_url_and_name_and_id))

        logger.info("\t\t total Garmin activities downloaded : %i" % pre_download_counter)
        logger.info("\t\t\t Listed activities by redis : %i" % len(activity_file_urls_list))
        logger.info("\t\t\t Number of activities passed though download : %i" % post_download_counter)
        return activities, exclusions

    def DownloadActivity(self, svcRecord, activity):
        return activity

    # Garmin Health is on read only access, we can't upload activities
    def UploadActivity(self, svcRecord, activity):
        logging.info("UPLOAD To Garming Health is not possible")
        pass

    def DeleteCachedData(self, serviceRecord):
        cachedb.garminhealth_cache.remove({"Owner": serviceRecord.ExternalID})
        cachedb.garminhealth_activity_cache.remove({"Owner": serviceRecord.ExternalID})


    def ExternalIDsForPartialSyncTrigger(self, req):
        # Even if no occurence of this error has happened in "normal conditions" for the moment.
        # It's still better to handle possible errors to avoid sending 500 to Garmin
        #       and possibly losse a lot of good activities.
        try:
            data = json.loads(req.body.decode("UTF-8"))
        except json.JSONDecodeError:
            logging.warning("No JSON detected in garmin webhook. Here is what the body looks like : \"%s\"" % req.body.decode("UTF-8"))
            data = {}
        logger.info("GARMIN CALLBACK POKE")
        # Get user ids to sync
        external_user_ids = []
        if data.get('activityFiles') != None:
            for activity in data['activityFiles']:
                # Pushing the callback url in redis that will be used in downloadActivityList
                #       The "activityName" sent by Garmin could be None and it is very bad. 
                #       So if the case happen, we just set an empty string ("") in the redis key to avoid crash.
                try:
                    redis.rpush("garminhealth:webhook:%s" % activity['userId'], activity["callbackURL"]+"::"+activity.get("activityName","")+"::"+str(activity["activityId"]))
                    external_user_ids.append(activity['userId'])
                    logging.info("\tGARMIN CALLBACK user to sync "+ activity['userId'])
                except KeyError as e:
                    logging.warning("Garmin sent through the webhook an activityFile with no %s defined in the metadata" % e)

        return external_user_ids



