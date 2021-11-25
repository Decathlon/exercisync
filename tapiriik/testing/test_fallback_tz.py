import time
from unittest.case import TestCase
from tapiriik.sync import SynchronizationTask
from tapiriik.auth import User
from tapiriik.database import db
from bson.objectid import ObjectId
import pytz

class FallbackTzTest(TestCase):

    def test_user_with_no_timezone_and_no_activities_return_none(self):
        user = User.Create()
        activities = []
        
        sync_task = SynchronizationTask(user)
        fallback_tz = sync_task._estimateFallbackTZ(activities)

        self.assertIsNone(fallback_tz)

        # Cleaning created User
        db.users.delete_one({"_id": ObjectId(user["_id"])})


    def test_user_with_none_timezone_and_no_activities_return_none(self):
        user = User.Create()
        user.update({"Timezone": None})
        activities = []
        
        sync_task = SynchronizationTask(user)
        fallback_tz = sync_task._estimateFallbackTZ(activities)
        
        self.assertIsNone(fallback_tz)

        # Cleaning created User
        db.users.delete_one({"_id": ObjectId(user["_id"])})


    def test_user_with_utc_timezone_and_no_activities_return_utc(self):
        user = User.Create()
        user.update({"Timezone": "UTC"})
        activities = []
        
        sync_task = SynchronizationTask(user)
        fallback_tz = sync_task._estimateFallbackTZ(activities) 

        self.assertIsInstance(fallback_tz, type(pytz.UTC))

        # Cleaning created User
        db.users.delete_one({"_id": ObjectId(user["_id"])})
