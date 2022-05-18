from tapiriik.settings import WEB_ROOT, FITBIT_CLIENT_ID, FITBIT_CLIENT_SECRET, FITBIT_DURATION, FITBIT_WEBHOOK_VERIFICATION_CODE, FITBIT_SUBSCRIBER_ID
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.service_record import ServiceRecord
from tapiriik.database import cachedb, db
from tapiriik.services.interchange import UploadedActivity, ActivityType, ActivityStatistic, ActivityStatistics, ActivityStatisticUnit, Waypoint, WaypointType, Location, Lap
from tapiriik.services.api import APIException, UserException, UserExceptionType, APIExcludeActivity, ServiceException
from tapiriik.services.fit import FITIO
from tapiriik.services.tcx import TCXIO
from tapiriik.services.ratelimiting import RateLimit, RateLimitExceededException
from lxml import etree
import copy
from django.urls import reverse
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
import calendar
import requests
import os
import logging
import pytz
import re
import time
import json
import pprint
import base64
from requests_oauthlib import OAuth2Session
from dateutil.parser import parse
from tapiriik.database import redis

logger = logging.getLogger(__name__)

class FitbitService(ServiceBase):
    FITBIT_AUTH_URI = "https://www.fitbit.com/oauth2/authorize"
    FITBIT_REFRESH_URI = "https://api.fitbit.com/oauth2/token"
    FITBIT_REVOKE_URI = "https://api.fitbit.com/oauth2/revoke"


    header_line = FITBIT_CLIENT_ID + ":" + FITBIT_CLIENT_SECRET
    header_byte = header_line.encode("utf-8")
    header_encode = base64.b64encode(header_byte)
    header_encode = header_encode.decode("utf-8")

    ID = "fitbit"
    DisplayName = "Fitbit"
    DisplayAbbreviation = "FTB"

    AuthenticationType = ServiceAuthenticationType.OAuth
    AuthenticationNoFrame = True  # They don't prevent the iframe, it just looks really ugly.
    PartialSyncRequiresTrigger = True
    PartialSyncTriggerRequiresSubscription = True
    PartialSyncTriggerStatusCode = 204
    LastUpload = None

    SupportsHR = SupportsCadence = SupportsTemp = SupportsPower = False

    SupportsActivityDeletion = False


    # source for the mapping : GET https://api.fitbit.com/1/activities.json and https://dev.fitbit.com/build/reference/web-api/activity/#activity-types
    _activityTypeMappings = {
        ActivityType.Running: 90009,
        ActivityType.Cycling: 90001,
        ActivityType.MountainBiking: 1009,
        ActivityType.Walking: 90013,
        ActivityType.Hiking: 90012,
        ActivityType.DownhillSkiing: 19160,
        ActivityType.CrossCountrySkiing: 90015,
        # ActivityType.Snowboarding: "Snowboarding", # No snowboarding in fitbit
        ActivityType.Skating: 19030,
        ActivityType.Snowshoeing: 19190,
        ActivityType.Swimming: 90024,
        # ActivityType.Wheelchair: "Wheelchair", # No wheelchair ...
        ActivityType.Rowing: 90014,
        ActivityType.Kayaking: 18100,
        # ActivityType.KiteSurfing: "Kite surfing", # No snowboarding in fitbit
        # ActivityType.WindSurfing: "Wind surfing", # No snowboarding in fitbit
        ActivityType.Surfing: 18220,
        ActivityType.InlineSkating: 15591,
        ActivityType.Elliptical: 90017,
        ActivityType.Gym: 15300,
        ActivityType.Climbing: 15535,
        ActivityType.RollerSkiing: 19160, # Same as DownhillSkiing
        ActivityType.StrengthTraining: 2130, # Weight lifting
        # ActivityType.StandUpPaddling: "Stand up paddling", # No StandUpPaddling in fitbit
        ActivityType.Yoga: 52001,
        # ActivityType.Other: "Training", # No "Other" sport type
    }

    _reverseActivityTypeMappings = {
        90001: ActivityType.Cycling,
        20047: ActivityType.Elliptical,
        0: ActivityType.Gym,
        90004: ActivityType.Gym, # 		0	Aerobic step	Dancing
        3015: ActivityType.Gym, # 		0	Aerobic, general	Dancing
        90005: ActivityType.Gym, # 		0	Aerobics	Dancing
        3050: ActivityType.Gym, # 		0	Anishinaabe Jingle Dancing or other traditional American Indian dancing	Dancing
        3010: ActivityType.Gym, # 		0	Ballet	Dancing
        3040: ActivityType.Gym, # 		0	Ballroom, slow (e.g. waltz, foxtrot, slow dancing), samba, tango, 19th C, mambo, chacha	Dancing
        3031: ActivityType.Gym, # 		0	Dancing	Dancing
        3025: ActivityType.Gym, # 		0	General, Greek, Middle Eastern, hula, flamenco, belly, swing	Dancing
        56001: ActivityType.Gym, # 		0	Zumba	Dancing
        1: ActivityType.Other,
        4001: ActivityType.Other, # 		1	Fishing	Fishing and Hunting
        4030: ActivityType.Other, # 		1	Fishing from boat, sitting	Fishing and Hunting
        4020: ActivityType.Other, # 		1	Fishing from river bank and walking	Fishing and Hunting
        4040: ActivityType.Other, # 		1	Fishing from river bank, standing	Fishing and Hunting
        4050: ActivityType.Other, # 		1	Fishing in stream, in waders	Fishing and Hunting
        4060: ActivityType.Other, # 		1	Fishing, ice, sitting	Fishing and Hunting
        4100: ActivityType.Other, # 		1	Hunting	Fishing and Hunting
        4070: ActivityType.Other, # 		1	Hunting, bow and arrow or crossbow	Fishing and Hunting
        4080: ActivityType.Other, # 		1	Hunting, deer, elk, large game	Fishing and Hunting
        4090: ActivityType.Other, # 		1	Hunting, duck, wading	Fishing and Hunting
        4110: ActivityType.Other, # 		1	Hunting, pheasants or grouse	Fishing and Hunting
        4120: ActivityType.Other, # 		1	Hunting, rabbit, squirrel, prairie chick, raccoon, small game	Fishing and Hunting
        4130: ActivityType.Other, # 		1	Shooting	Fishing and Hunting
        2: ActivityType.Walking, # Walking
        5175: ActivityType.Walking, #	2	Walk/run - playing with child(ren) - moderate, only active periods	Home activities
        5180: ActivityType.Walking, #	2	Walk/run - playing with child(ren) - vigorous, only active periods	Home activities
        5192: ActivityType.Walking, #	2	Walk/run, playing with animals, light, only active periods	Home activities
        5193: ActivityType.Walking, #	2	Walk/run, playing with animals, moderate, only active periods	Home activities
        5194: ActivityType.Walking, #	2	Walk/run, playing with animals, vigorous, only active periods	Home activities
        8: ActivityType.Walking, # Walking
        90009: ActivityType.Running,
        90024: ActivityType.Swimming,
        90008: ActivityType.Walking, #	8	Walking while carrying things	Occupations
        32: ActivityType.Gym, # Gym
        53001: ActivityType.Gym, #	32	Pilates	Pilates
        53003: ActivityType.Gym, #	32	Pilates, Advanced	Pilates
        53002: ActivityType.Gym, #	32	Pilates, Intermediate	Pilates
        20: ActivityType.Other, #
        15010: ActivityType.Other, #	20	Archery	Sports and Workouts
        15020: ActivityType.Other, #	20	Badminton	Sports and Workouts
        15030: ActivityType.Other, #	20	Badminton, social singles and doubles, general	Sports and Workouts
        15620: ActivityType.Other, #	20	Baseball	Sports and Workouts
        15040: ActivityType.Other, #	20	Basketball	Sports and Workouts
        15050: ActivityType.Other, #	20	Basketball, non-game, general	Sports and Workouts
        15060: ActivityType.Other, #	20	Basketball, officiating	Sports and Workouts
        15070: ActivityType.Other, #	20	Basketball, shooting baskets	Sports and Workouts
        15075: ActivityType.Other, #	20	Basketball, wheelchair	Sports and Workouts
        15080: ActivityType.Other, #	20	Billiards	Sports and Workouts
        55003: ActivityType.Other, #	20	Bootcamp	Sports and Workouts
        15090: ActivityType.Other, #	20	Bowling	Sports and Workouts
        15100: ActivityType.Other, #	20	Boxing	Sports and Workouts
        15110: ActivityType.Other, #	20	Boxing, punching bag	Sports and Workouts
        15120: ActivityType.Other, #	20	Boxing, sparring	Sports and Workouts
        15130: ActivityType.Other, #	20	Broomball	Sports and Workouts
        15140: ActivityType.Other, #	20	Coaching: football, soccer, basketball, baseball, swimming, etc.	Sports and Workouts
        15150: ActivityType.Other, #	20	Cricket	Sports and Workouts
        15160: ActivityType.Other, #	20	Croquet	Sports and Workouts
        15170: ActivityType.Other, #	20	Curling	Sports and Workouts
        15180: ActivityType.Other, #	20	Darts, wail or lawn	Sports and Workouts
        15190: ActivityType.Other, #	20	Drag racing, pushing or driving a car	Sports and Workouts
        15200: ActivityType.Other, #	20	Fencing	Sports and Workouts
        15350: ActivityType.Other, #	20	Field Hockey	Sports and Workouts
        15210: ActivityType.Other, #	20	Football	Sports and Workouts
        15235: ActivityType.Other, #	20	Football or baseball, playing catch	Sports and Workouts
        15230: ActivityType.Other, #	20	Football, touch, flag, general	Sports and Workouts
        15240: ActivityType.Other, #	20	Frisbee playing, general	Sports and Workouts
        15255: ActivityType.Other, #	20	Golf	Sports and Workouts
        15270: ActivityType.Other, #	20	Golf, miniature, driving range	Sports and Workouts
        15290: ActivityType.Other, #	20	Golf, using power cart	Sports and Workouts
        15265: ActivityType.Other, #	20	Golf, walking and carrying clubs	Sports and Workouts
        15285: ActivityType.Other, #	20	Golf, walking and pulling clubs	Sports and Workouts
        15300: ActivityType.Gym, #	20	Gymnastics	Sports and Workouts
        15310: ActivityType.Other, #	20	Hacky sack	Sports and Workouts
        15320: ActivityType.Other, #	20	Handball	Sports and Workouts
        15330: ActivityType.Other, #	20	Handball, team	Sports and Workouts
        15340: ActivityType.Other, #	20	Hang gliding	Sports and Workouts
        15360: ActivityType.Other, #	20	Hockey	Sports and Workouts
        15370: ActivityType.Other, #	20	Horseback riding	Sports and Workouts
        11390: ActivityType.Other, #	20	Horseback riding - galloping	Sports and Workouts
        11400: ActivityType.Other, #	20	Horseback riding - trotting	Sports and Workouts
        11410: ActivityType.Other, #	20	Horseback riding - walking	Sports and Workouts
        15380: ActivityType.Other, #	20	Horseback riding, saddling horse, grooming horse	Sports and Workouts
        15410: ActivityType.Other, #	20	Horseshoe pitching	Sports and Workouts
        15420: ActivityType.Other, #	20	Jai alai	Sports and Workouts
        15440: ActivityType.Other, #	20	Juggling	Sports and Workouts
        15551: ActivityType.Other, #	20	Jumping rope	Sports and Workouts
        15450: ActivityType.Other, #	20	Kickball	Sports and Workouts
        55002: ActivityType.Other, #	20	Kickboxing	Sports and Workouts
        15460: ActivityType.Other, #	20	Lacrosse	Sports and Workouts
        15430: ActivityType.Other, #	20	Martial Arts	Sports and Workouts
        15470: ActivityType.Other, #	20	Motocross	Sports and Workouts
        15480: ActivityType.Walking, #	20	Orienteering	Sports and Workouts
        15500: ActivityType.Other, #	20	Paddleball, casual, general	Sports and Workouts
        15490: ActivityType.Other, #	20	Paddleball, competitive	Sports and Workouts
        15510: ActivityType.Other, #	20	Polo	Sports and Workouts
        15530: ActivityType.Other, #	20	Racquetball	Sports and Workouts
        15520: ActivityType.Other, #	20	Racquetball, competitive	Sports and Workouts
        15535: ActivityType.Climbing, # 		20	Rock climbing	Sports and Workouts
        15540: ActivityType.Climbing, # 		20	Rock climbing, rappelling	Sports and Workouts
        15591: ActivityType.Other, #	20	Roller blading	Sports and Workouts
        15590: ActivityType.Other, #	20	Roller skating	Sports and Workouts
        15550: ActivityType.Other, #	20	Rope jumping, fast	Sports and Workouts
        15552: ActivityType.Other, #	20	Rope jumping, slow	Sports and Workouts
        15560: ActivityType.Other, #	20	Rugby	Sports and Workouts
        15570: ActivityType.Other, #	20	Shuffleboard, lawn bowling	Sports and Workouts
        15580: ActivityType.Skating, #	20	Skateboarding	Sports and Workouts
        15600: ActivityType.Other, #	20	Sky diving	Sports and Workouts
        15605: ActivityType.Other, #	20	Soccer	Sports and Workouts
        15610: ActivityType.Other, #	20	Soccer, casual, general	Sports and Workouts
        15640: ActivityType.Other, #	20	Softball	Sports and Workouts
        15630: ActivityType.Other, #	20	Softball, officiating	Sports and Workouts
        55001: ActivityType.Other, #	20	Spinning	Sports and Workouts
        15650: ActivityType.Other, #	20	Squash	Sports and Workouts
        15660: ActivityType.Other, #	20	Table tennis	Sports and Workouts
        15670: ActivityType.Other, #	20	Tai chi	Sports and Workouts
        15675: ActivityType.Other, #	20	Tennis	Sports and Workouts
        15680: ActivityType.Other, #	20	Tennis, doubles	Sports and Workouts
        15690: ActivityType.Other, #	20	Tennis, singles	Sports and Workouts
        15733: ActivityType.Other, #	20	Track and field (high jump, long jump, triple jump, javelin, pole vault)	Sports and Workouts
        15732: ActivityType.Other, #	20	Track and field (shot, discus, hammer throw)	Sports and Workouts
        15734: ActivityType.Other, #	20	Track and field (steeplechase, hurdles)	Sports and Workouts
        15700: ActivityType.Other, #	20	Trampoline	Sports and Workouts
        15250: ActivityType.Other, #	20	Ultimate frisbee	Sports and Workouts
        15711: ActivityType.Other, #	20	Volleyball	Sports and Workouts
        15725: ActivityType.Other, #	20	Volleyball, beach	Sports and Workouts
        15710: ActivityType.Other, #	20	Volleyball, light	Sports and Workouts
        15720: ActivityType.Other, #	20	Volleyball, non-competitive, 6 - 9 member team, general	Sports and Workouts
        15731: ActivityType.Other, #	20	Wallyball, general	Sports and Workouts
        15730: ActivityType.Other, #	20	Wrestling	Sports and Workouts
        27: ActivityType.Walking, #
        17010: ActivityType.Walking, #	27	Backpacking	Walking
        17085: ActivityType.Walking, #	27	Bird watching	Walking
        17020: ActivityType.Walking, #	27	Carrying infant or 15 pound load (e.g. suitcase)	Walking
        90012: ActivityType.Hiking, #	27	Hike	Walking
        17080: ActivityType.Hiking, #	27	Hiking, cross country	Walking
        17090: ActivityType.Walking, #	27	Marching, rapidly, military	Walking
        17105: ActivityType.Walking, #	27	Pushing a wheelchair	Walking
        17100: ActivityType.Walking, #	27	Pushing or pulling stroller with child or walking with children	Walking
        17110: ActivityType.Walking, #	27	Race walking	Walking
        17120: ActivityType.Walking, #	27	Rock climbing	Walking
        17140: ActivityType.Walking, #	27	Using crutches	Walking
        90013: ActivityType.Walking, #	27	Walk	Walking
        17160: ActivityType.Walking, #	27	Walking for pleasure	Walking
        17260: ActivityType.Walking, #	27	Walking, grass track	Walking
        17150: ActivityType.Walking, #	27	Walking, household	Walking
        31: ActivityType.Other, #
        52001: ActivityType.Other, #	31	Yoga	Yoga
        52002: ActivityType.Other, #	31	Yoga, Bikram	Yoga
        52003: ActivityType.Other, #	31	Yoga, Hatha	Yoga
        52004: ActivityType.Other, #	31	Yoga, Power	Yoga
        52005: ActivityType.Other, #	31	Yoga, Vinyasa	Yoga
        3016: ActivityType.Gym, #	90004	0	6 - 8 inch step	Aerobic step	Dancing
        3017: ActivityType.Gym, #	90004	0	10 - 12 inch step	Aerobic step	Dancing
        3020: ActivityType.Gym, #	90005	0	low impact	Aerobics	Dancing
        3021: ActivityType.Gym, #	90005	0	high impact	Aerobics	Dancing
        11810: ActivityType.Walking, #	90008	8	Carrying under 25 pounds	Walking while carrying things	Occupations
        11820: ActivityType.Walking, #	90008	8	Carrying 25 to 49 pounds	Walking while carrying things	Occupations
        11830: ActivityType.Walking, #	90008	8	Carrying 50 to 74 pounds	Walking while carrying things	Occupations
        11840: ActivityType.Walking, #	90008	8	Carrying 75 to 99 pounds	Walking while carrying things	Occupations
        11850: ActivityType.Walking, #	90008	8	Carrying over 100 pounds	Walking while carrying things	Occupations
        17035: ActivityType.Walking, #	90012	27	With 0 to 9 pound pack	Hike	Walking
        17040: ActivityType.Walking, #	90012	27	With 10 to 20 pound pack	Hike	Walking
        17050: ActivityType.Walking, #	90012	27	With 21 to 42 pound pack	Hike	Walking
        17060: ActivityType.Walking, #	90012	27	With 42+ pound pack	Hike	Walking
        17151: ActivityType.Walking, #	90013	27	less than 2 mph, strolling very slowly	Walk	Walking
        17152: ActivityType.Walking, #	90013	27	2.0 mph, slow pace	Walk	Walking
        17170: ActivityType.Walking, #	90013	27	2.5 mph	Walk	Walking
        17190: ActivityType.Walking, #	90013	27	3.0 mph, moderate pace	Walk	Walking
        17200: ActivityType.Walking, #	90013	27	3.5 mph, walking for exercise	Walk	Walking
        17220: ActivityType.Walking, #	90013	27	4.0 mph, very brisk pace	Walk	Walking
        17230: ActivityType.Walking, #	90013	27	4.5 mph, very, very brisk	Walk	Walking
        17231: ActivityType.Walking, #	90013	27	5.0 mph, speed walking	Walk	Walking
        17165: ActivityType.Walking, #	90013	27	Walking the dog	Walk	Walking
        1071: ActivityType.Cycling,
        2131: ActivityType.StrengthTraining
    }

    SupportedActivities = list(_activityTypeMappings.keys())


    def UserUploadedActivityURL(self, uploadId):
        return "https://www.fitbit.com/activities"

    # Use this function to get Autorization URL
    def WebInit(self):

        uri_parameters = {
            'response_type': 'code',
            'client_id': FITBIT_CLIENT_ID,
            'expire_in': FITBIT_DURATION,
            'redirect_uri': WEB_ROOT + reverse("oauth_return", kwargs={"service": "fitbit"}),
            'scope': 'activity location profile heartrate'
        }
        self.UserAuthorizationURL = self.FITBIT_AUTH_URI + "?" + urlencode(uri_parameters)


    # This function refresh access token if current is expire
    def _requestWithAuth(self, reqLambda, serviceRecord):
        session = requests.Session()

        now = datetime.now(timezone.utc)

        # Must do the replace to make the datetime timezone aware else it will crash
        if now > serviceRecord.Authorization.get("AccessTokenExpiresAt", 0).replace(tzinfo=pytz.utc):
            logging.info("Refresh Fitbit Authorization Token")

            # Expired access token, or still running (now-deprecated) indefinite access token.
            refreshToken = serviceRecord.Authorization.get("RefreshToken",
                                                           serviceRecord.Authorization.get("OAuthToken"))
            params = {
                "grant_type": "refresh_token",
                "refresh_token": refreshToken,
                "expires_in": FITBIT_DURATION
            }

            response = requests.post(self.FITBIT_REFRESH_URI,
                                     data=params,
                                     headers={
                                         'Authorization': 'Basic ' + self.header_encode,
                                         'Content-Type': 'application/x-www-form-urlencoded'
                                     })

            if response.status_code != 200:
                errors = response.json().get("errors")
                if (response.status_code == 401 or response.status_code == 403 
                    or (response.json().get("errors") != None
                        and len(errors) > 0
                        and errors[0].get("errorType") == "invalid_grant")):
                    raise APIException("%i - No authorization to refresh token for the user with FITBIT ID : %s" %(response.status_code, serviceRecord.ExternalID), block=True,
                                        user_exception=UserException(UserExceptionType.Authorization,
                                        intervention_required=True))
                else: 
                    raise APIException("%i - Can't refresh token (for an undefined reason) for the user with FITBIT ID : %s" %(response.status_code, serviceRecord.ExternalID))
            else:

                data = response.json()

                now = datetime.now(timezone.utc)
                endDate = now + timedelta(seconds=data['expires_in'])

                authorizationData = {
                    "AccessToken": data["access_token"],
                    "AccessTokenRequestedAt": now,
                    "AccessTokenExpiresAt": endDate,
                    "RefreshToken": data["refresh_token"],
                    'TokenType': data['token_type']
                }

                serviceRecord.Authorization.update(authorizationData)
                db.connections.update({"_id": serviceRecord._id}, {"$set": {"Authorization": authorizationData}})

        #session.headers.update({"Authorization": "access_token %s" % serviceRecord.Authorization["AccessToken"]})
        return reqLambda(session)

    # This function is used to se token info for a user, get expiration date, refresh and access token
    def RetrieveAuthorizationToken(self, req, level):
        code = req.GET.get("code")
        params = {
            "grant_type": "authorization_code",
            "code": code,
            "clientId": FITBIT_CLIENT_ID,
            "redirect_uri": WEB_ROOT + reverse("oauth_return", kwargs={"service": "fitbit"}),
            "expires_in": FITBIT_DURATION
        }

        response = requests.post(self.FITBIT_REFRESH_URI,
                                 data=params,
                                 headers={
                                    'Authorization': 'Basic '+ self.header_encode,
                                    'Content-Type': 'application/x-www-form-urlencoded'
                                 })

        if response.status_code != 200:
            raise APIException("Invalid code")
        data = response.json()

        logging.info("Retrieve Fitbit Authorization Token")

        now = datetime.now(timezone.utc)
        endDate = now + timedelta(seconds=data['expires_in'])

        authorizationData = {
            "AccessToken": data["access_token"],
            "AccessTokenRequestedAt": now,
            "AccessTokenExpiresAt": endDate,
            "RefreshToken": data["refresh_token"],
            'TokenType': data['token_type']
        }

        return (data["user_id"], authorizationData)

    # This function is used to revoke access token
    def RevokeAuthorization(self, serviceRecord):

        resp = self._requestWithAuth(lambda session: session.post(self.FITBIT_REVOKE_URI,
                                                                  data={
                                                                      "token": serviceRecord.Authorization.get('AccessToken')
                                                                  },
                                                                  headers={
                                                                      'Authorization': 'Basic '+ self.header_encode,
                                                                      'Content-Type': 'application/x-www-form-urlencoded'
                                                                  }), serviceRecord)

        if resp.status_code != 204 and resp.status_code != 200:
            # The modification below was made to fix the case where an user revoke the Hub access from fitbit.
            # Now the user can disconnect the service from the Hub without blocking.
            # raise APIException("Unable to deauthorize Fitbit auth token, status " + str(resp.status_code) + " resp " + resp.text)
            logging.warning("Impossible to revoke from fitbit. Deleting connection from the Hub Anyway")

        logging.info("Revoke Fitbit Authorization")

    def DownloadActivityList(self, svcRecord, exhaustive=False):
        activities = []
        exclusions = []
        before = earliestDate = None

        # define low parameter
        limit = 20
        offset = 0
        sort = "desc"
        # get user Fitbit ID
        userID = svcRecord.ExternalID
        # get service Tapiriik ID
        service_id = svcRecord._id
        # get user "start sync from date" info
        # then prepare afterDate var (this var determine the date since we download activities)
        user = db.users.find_one({'ConnectedServices': {'$elemMatch': {'ID': service_id, 'Service': 'fitbit'}}})
        afterDateObj = datetime.now() - timedelta(days=40)

        # Obscure setting only used by fitbit so forcing to false
        # And for other obscure reason this date could be set couple of month before now so non exhaustive sync are sort of exhaustive.
        if user['Config']['sync_skip_before'] is not None and False:
            afterDateObj = user['Config']['sync_skip_before']
        else:
            if exhaustive:
                afterDateObj = datetime.now() - timedelta(days=3650) # throw back to 10 years

        afterDate = afterDateObj.strftime("%Y-%m-%d")
        logging.info("\t Download Fitbit activities since : " + afterDate)

        # prepare parameters to set in fitbit request uri
        uri_parameters = {
            'limit': limit,
            'offset': offset,
            'sort': sort,
            'afterDate': afterDate,
            'token': svcRecord.Authorization.get('AccessToken')
        }
        # set base fitbit request uri
        activities_uri_origin = 'https://api.fitbit.com/1/user/' + userID + '/activities/list.json'

        # first execute offset = 0,
        # offset will be set to -1 if fitbit response don't give next pagination info
        # offset will be incremented by 1 if fitbit response give next pagination info
        index_total = 0
        while offset > -1:

            # prepare uri parameters
            uri_parameters['offset'] = offset
            # build fitbit uri with new parameters
            activities_uri = activities_uri_origin + "?" + urlencode(uri_parameters)
            # execute fitbit request using "request with auth" function (it refreshes token if needed)
            logging.info("\t\t downloading offset : " + str(offset))
            resp = self._requestWithAuth(lambda session: session.get(
                activities_uri,
                headers={
                    'Authorization': 'Bearer ' + svcRecord.Authorization.get('AccessToken')
                }), svcRecord)

            # check if request has error
            if resp.status_code != 204 and resp.status_code != 200:
                raise APIException("Unable to find Fitbit activities")

            # get request data
            data = {}
            try:
                data = resp.json()
            except ValueError:
                raise APIException("Failed parsing fitbit list response %s - %s" % (resp.status_code, resp.text))

            # if request return activities infos
            if data['activities']:
                ftbt_activities = data['activities']
                logging.info("\t\t nb activity : " + str(len(ftbt_activities)))

                # for every activities in this request pagination
                # (Fitbit give 20 activities MAXIMUM, use limit parameter)
                for ftbt_activity in ftbt_activities:
                    index_total = index_total +1
                    activity = UploadedActivity()
                    activity.SourceServiceID = self.ID

                    #parse date start to get timezone and date
                    activity.StartTime = parse(ftbt_activity["startTime"])
                    activity.TZ = pytz.FixedOffset(int(datetime.utcoffset(activity.StartTime).total_seconds()/60))

                    logger.debug("\tActivity s/t %s: %s" % (activity.StartTime, ftbt_activity["activityName"]))

                    activity.EndTime = activity.StartTime + timedelta(0, (ftbt_activity["duration"]/1000))
                    activity.ServiceData = {"ActivityID": ftbt_activity["logId"], "Manual": ftbt_activity["logType"]}

                    # check if activity type ID exists
                    if ftbt_activity["activityTypeId"] not in self._reverseActivityTypeMappings:
                        exclusions.append(APIExcludeActivity("Unsupported activity type %s" % ftbt_activity["activityTypeId"],
                                                             activity_id=ftbt_activity["logId"],
                                                             user_exception=UserException(UserExceptionType.Other)))
                        logger.info("\t\tUnknown activity")
                        continue

                    activity.Type = self._reverseActivityTypeMappings[ftbt_activity["activityTypeId"]]

                    if "distance" in ftbt_activity :
                        activity.Stats.Distance = ActivityStatistic(ActivityStatisticUnit.Kilometers,
                                                                value=ftbt_activity["distance"])

                    if "speed" in ftbt_activity:
                        activity.Stats.Speed = ActivityStatistic(
                            ActivityStatisticUnit.KilometersPerHour,
                            avg=ftbt_activity["speed"],
                            max=ftbt_activity["speed"]
                        )
                    activity.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilocalories, value=ftbt_activity["calories"])
                    # Todo: find fitbit data name
                    #activity.Stats.MovingTime = ActivityStatistic(ActivityStatisticUnit.Seconds, value=ride[
                    #    "moving_time"] if "moving_time" in ride and ride[
                    #    "moving_time"] > 0 else None)  # They don't let you manually enter this, and I think it returns 0 for those activities.
                    # Todo: find fitbit data name
                    #if "average_watts" in ride:
                    #    activity.Stats.Power = ActivityStatistic(ActivityStatisticUnit.Watts,
                    #                                             avg=ride["average_watts"])

                    if "averageHeartRate" in ftbt_activity:
                        activity.Stats.HR.update(
                            ActivityStatistic(ActivityStatisticUnit.BeatsPerMinute, avg=ftbt_activity["averageHeartRate"]))
                    # Todo: find fitbit data name
                    #if "max_heartrate" in ride:
                    #    activity.Stats.HR.update(
                    #        ActivityStatistic(ActivityStatisticUnit.BeatsPerMinute, max=ride["max_heartrate"]))
                    # Todo: find fitbit data name
                    #if "average_cadence" in ride:
                    #    activity.Stats.Cadence.update(ActivityStatistic(ActivityStatisticUnit.RevolutionsPerMinute,
                    #                                                    avg=ride["average_cadence"]))
                    # Todo: find fitbit data name
                    #if "average_temp" in ride:
                    #    activity.Stats.Temperature.update(
                    #        ActivityStatistic(ActivityStatisticUnit.DegreesCelcius, avg=ride["average_temp"]))

                    if "calories" in ftbt_activity:
                        activity.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilocalories,
                                                                  value=ftbt_activity["calories"])
                    activity.Name = ftbt_activity["activityName"]


                    activity.Private = False
                    if ftbt_activity['logType'] == 'manual':
                        activity.Stationary = True
                    else:
                        activity.Stationary = False


                    # Todo: find fitbit data
                    #activity.GPS = ("start_latlng" in ride) and (ride["start_latlng"] is not None)
                    activity.AdjustTZ()
                    activity.CalculateUID()
                    activities.append(activity)
                    logging.info("\t\t Fitbit Activity ID : " + str(ftbt_activity["logId"]))

                if not exhaustive:
                    break
            # get next info for while condition and prepare offset for next request
            if 'next' not in data['pagination'] or not data['pagination']['next']:
                next = None
                offset = -1
            else:
                next = data['pagination']['next']
                offset = offset + 1

        logging.info("\t\t total Fitbit activities downloaded : " + str(index_total))
        return activities, exclusions

    def DownloadActivity(self, svcRecord, activity):

        userID = svcRecord.ExternalID
        activity_id = activity.ServiceData["ActivityID"]

        logging.info("\t\t FITBIT LOADING  : " + str(activity_id))
        activity_tcx_uri = 'https://api.fitbit.com/1/user/' + userID + '/activities/' + str(activity_id) + '.tcx'
        resp = self._requestWithAuth(lambda session: session.get(
            activity_tcx_uri,
            headers={
                'Authorization': 'Bearer ' + svcRecord.Authorization.get('AccessToken')
            }), svcRecord)
        # check if request has error
        if resp.status_code != 204 and resp.status_code != 200:
            logger.warn("Fitbit responded with the code %i, it is unable to send the activity with ID:%s from USER:%s" % (resp.status_code, activity_id, userID))
            return activity

        # Prepare tcxio params
        ns = copy.deepcopy(TCXIO.Namespaces)
        ns["tcx"] = ns[None]
        del ns[None]

        # Read tcx to know if this is a stationary activity or not
        try:
            root = etree.XML(resp.text.encode('utf-8'))
        except:
            root = etree.fromstring(resp.text.encode('utf-8'))

        xacts = root.find("tcx:Activities", namespaces=ns)
        if xacts is None:
            raise ValueError("No activities element in TCX")

        xact = xacts.find("tcx:Activity", namespaces=ns)
        if xact is None:
            raise ValueError("No activity element in TCX")

        # Define activity type from tcx
        if not activity.Type or activity.Type == ActivityType.Other:
            if xact.attrib["Sport"] == "Biking":
                activity.Type = ActivityType.Cycling
            elif xact.attrib["Sport"] == "Running":
                activity.Type = ActivityType.Running

        # Find all lap in tcx
        xlaps = xact.findall("tcx:Lap", namespaces=ns)
        if len(xlaps) > 0:
            activity = TCXIO.Parse(resp.text.encode('utf-8'), activity)
        else:
            # Define lap for activity
            lap = Lap(stats=activity.Stats, startTime=activity.StartTime, endTime=activity.EndTime)
            activity.Laps = [lap]
            lap.Waypoints = []
            activity.GPS = False
            activity.Stationary = len(lap.Waypoints) == 0

        return activity

    def UploadActivity(self, svcRecord, activity):
        logging.info("UPLOAD To Fitbit Activity tz " + str(activity.TZ) + " dt tz " + str(
            activity.StartTime.tzinfo) + " starttime " + str(activity.StartTime))

        logger.info("Activity tz " + str(activity.TZ) + " dt tz " + str(activity.StartTime.tzinfo) + " starttime " + str(activity.StartTime))

        # Check if we're currently uploading item
        if self.LastUpload is not None:
            while (datetime.now() - self.LastUpload).total_seconds() < 5:
                time.sleep(1)
                logger.debug("Inter-upload cooldown")

        upload_id = None

        userID = svcRecord.ExternalID

        activity_date = activity.StartTime.strftime("%Y-%m-%d")
        activity_time = activity.StartTime.strftime("%H:%M:%S")

        if activity.Stats.MovingTime is not None and activity.Stats.MovingTime.Value is not None:
            duration = int(activity.Stats.MovingTime.asUnits(ActivityStatisticUnit.Milliseconds).Value)
        else:
            durationDelta = activity.EndTime - activity.StartTime
            duration = durationDelta.total_seconds() * 1000

        distance = 0
        if activity.Stats.Distance:
            distance = activity.Stats.Distance.asUnits(ActivityStatisticUnit.Meters).Value

        calories = 0
        if activity.Stats.Energy and activity.Stats.Energy.asUnits(ActivityStatisticUnit.Kilocalories).Value is not None:
            calories = activity.Stats.Energy.asUnits(ActivityStatisticUnit.Kilocalories).Value

        parameters = {
            'manualCalories': int(calories),
            'startTime': activity_time,
            'date': activity_date,
            'durationMillis': int(duration),
            'distance': distance,
            'distanceUnit': 'Meter',

        }

        # If activity type is "other" set name into parameters, else set activity type
        # uri parameters doesn't accept both on same post
        if activity.Type != 20:
            activity_name = activity.StartTime.strftime("%d/%m/%Y")
            if activity.Name:
                activity_name = activity.Name
            parameters['activityName'] = activity_name
        else:
            parameters['activityId'] = self._activityTypeMappings[activity.Type]


        activity_upload_uri = 'https://api.fitbit.com/1/user/' + userID + '/activities.json'
        resp = self._requestWithAuth(lambda session: session.post(
            activity_upload_uri,
            data=parameters,
            headers={
                'Authorization': 'Bearer ' + svcRecord.Authorization.get('AccessToken')
            }), svcRecord)

        self.LastUpload = datetime.now()

        if resp.status_code != 201 and resp.status_code != 200:
            if resp.status_code == 401:
                raise APIException(
                    "No authorization to upload activity " + activity.UID + " response " + resp.text + " status " + str(
                        resp.status_code), block=True,
                    user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))

            raise APIException(
                "Unable to upload activity " + activity.UID + " response " + resp.text + " status " + str(
                    resp.status_code))

        resp_json = resp.json()
        upload_id = resp_json['activityLog']['activityId']

        return upload_id

    def DeleteCachedData(self, serviceRecord):
        cachedb.fitbit_cache.remove({"Owner": serviceRecord.ExternalID})
        cachedb.fitbit_activity_cache.remove({"Owner": serviceRecord.ExternalID})

    def PartialSyncTriggerGET(self, req):
        # To verify the endpoint, fitbit send 2 verification codes.
        # - One of it must match the verification code given in the app configuration page. 
        #   It is stored in the local settings in the FITBIT_WEBHOOK_VERIFICATION_CODE var.
        #   If the check succeed we have to return a 204 status code.

        # - The second is voluntarily invalid.
        #   So the check must fail and we have to send a 404 status code
        from django.http import HttpResponse
        if req.GET["verify"] == FITBIT_WEBHOOK_VERIFICATION_CODE:
            return HttpResponse(status=204)
        return HttpResponse(status=404)


    def SubscribeToPartialSyncTrigger(self, serviceRecord):
        # Safety features to avoid resubscribing multiple times
        if serviceRecord.PartialSyncTriggerSubscribed:
            logging.warning("Trying to re-subscribe an already subscribed user skipping")
            return
        
        webhook_sub_URL = "https://api.fitbit.com/1/user/-/activities/apiSubscriptions/"+serviceRecord.ExternalID+".json?subscriberId=" + FITBIT_SUBSCRIBER_ID
        logging.info(webhook_sub_URL)

        resp = self._requestWithAuth(lambda session: session.post(
            webhook_sub_URL,
            headers={
                'Authorization': 'Bearer ' + serviceRecord.Authorization.get('AccessToken')
        }), serviceRecord)

        if resp.status_code != 201:
            logger.error("Can't subscribe user to Fitbit webhook {}".format(str(resp)))
        else:
            serviceRecord.SetPartialSyncTriggerSubscriptionState(True)


    def ExternalIDsForPartialSyncTrigger(self, req):
        pause_delay_in_sec = 3600
        data = json.loads(req.body.decode("UTF-8"))
        
        
        users_to_sync = []
        # We filter the data to get uniques user IDs and remove all unnecessary fitbit data
        # We ensure user IDs are unique because fitbit send A LOT of data and maybe duplicates
        idList = list({notif.get("ownerId") for notif in data if notif.get('collectionType') == 'activities'})
        
        for id in idList:
            # Telling which user has a fitbit trigger event
            logging.info("[WEBHOOK] FITBIT CALLBACK for user id %s" % id)
            redis_key = "fitbit-wh-recent-sync:%s" % id
            # If the user has no recent sync key in redis
            if redis.get(redis_key) == None:
                # It's ok and we add the id to the users to sync list
                # And we also set a recent-sync key into redis wich will expire in "pause_delay_in_sec"
                users_to_sync.append(id)
                redis.setex(redis_key, 1, pause_delay_in_sec)
            else:
                # The user has been synced recently so ignoring its trigger
                logging.info("\t\tbut ignored because it has already been triggered in the last %i hours" % (pause_delay_in_sec/3600))
            
        return users_to_sync
        