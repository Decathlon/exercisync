# Synchronization module for COROS
from tapiriik.settings import WEB_ROOT, COROS_CLIENT_SECRET, COROS_CLIENT_ID, COROS_API_BASE_URL
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.api import APIException, UserException, UserExceptionType, APIExcludeActivity, ServiceWarning
from tapiriik.services.interchange import UploadedActivity, ActivityType, ActivityStatistic, ActivityStatisticUnit, Lap
from tapiriik.services.fit import FITIO
from tapiriik.database import db

from datetime import datetime, timedelta
from django.core.urlresolvers import reverse
from urllib.parse import urlencode

import logging
import pytz
import requests
import time
import json

logger = logging.getLogger(__name__)

class CorosService(ServiceBase):
    ID = "coros"
    DisplayName = "Coros"
    DisplayAbbreviation = "CRS"
    AuthenticationType = ServiceAuthenticationType.OAuth
    AuthenticationNoFrame = True # Because all services does that
    # For the 2 following vars, waiting for more infos from Coros
    UserProfileURL = None
    UserActivityURL = None

    # Used only in tests | But to be verified in case of
    SupportsHR = SupportsCalories = SupportsCadence = SupportsTemp = SupportsPower = False

    # Enables extended auth ("Save these details") functionality
    RequiresExtendedAuthorizationDetails = False

    # URL to direct user to when starting authentication
    UserAuthorizationURL = None

    # List of ActivityTypes
    SupportedActivities = None

    
    # Does it?
    ReceivesActivities = False # Any at all?
    ReceivesStationaryActivities = False # Manually-entered?
    ReceivesNonGPSActivitiesWithOtherSensorData = False # Trainer-ish?
    SuppliesActivities = True

    SupportsExhaustiveListing = True


    SupportsActivityDeletion = False


    # Causes synchronizations to be skipped until...
    #  - One is triggered (via IDs returned by ExternalIDsForPartialSyncTrigger or PollPartialSyncTrigger)
    #  - One is necessitated (non-partial sync, possibility of uploading new activities, etc)
    PartialSyncRequiresTrigger = False
    PartialSyncTriggerRequiresSubscription = False
    PartialSyncTriggerStatusCode = 200
    # Timedelta for polling to happen at (or None for no polling)
    PartialSyncTriggerPollInterval = None
    # How many times to call the polling method per interval (this is for the multiple_index kwarg)
    PartialSyncTriggerPollMultiple = 1

    # How many times should we try each operation on an activity before giving up?
    # (only ever tries once per sync run - so ~1 hour interval on average)
    UploadRetryCount = 5
    DownloadRetryCount = 5

    # Global rate limiting options
    # For when there's a limit on the API key itself
    GlobalRateLimits = []


    # For mapping common->Coros
    _activityTypeMappings = {
        ActivityType.Running: 8,
        ActivityType.Cycling: 9,
        ActivityType.Swimming: 10,
        ActivityType.Climbing: 14,
        ActivityType.Hiking: 16,
        ActivityType.Walking: 16, # There is no walking in coros but as it is a very common one it will be displayed ad hiking
        ActivityType.Gym: 18,
        ActivityType.CrossCountrySkiing: 19,
        ActivityType.Snowboarding: 21,
        ActivityType.DownhillSkiing: 21,
        ActivityType.StrengthTraining: 23
        # ActivityType.Skating: "IceSkate",
        # ActivityType.Rowing: "Rowing",
        # ActivityType.Elliptical: "Elliptical",
        # ActivityType.RollerSkiing: "RollerSki",
        # ActivityType.StandUpPaddling: "StandUpPaddling",
    }

    # For mapping Coros->common
    _reverseActivityTypeMappings = {
        8: ActivityType.Running,
        9: ActivityType.Cycling,
        10: ActivityType.Swimming,
        # 13: ActivityType. # TRIATHLON and MULTISPORT
        14: ActivityType.Climbing,
        15: ActivityType.Running,
        16: ActivityType.Hiking,
        18: ActivityType.Gym,
        19: ActivityType.CrossCountrySkiing,
        20: ActivityType.Running,
        21: ActivityType.DownhillSkiing,
        23: ActivityType.StrengthTraining
    }

    SupportedActivities = list(_activityTypeMappings.keys())


    _BaseUrl = COROS_API_BASE_URL

    def WebInit(self):
        params = {
            'client_id': COROS_CLIENT_ID,
            'redirect_uri': WEB_ROOT + reverse("oauth_return", kwargs={"service": "coros"}),
            # Kinda look like the challenge string of strava (To test in conditions), but required though.
            'state': 'Potato',
            'response_type': 'code'
        }
        self.UserAuthorizationURL = self._BaseUrl+"/oauth2/authorize?" + urlencode(params)

    def RetrieveAuthorizationToken(self, req, level):
        code = req.GET.get("code")
        params = {
            "grant_type": "authorization_code", 
            "code": code, 
            "client_id": COROS_CLIENT_ID, 
            "client_secret": COROS_CLIENT_SECRET,
            "redirect_uri": WEB_ROOT + reverse("oauth_return", kwargs={"service": "coros"})
        }

        # Implement this one if there is actual rate limits for coros
        # self._rate_limit()
        response = requests.post(self._BaseUrl+"/oauth2/accesstoken", data=params)
        if response.status_code != 200:
            raise APIException("Invalid code")
        data = response.json()

        authorizationData = {
            "AccessToken": data["access_token"],
            "AccessTokenExpiresAt": time.time()+data["expires_in"],
            "RefreshToken": data["refresh_token"]
        }
        return (data["openId"], authorizationData)

    def DeleteCachedData(self, serviceRecord):
        # Nothing to delete according to the Coros API specs
        pass

    def RevokeAuthorization(self, serviceRecord):
        # As there are no disconnect endpoints from coros this functions does not seem to be useful
        # For example for Strava we call https://www.strava.com/oauth/deauthorize
        # For polar flow we make a DELETE https://www.polaraccesslink.com/v3/users/{userid}
        pass

    def _refresh_token(self, serviceRecord):
        params = {
            'client_id': COROS_CLIENT_ID,
            'client_secret': COROS_CLIENT_SECRET,
            'grant_type': "refresh_token",
            'refresh_token': serviceRecord.Authorization.get("RefreshToken")
        }
        response = requests.post(self._BaseUrl+"/oauth2/refresh-token", data=params)

        tokenRefreshmentStatus = response.json()
        if tokenRefreshmentStatus["message"] == "Token expired or invalid":
            raise APIException("[%s] - No authorization to refresh token for the user with COROS ID : %s" %(tokenRefreshmentStatus["result"]+" : "+tokenRefreshmentStatus["message"], serviceRecord.ExternalID), block=True,
                                user_exception=UserException(UserExceptionType.Authorization,
                                intervention_required=True))
        elif tokenRefreshmentStatus["message"] != "OK":
            raise APIException("%i - Corros message [%s] - Can't refresh token for an unknown reason for the user with COROS ID : %s" % (response.status_code, tokenRefreshmentStatus["result"]+" : "+tokenRefreshmentStatus["message"], serviceRecord.ExternalID))

        authorizationData = {
                "AccessToken": serviceRecord.Authorization.get("AccessToken"),
                "AccessTokenExpiresAt": time.time()+2592000, # Adding 30 days in sec as specified in the coros API doc
                "RefreshToken": serviceRecord.Authorization.get("RefreshToken")
            }

        serviceRecord.Authorization.update(authorizationData)
        db.connections.update({"_id": serviceRecord._id}, {"$set": {"Authorization": authorizationData}})


    def DownloadActivityList(self, svcRecord, exhaustive=False):
        activities = []
        exclusions = []
        activitiesData = []

        # We refresh the token before asking for data
        self._refresh_token(svcRecord)

        # Defining dates, 7 days if not exhaustive else 30
        startDate = datetime.now() - timedelta(days=(30 if exhaustive else 7))
        endDate = datetime.now()

        params = {
            'token': svcRecord.Authorization.get("AccessToken"),
            'openId': svcRecord.ExternalID,
            'startDate': startDate.strftime("%Y%m%d"),
            'endDate': endDate.strftime("%Y%m%d")
        }


        if exhaustive:
            logger.info("Retreiving 24 month COROS activities this may take couple of seconds")
        # Coros allows only 30 days by query so i make 24 of them decrementing the dates if exhaustive = True 
        for _ in range((24 if exhaustive else 1)):
            response = requests.get(self._BaseUrl+"/v2/coros/sport/list?"+ urlencode(params))
            # If there is no data in the response so there is an error. It can be everything (expired or wrong token, etc.)
            if response.json()["data"] == None:
                raise APIException("Bad request to Coros")
            
            # We don't use append 'cause it will become 2 dimensional array and that implies making double for 
            activitiesData += response.json()["data"]

            # Decrementing query dates by 30 days
            startDate -= timedelta(days=30)
            endDate -= timedelta(days=30)

            params["startDate"] = startDate.strftime("%Y%m%d")
            params["endDate"] = endDate.strftime("%Y%m%d")


        for ride in activitiesData:
            # Some king of factory design patern for instanciating an activity
            activity = UploadedActivity()
            activity.SourceServiceID = self.ID
            # Puting UTC by default but it's possible to get possibles timezones and chose it randomly with the possible_timezones method. 
            # The only problem is the possility to select a non DST timezone for an activity in a DST one.
            # self.possible_timezones(ride["startTimezone"]/4)  <== keeping this in case of really needing timzones
            activity.TZ = pytz.timezone("UTC")
            activity.StartTime = datetime.fromtimestamp(ride["startTime"])
            activity.EndTime = datetime.fromtimestamp(ride["endTime"])
            activity.ServiceData = {"ActivityID": ride["labelId"]}

            if ride["mode"] not in self._reverseActivityTypeMappings:
                if id in ride :
                    act_id = ride["id"]
                else :
                    act_id = "0"
                exclusions.append(APIExcludeActivity("Unsupported activity type %s" % ride["mode"], activity_id=act_id, user_exception=UserException(UserExceptionType.Other)))
                logger.debug("\t\tUnknown activity")
                continue

            activity.Type = self._reverseActivityTypeMappings[ride["mode"]]
            activity.Stats.Distance = ActivityStatistic(ActivityStatisticUnit.Meters, value=ride["distance"])
            activity.Stats.Speed = ActivityStatistic(ActivityStatisticUnit.SecondsPerKilometer, avg=ride["avgSpeed"] if "avgSpeed" in ride else None, max=None)
            activity.Stats.RunCadence.update(ActivityStatistic(ActivityStatisticUnit.StepsPerMinute, avg=ride["avgFrequency"]))
            activity.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilocalories, value=(ride["calorie"]/1000))
            activity.FitFileUrl = ride["fitUrl"]

            # As coros don't provide name in activity summary I temporarly put the activity name
            activity.Name = activity.Type

            activity.AdjustTZ()
            activity.CalculateUID()
            activities.append(activity)
        return activities, exclusions

    def DownloadActivity(self, svcRecord, activity):
        # We don't redownload the activities but only the fit file thanks to the fitURL
        fitFileBinary = requests.get(activity.FitFileUrl).content
        activity = FITIO.Parse(fitFileBinary, activity)

        return activity


    def UploadActivity(self, svcRecord, activity):
        raise ServiceWarning("There is no upload for COROS Skipping")


    def possible_timezones(self, tz_offset, common_only=True):
        # pick one of the timezone collections
        timezones = pytz.common_timezones if common_only else pytz.all_timezones

        # convert the float hours offset to a timedelta
        offset_days, offset_seconds = 0, int(tz_offset * 3600)
        if offset_seconds < 0:
            offset_days = -1
            offset_seconds += 24 * 3600
        desired_delta = timedelta(offset_days, offset_seconds)

        # Loop through the timezones and find any with matching offsets
        null_delta = timedelta(0, 0)
        results = []
        for tz_name in timezones:
            tz = pytz.timezone(tz_name)
            non_dst_offset = getattr(tz, '_transition_info', [[null_delta]])[-1]
            if desired_delta == non_dst_offset[0]:
                results.append(tz_name)

        return results


    def ExternalIDsForPartialSyncTrigger(self, req):
        data = json.loads(req.body.decode("UTF-8"))
        # Get user id to sync
        external_user_ids = []

        for item in data['sportDataList'] :
            if 'openId' in item:
                external_user_ids.append(item['openId'])
                logging.info("\t\t COROS USER ID : " + item['openId'])
                return external_user_ids
        return []
