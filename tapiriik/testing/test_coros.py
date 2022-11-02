from datetime import datetime
from unittest import TestCase

import pytz

from tapiriik.services.Coros import CorosService
from tapiriik.services.interchange import ActivityType, ActivityStatistic, ActivityStatisticUnit

Coros = CorosService()


# To run test : 'docker exec -it hub-decathlon-web-1 python manage.py test tapiriik.testing.test_coros'

class CorosTest(TestCase):

    def test_map_to_hub_activities_walking(self):
        # given
        activities_data = [{
            "avgFrequency": 117,
            "avgHeartRate": 124,
            "avgSpeed": 2.0,
            "calorie": 520898.0,
            "deviceName": "COROS APEX 46mm",
            "distance": 1.0,
            "duration": 3606,
            "endTime": 1666948512,
            "endTimezone": 8,
            "fitUrl": "https://localhost:8000",
            "labelId": "xxx",
            "mode": 31,
            "startTime": 1666944907,
            "startTimezone": 8,
            "step": 1092,
            "subMode": 2
        }]

        # when
        hub_activities, exclusions = Coros._map_to_hub_activities(activities_data)

        # then
        self.assertEqual(len(exclusions), 0, 'should have no error')

        self.assertEqual(len(hub_activities), 1, 'should map one activity')

        self.assertEqual(hub_activities[0].SourceServiceID, Coros.ID)
        self.assertEqual(hub_activities[0].TZ, pytz.UTC)
        self.assertEqual(hub_activities[0].StartTime, datetime.fromtimestamp(1666944907).astimezone(pytz.UTC))
        self.assertEqual(hub_activities[0].EndTime, datetime.fromtimestamp(1666948512).astimezone(pytz.UTC))
        self.assertEqual(hub_activities[0].ServiceData, {"ActivityID": "xxx"})
        self.assertEqual(hub_activities[0].Type, ActivityType.Walking)
        self.assertEqual(hub_activities[0].Stats.Distance, ActivityStatistic(ActivityStatisticUnit.Meters, 1.0))
        self.assertEqual(
            hub_activities[0].Stats.Energy,
            ActivityStatistic(ActivityStatisticUnit.Kilocalories, 520.8980)
        )
        self.assertEqual(
            hub_activities[0].Stats.Speed,
            ActivityStatistic(ActivityStatisticUnit.SecondsPerKilometer, avg=2.0)
        )
        self.assertEqual(
            hub_activities[0].Stats.RunCadence,
            ActivityStatistic(ActivityStatisticUnit.StepsPerMinute, avg=117.0)
        )
        self.assertEqual(hub_activities[0].FitFileUrl, "https://localhost:8000")
        self.assertEqual(hub_activities[0].Name, ActivityType.Walking)
        self.assertIsNotNone(hub_activities[0].UID)
