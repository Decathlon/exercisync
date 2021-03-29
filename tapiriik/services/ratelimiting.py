from tapiriik.database import ratelimit as rl_db, redis
from tapiriik.settings import _GLOBAL_LOGGER
from pymongo.read_preferences import ReadPreference
from datetime import datetime, timedelta
import math
import logging

class RateLimitExceededException(Exception):
	pass

class RateLimit:
	def Limit(key):
		current_limits = rl_db.limits.find({"Key": key}, {"Max": 1, "Count": 1})
		for limit in current_limits:
			if limit["Max"] < limit["Count"]:
				# We can't continue without exceeding this limit
				# Don't want to halt the synchronization worker to wait for 15min-1 hour
				# So...
				raise RateLimitExceededException()
		_GLOBAL_LOGGER.info("Adding 1 to count")
		rl_db.limits.update_many({"Key": key}, {"$inc": {"Count": 1}})

	def Refresh(key, limits):
		# Limits is in format [(timespan, max-count),...]
		# The windows are anchored at midnight
		# The timespan is used to uniquely identify limit instances between runs
		midnight = datetime.combine(datetime.utcnow().date(), datetime.min.time())
		time_since_midnight = (datetime.utcnow() - midnight)

		rl_db.limits.delete_many({"Key": key, "Expires": {"$lt": datetime.utcnow()}})
		current_limits = list(rl_db.limits.with_options(read_preference=ReadPreference.PRIMARY).find({"Key": key}, {"Duration": 1}))
		missing_limits = [x for x in limits if x[0].total_seconds() not in [limit["Duration"] for limit in current_limits]]
		for limit in missing_limits:
			window_start = midnight + timedelta(seconds=math.floor(time_since_midnight.total_seconds()/limit[0].total_seconds()) * limit[0].total_seconds())
			window_end = window_start + limit[0]
			rl_db.limits.insert({"Key": key, "Count": 0, "Duration": limit[0].total_seconds(), "Max": limit[1], "Expires": window_end})

class RedisRateLimit:
	def IsOneRateLimitReached(rate_limited_services):
		for svc in rate_limited_services:
			for limit in svc.GlobalRateLimits:
				limit_timedelta_seconds = int(limit[0].total_seconds())
				limit_number = limit[1]
				limit_key = svc.ID+":lm:"+str(limit_timedelta_seconds)
				actual_limit = redis.get(limit_key)
				if actual_limit != None:
					if int(actual_limit.decode('utf-8')) >= limit_number:
						return True
		return False

	def Limit(key, limits):
		for limit in limits:
			limit_timedelta_seconds = int(limit[0].total_seconds())
			limit_number = limit[1]
			limit_key = key+":lm:"+str(limit_timedelta_seconds)

			# Increasing the key by one
			# If it does not exist or it has expired it will be set to one
			# The incr function of redis is atomic and "SHOULD" not create race condition
			actual_rl = redis.incr(limit_key)

			# The key expires at time is determined by :
			# - now in UNIX epoch floor divided by limit_timedelta_seconds
			# - added by one to simulate a ceil division
			# - multiplied by limit_timedelta_seconds to set this back in an UNIX epoch timestamp
			redis.expireat(limit_key, ((int(datetime.now().strftime('%s')) // limit_timedelta_seconds)+1) * limit_timedelta_seconds)

			# Well, here we might loose 1 api call but this is for security purpose if an unexpected race condition happens
			# Better safe than sorry :)
			if actual_rl >= limit_number-1:
				raise RateLimitExceededException("Actual rate limit : %s / Max rate limit : %s" % (actual_rl, limit_number))

			_GLOBAL_LOGGER.info("Adding 1 to %s %s limit count. It is now %s/%s" % (key, limit_number, actual_rl, limit_number))