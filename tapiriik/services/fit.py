from datetime import datetime, timedelta
from .interchange import WaypointType, ActivityStatisticUnit, ActivityType, LapIntensity, LapTriggerMethod, Activity, Lap, UploadedActivity, Waypoint, Location, ActivityStatistics
from .devices import DeviceIdentifier, DeviceIdentifierType, Device
from fitparse.profile import FIELD_TYPES
import struct
import sys
import pytz
import json

# This const has been added to avoid using different values for the parser and the dumper.
# Previously it was this one for the dumper and it was a rounded value for the parser.
# This difference has caused lat/long shifts of few centimeters during the parsing or dumping process.
# The other goal is to avoid doing this calculation thousands of times (each point lat and long 2 times for parsing and dumping)
SEMI_CIRCLE_CONST = (2 ** 31 / 180)

class FITFileType:
	Activity = 4 # The only one we care about now.

class FITManufacturer:
	DEVELOPMENT = 255 # $1500/year for one of these numbers.

class FITEvent:
	Timer = 0
	Lap = 9
	Activity = 26

class FITEventType:
	Start = 0
	Stop = 1

# It's not a coincidence that these enums match the ones in interchange perfectly
class FITLapIntensity:
	Active = 0
	Rest = 1
	Warmup = 2
	Cooldown = 3

class FITLapTriggerMethod:
    Manual = 0
    Time = 1
    Distance = 2
    PositionStart = 3
    PositionLap = 4
    PositionWaypoint = 5
    PositionMarked = 6
    SessionEnd = 7
    FitnessEquipment = 8


class FITActivityType:
	GENERIC = 0
	RUNNING = 1
	CYCLING = 2
	TRANSITION = 3
	FITNESS_EQUIPMENT = 4
	SWIMMING = 5
	WALKING = 6
	ALL = 254

class FITMessageDataType:
	def __init__(self, name, typeField, size, packFormat, invalid, formatter=None):
		self.Name = name
		self.TypeField = typeField
		self.Size = size
		self.PackFormat = packFormat
		self.Formatter = formatter
		self.InvalidValue = invalid

class FITMessageTemplate:
	def __init__(self, name, number, *args, fields=None):
		self.Name = name
		self.Number = number
		self.Fields = {}
		self.FieldNameSet = set()
		self.FieldNameList = []
		if len(args) == 1 and type(args[0]) is dict:
			fields = args[0]
			self.Fields = fields
			self.FieldNameSet = set(fields.keys()) # It strikes me that keys might already be a set?
		else:
			# Supply fields in order NUM, NAME, TYPE
			for x in range(0, int(len(args)/3)):
				n = x * 3
				self.Fields[args[n+1]] = {"Name": args[n+1], "Number": args[n], "Type": args[n+2]}
				self.FieldNameSet.add(args[n+1])
		sortedFields = list(self.Fields.values())
		sortedFields.sort(key = lambda x: x["Number"])
		self.FieldNameList = [x["Name"] for x in sortedFields] # *ordered*


class FITMessageGenerator:
	def __init__(self):
		self._types = {}
		self._messageTemplates = {}
		self._definitions = {}
		self._result = []
		# All our convience functions for preparing the field types to be packed.
		def stringFormatter(input):
			raise Exception("Not implemented")
		def dateTimeFormatter(input):
			# UINT32
			# Seconds since UTC 00:00 Dec 31 1989. If <0x10000000 = system time
			if input is None:
				return struct.pack("<I", 0xFFFFFFFF)
			delta = round((input - datetime(hour=0, minute=0, month=12, day=31, year=1989)).total_seconds())
			return struct.pack("<I", delta)
		def msecFormatter(input):
			# UINT32
			if input is None:
				return struct.pack("<I", 0xFFFFFFFF)
			return struct.pack("<I", round((input if type(input) is not timedelta else input.total_seconds()) * 1000))
		def mmPerSecFormatter(input):
			# UINT16
			if input is None:
				return struct.pack("<H", 0xFFFF)
			return struct.pack("<H", round(input * 1000))
		def cmFormatter(input):
			# UINT32
			if input is None:
				return struct.pack("<I", 0xFFFFFFFF)
			return struct.pack("<I", round(input * 100))
		def altitudeFormatter(input):
			# UINT16
			if input is None:
				return struct.pack("<H", 0xFFFF)
			return struct.pack("<H", round((input + 500) * 5)) # Increments of 1/5, offset from -500m :S
		def semicirclesFormatter(input):
			# SINT32
			if input is None:
				return struct.pack("<i", 0x7FFFFFFF) # FIT-defined invalid value
			return struct.pack("<i", round(input * SEMI_CIRCLE_CONST))
		def versionFormatter(input):
			# UINT16
			if input is None:
				return struct.pack("<H", 0xFFFF)
			return struct.pack("<H", round(input * 100))


		def defType(name, *args, **kwargs):

			aliases = [name] if type(name) is not list else name
			# Cheap cheap cheap
			for alias in aliases:
				self._types[alias] = FITMessageDataType(alias, *args, **kwargs)

		defType(["enum", "file"], 0x00, 1, "B", 0xFF)
		defType("sint8", 0x01, 1, "b", 0x7F)
		defType("uint8", 0x02, 1, "B", 0xFF)
		defType("sint16", 0x83, 2, "h", 0x7FFF)
		defType(["uint16", "manufacturer"], 0x84, 2, "H", 0xFFFF)
		defType("sint32", 0x85, 4, "i", 0x7FFFFFFF)
		defType("uint32", 0x86, 4, "I", 0xFFFFFFFF)
		defType("string", 0x07, None, None, 0x0, formatter=stringFormatter)
		defType("float32", 0x88, 4, "f", 0xFFFFFFFF)
		defType("float64", 0x89, 8, "d", 0xFFFFFFFFFFFFFFFF)
		defType("uint8z", 0x0A, 1, "B", 0x00)
		defType("uint16z", 0x0B, 2, "H", 0x00)
		defType("uint32z", 0x0C, 4, "I", 0x00)
		defType("byte", 0x0D, 1, "B", 0xFF) # This isn't totally correct, docs say "an array of bytes"

		# Not strictly FIT fields, but convenient.
		defType("date_time", 0x86, 4, None, 0xFFFFFFFF, formatter=dateTimeFormatter)
		defType("duration_msec", 0x86, 4, None, 0xFFFFFFFF, formatter=msecFormatter)
		defType("distance_cm", 0x86, 4, None, 0xFFFFFFFF, formatter=cmFormatter)
		defType("mmPerSec", 0x84, 2, None, 0xFFFF, formatter=mmPerSecFormatter)
		defType("semicircles", 0x85, 4, None, 0x7FFFFFFF, formatter=semicirclesFormatter)
		defType("altitude", 0x84, 2, None, 0xFFFF, formatter=altitudeFormatter)
		defType("version", 0x84, 2, None, 0xFFFF, formatter=versionFormatter)

		def defMsg(name, *args):
			self._messageTemplates[name] = FITMessageTemplate(name, *args)

		defMsg("file_id", 0,
			0, "type", "file",
			1, "manufacturer", "manufacturer",
			2, "product", "uint16",
			3, "serial_number", "uint32z",
			4, "time_created", "date_time",
			5, "number", "uint16")

		defMsg("file_creator", 49,
			0, "software_version", "uint16",
			1, "hardware_version", "uint8")

		defMsg("activity", 34,
			253, "timestamp", "date_time",
			1, "num_sessions", "uint16",
			2, "type", "enum",
			3, "event", "enum", # Required
			4, "event_type", "enum",
			5, "local_timestamp", "date_time")

		defMsg("session", 18,
			253, "timestamp", "date_time",
			2, "start_time", "date_time", # Vs timestamp, which was whenever the record was "written"/end of the session
			7, "total_elapsed_time", "duration_msec", # Including pauses
			8, "total_timer_time", "duration_msec", # Excluding pauses
			59, "total_moving_time", "duration_msec",
			5, "sport", "enum",
			6, "sub_sport", "enum",
			0, "event", "enum",
			1, "event_type", "enum",
			9, "total_distance", "distance_cm",
			11,"total_calories", "uint16",
			14, "avg_speed", "mmPerSec",
			15, "max_speed", "mmPerSec",
			16, "avg_heart_rate", "uint8",
			17, "max_heart_rate", "uint8",
			18, "avg_cadence", "uint8",
			19, "max_cadence", "uint8",
			20, "avg_power", "uint16",
			21, "max_power", "uint16",
			22, "total_ascent", "uint16",
			23, "total_descent", "uint16",
			49, "avg_altitude", "altitude",
			50, "max_altitude", "altitude",
			71, "min_altitude", "altitude",
			57, "avg_temperature", "sint8",
			58, "max_temperature", "sint8")

		defMsg("lap", 19,
			253, "timestamp", "date_time",
			0, "event", "enum",
			1, "event_type", "enum",
			25, "sport", "enum",
			23, "intensity", "enum",
			24, "lap_trigger", "enum",
			2, "start_time", "date_time", # Vs timestamp, which was whenever the record was "written"/end of the session
			7, "total_elapsed_time", "duration_msec", # Including pauses
			8, "total_timer_time", "duration_msec", # Excluding pauses
			52, "total_moving_time", "duration_msec",
			9, "total_distance", "distance_cm",
			11,"total_calories", "uint16",
			13, "avg_speed", "mmPerSec",
			14, "max_speed", "mmPerSec",
			15, "avg_heart_rate", "uint8",
			16, "max_heart_rate", "uint8",
			17, "avg_cadence", "uint8", # FIT rolls run and bike cadence into one
			18, "max_cadence", "uint8",
			19, "avg_power", "uint16",
			20, "max_power", "uint16",
			21, "total_ascent", "uint16",
			22, "total_descent", "uint16",
			42, "avg_altitude", "altitude",
			43, "max_altitude", "altitude",
			62, "min_altitude", "altitude",
			50, "avg_temperature", "sint8",
			51, "max_temperature", "sint8"
			)

		defMsg("record", 20,
			253, "timestamp", "date_time",
			0, "position_lat", "semicircles",
			1, "position_long", "semicircles",
			2, "altitude", "altitude",
			3, "heart_rate", "uint8",
			4, "cadence", "uint8",
			5, "distance", "distance_cm",
			6, "speed", "mmPerSec",
			7, "power", "uint16",
			13, "temperature", "sint8",
			33, "calories", "uint16",
			)

		defMsg("event", 21,
			253, "timestamp", "date_time",
			0, "event", "enum",
			1, "event_type", "enum")

		defMsg("device_info", 23,
			253, "timestamp", "date_time",
			0, "device_index", "uint8",
			1, "device_type", "uint8",
			2, "manufacturer", "manufacturer",
			3, "serial_number", "uint32z",
			4, "product", "uint16",
			5, "software_version", "version"
			)

	def _write(self, contents):
		self._result.append(contents)

	def GetResult(self):
		return b''.join(self._result)

	def _defineMessage(self, local_no, global_message, field_names):
		assert local_no < 16 and local_no >= 0
		if set(field_names) - set(global_message.FieldNameList):
			raise ValueError("Attempting to use undefined fields %s" % (set(field_names) - set(global_message.FieldNameList)))
		messageHeader = 0b01000000
		messageHeader = messageHeader | local_no

		local_fields = {}

		arch = 0 # Little-endian
		global_no = global_message.Number
		field_count = len(field_names)
		pack_tuple = (messageHeader, 0, arch, global_no, field_count)
		for field_name in global_message.FieldNameList:
			if field_name in field_names:
				field = global_message.Fields[field_name]
				field_type = self._types[field["Type"]]
				pack_tuple += (field["Number"], field_type.Size, field_type.TypeField)
				local_fields[field_name] = field
		self._definitions[local_no] = FITMessageTemplate(global_message.Name, local_no, local_fields)
		self._write(struct.pack("<BBBHB" + ("BBB" * field_count), *pack_tuple))
		return self._definitions[local_no]


	def GenerateMessage(self, name, **kwargs):
		globalDefn = self._messageTemplates[name]

		# Create a subset of the global message's fields
		localFieldNamesSet = set()
		for fieldName in kwargs:
			localFieldNamesSet.add(fieldName)

		# I'll look at this later
		compressTS = False

		# Are these fields covered by an existing local message type?
		active_definition = None
		for defn_n in self._definitions:
			defn = self._definitions[defn_n]
			if defn.Name == name:
				if defn.FieldNameSet == localFieldNamesSet:
					active_definition = defn

		# If not, create a new local message type with these fields
		if not active_definition:
			active_definition_no = len(self._definitions)
			active_definition = self._defineMessage(active_definition_no, globalDefn, localFieldNamesSet)

		if compressTS and active_definition.Number > 3:
			raise Exception("Can't use compressed timestamp when local message number > 3")

		messageHeader = 0
		if compressTS:
			messageHeader = messageHeader | (1 << 7)
			tsOffsetVal = -1 # TODO
			messageHeader = messageHeader | (active_definition.Number << 4)
		else:
			messageHeader = messageHeader | active_definition.Number

		packResult = [struct.pack("<B", messageHeader)]
		for field_name in active_definition.FieldNameList:
			field = active_definition.Fields[field_name]
			field_type = self._types[field["Type"]]
			try:
				if field_type.Formatter:
					result = field_type.Formatter(kwargs[field_name])
				else:
					sanitized_value = kwargs[field_name]
					if sanitized_value is None:
						result = struct.pack("<" + field_type.PackFormat, field_type.InvalidValue)
					else:
						if field_type.PackFormat in ["B","b", "H", "h", "I", "i"]:
							sanitized_value = round(sanitized_value)
						try:
							result = struct.pack("<" + field_type.PackFormat, sanitized_value)
						except struct.error as e: # I guess more specific exception types were too much to ask for.
							if "<=" in str(e) or "out of range" in str(e):
								result = struct.pack("<" + field_type.PackFormat, field_type.InvalidValue)
							else:
								raise
			except Exception as e:
				raise Exception("Failed packing %s=%s - %s" % (field_name, kwargs[field_name], e))
			packResult.append(result)
		self._write(b''.join(packResult))


class FITIO:

	_sportMap = {
		ActivityType.Other: 0,
		ActivityType.Running: 1,
		ActivityType.Cycling: 2,
		ActivityType.MountainBiking: 2,
		ActivityType.Elliptical: 4,
		ActivityType.Swimming: 5,
		ActivityType.Gym: 10,
		ActivityType.Walking: 11,
		ActivityType.CrossCountrySkiing: 12,
		ActivityType.DownhillSkiing: 13,
		ActivityType.Snowboarding: 14,
		ActivityType.Rowing: 15,
		ActivityType.Hiking: 17,
		ActivityType.InlineSkating: 30,
		ActivityType.Climbing: 31,
		ActivityType.Skating: 33,
		ActivityType.Snowshoeing: 35,
		ActivityType.StandUpPaddling: 37,
		ActivityType.Surfing: 38,
		ActivityType.Kayaking: 41,
		ActivityType.WindSurfing: 43,
		ActivityType.KiteSurfing: 44,

	}
	_subSportMap = {
		'treadmill': ActivityType.Running,  # Run/Fitness Equipment
		'street': ActivityType.Running,  # Run
		'trail': ActivityType.Running,  # Run
		'track': ActivityType.Running,  # Run
		'spin': ActivityType.Cycling,  # Cycling
		'indoor_cycling': ActivityType.Cycling,  # Cycling/Fitness Equipment
		'road': ActivityType.Cycling,  # Cycling
		'mountain': ActivityType.Cycling,  # Cycling
		'downhill': ActivityType.Cycling,  # Cycling
		'recumbent': ActivityType.Cycling,  # Cycling
		'cyclocross': ActivityType.Cycling,  # Cycling
		'hand_cycling': ActivityType.Cycling,  # Cycling
		'track_cycling': ActivityType.Cycling,  # Cycling
		'indoor_rowing': ActivityType.Rowing,  # Fitness Equipment
		'elliptical': ActivityType.Elliptical,  # Fitness Equipment
		'stair_climbing': ActivityType.StrengthTraining,  # Fitness Equipment
		'lap_swimming': ActivityType.Swimming,  # Swimming
		'open_water': ActivityType.Swimming,  # Swimming
		'flexibility_training': ActivityType.Gym,  # Training
		'strength_training': ActivityType.StrengthTraining,  # Training
		'warm_up': ActivityType.Other,  # Tennis
		'match': ActivityType.Other,  # Tennis
		'exercise': ActivityType.Other,  # Tennis
		'challenge': ActivityType.Other,
		'indoor_skiing': ActivityType.DownhillSkiing,  # Fitness Equipment
		'cardio_training': ActivityType.StrengthTraining,  # Training
		'indoor_walking': ActivityType.Walking,  # Walking/Fitness Equipment
		'e_bike_fitness': ActivityType.Cycling,  # E-Biking
		'bmx': ActivityType.Cycling,  # Cycling
		'casual_walking': ActivityType.Walking,  # Walking
		'speed_walking': ActivityType.Walking,  # Walking
		'bike_to_run_transition': ActivityType.Other,  # Transition
		'run_to_bike_transition': ActivityType.Other,  # Transition
		'swim_to_bike_transition': ActivityType.Other,  # Transition
		'atv': ActivityType.Other,  # Motorcycling
		'motocross': ActivityType.Other,  # Motorcycling
		# This is voluntarly other as it removes specificity of Skiing or Snowboarding
		'backcountry': ActivityType.Other,  # Alpine Skiing/Snowboarding
		'resort': ActivityType.Other,  # Alpine Skiing/Snowboarding
		'rc_drone': ActivityType.Other,  # Flying
		'wingsuit': ActivityType.Other,  # Flying
		'whitewater': ActivityType.Other,  # Kayaking/Rafting
		'skate_skiing': ActivityType.CrossCountrySkiing,  # Cross Country Skiing
		'yoga': ActivityType.Yoga,  # Training
		'pilates': ActivityType.Yoga,  # Training
		'indoor_running': ActivityType.Running,  # Run
		'gravel_cycling': ActivityType.Cycling,  # Cycling
		'e_bike_mountain': ActivityType.Cycling,  # Cycling
		'commuting': ActivityType.Cycling,  # Cycling
		'mixed_surface': ActivityType.Cycling,  # Cycling
		'navigate': ActivityType.Other,
		'track_me': ActivityType.Other,
		'map': ActivityType.Other,
		'single_gas_diving': ActivityType.Other,  # Diving
		'multi_gas_diving': ActivityType.Other,  # Diving
		'gauge_diving': ActivityType.Other,  # Diving
		'apnea_diving': ActivityType.Other,  # Diving
		'apnea_hunting': ActivityType.Other,  # Diving
		'virtual_activity': ActivityType.Other,
		'obstacle': ActivityType.Other,  # Used for events where participants run, crawl through mud, climb over walls, etc.
		'all': ActivityType.Other,	
	}

	_reverseSportMap = {
		'running': ActivityType.Running,
		'cycling': ActivityType.Cycling,
		'transition': ActivityType.Other,  # Mulitsport transition
		'fitness_equipment': ActivityType.StrengthTraining,
		'swimming': ActivityType.Swimming,
		'basketball': ActivityType.Other,
		'soccer': ActivityType.Other,
		'tennis': ActivityType.Other,
		'american_football': ActivityType.Other,
		'training': ActivityType.Gym,
		'walking': ActivityType.Walking,
		'cross_country_skiing': ActivityType.CrossCountrySkiing,
		'alpine_skiing': ActivityType.DownhillSkiing,
		'snowboarding': ActivityType.Snowboarding,
		'rowing': ActivityType.Rowing,
		'mountaineering': ActivityType.Climbing,
		'hiking': ActivityType.Hiking,
		'multisport': ActivityType.Other,
		'paddling': ActivityType.Kayaking,
		'flying': ActivityType.Other,
		'e_biking': ActivityType.Cycling,
		'motorcycling': ActivityType.Other,
		'boating': ActivityType.Other,
		'driving': ActivityType.Other,
		'golf': ActivityType.Other,
		'hang_gliding': ActivityType.Other,
		'horseback_riding': ActivityType.Other,
		'hunting': ActivityType.Other,
		'fishing': ActivityType.Other,
		'inline_skating': ActivityType.InlineSkating,
		'rock_climbing': ActivityType.Climbing,
		'sailing': ActivityType.Other,
		'ice_skating': ActivityType.Skating,
		'sky_diving': ActivityType.Other,
		'snowshoeing': ActivityType.Snowshoeing,
		'snowmobiling': ActivityType.Other,
		'stand_up_paddleboarding': ActivityType.StandUpPaddling,
		'surfing': ActivityType.Surfing,
		'wakeboarding': ActivityType.Other,
		'water_skiing': ActivityType.Other,
		'kayaking': ActivityType.Kayaking,
		'rafting': ActivityType.Other,
		'windsurfing': ActivityType.WindSurfing,
		'kitesurfing': ActivityType.KiteSurfing,
		'tactical': ActivityType.Other,
		'jumpmaster': ActivityType.Other,
		'boxing': ActivityType.Other,
		'floor_climbing': ActivityType.Climbing,
		'all': ActivityType.Other
	}

	def _calculateCRC(bytestring, crc=0):
		crc_table = [0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401, 0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400]
		for byte in bytestring:
			tmp = crc_table[crc & 0xF]
			crc = (crc >> 4) & 0x0FFF
			crc = crc ^ tmp ^ crc_table[byte & 0xF]

			tmp = crc_table[crc & 0xF]
			crc = (crc >> 4) & 0x0FFF
			crc = crc ^ tmp ^ crc_table[(byte >> 4) & 0xF]
		return crc

	def _generateHeader(dataLength):
		# We need to call this once the final records are assembled and their length is known, to avoid having to seek back
		header_len = 12
		protocolVer = 16 # The FIT SDK code provides these in a very rounabout fashion
		profileVer = 810
		tag = ".FIT"
		return struct.pack("<BBHI4s", header_len, protocolVer, profileVer, dataLength, tag.encode("ASCII"))

	def Parse(fitData, activity=None):
		import fitparse
		from fitparse.records import DefinitionMessage, DataMessage

		# We create a new activity if it's not sent through that function
		activity = activity if activity else UploadedActivity()

		# We open the FIT binary stream and parse it
		fitfile = fitparse.FitFile(fitData)
		fitfile.parse()

		actividict = {
			"file_id": None,
			"waypoints": [],
			"laps": [],
			"sessions": [],
			"activity": None
		}

		# We fill the actividict
		for msg in fitfile._messages:
			# We check if the message is not an instance of DefinitionMessage (so it is a data message)
			if not isinstance(msg, DefinitionMessage) and msg != None :
				# We get the key/values of the message
				msg_data = msg.get_values()
				msg_data_keys = msg_data.keys()

				# We check for the records (waypoints) and the minimal information needed
				if (msg.name == "record" and "position_lat" in msg_data_keys and "position_long" in msg_data_keys and "timestamp" in msg_data_keys):
					# We append the waypoint to a waypoints list
					actividict["waypoints"].append({
						"timestamp": msg_data["timestamp"],
						"lat": msg_data["position_lat"] / SEMI_CIRCLE_CONST if msg_data["position_lat"] != None else None,
                		"lon": msg_data["position_long"] / SEMI_CIRCLE_CONST if msg_data["position_long"] != None else None,
						"altitude": msg_data.get("altitude") if "altitude" in msg_data_keys else msg_data.get("enhanced_altitude"),
						# The .get avoid the usage of conditions to ensure that the property exist in the dict
						# If it does not exist it returns None instead of crashing
						"hr": msg_data.get("heart_rate"),
						"cadence": msg_data.get("cadence"),
						"speed": msg_data.get("speed") if "speed" in msg_data_keys else msg_data.get("enhanced_speed"),
						"distance": msg_data.get("distance"),
						"temperature" : msg_data.get("temperature")
					})

				elif msg.name == "lap":
					# We just push the lap data as it is, because it seems that there is no different defs
					actividict["laps"].append(msg_data)

				elif msg.name == "session":
					# It seams that garmin fit files might have multiples "enhanced_speed" values in one sessions 
					# 		(perhaps it's only the case for the instinct solar watch)
					#
					# The problem is python dict can't have more than one key with the same name. 
					# 		So if an incorrect key/value is after the correct key/value in the "msg.as_dict()",
					# 		the incorrect one will be chosen
					#
					# So i made a little patch in case it is occuring for other devices.
					filtered_enhanced_speed_msg_data = {
						field["name"]: field["value"] for field in msg.as_dict()["fields"] 
						if not (
							field["name"] == "enhanced_avg_speed" and field["value"] == None
							or field["name"] == "enhanced_max_speed" and field["value"] == None
						)
					}
					actividict["sessions"].append(filtered_enhanced_speed_msg_data)

				elif msg.name == "activity":
					# according to fit documentations there must be only one activity record
					# For multisport the activity will be tagged multisport and the sessions will tell the subsports
					actividict["activity"] = msg_data

				elif msg.name == "file_id":
					# according to fit documentations there must be only one file_id record
					actividict["file_id"] = msg_data


		# We check if there is only one session for the moment
		if len(actividict["sessions"]) == 1:
			# We create a temp var for simplicity
			actividata = actividict["sessions"][0]

			# As the fit parsing library loves converting the digital data into string,
			#		i have to reverse that conversion or the dumper will crash
			reversed_key_val_garmin_product = {FIELD_TYPES["garmin_product"].values[gp_key]: gp_key for gp_key in FIELD_TYPES["garmin_product"].values.keys()}
			if actividict["file_id"].get("garmin_product") != None:
				if reversed_key_val_garmin_product.get(actividict["file_id"].get("garmin_product")) != None:
					# TODO make this more readable and more concise, but this needed to be hotfixed ASAP
					actividict["file_id"].update({"product": reversed_key_val_garmin_product.get(actividict["file_id"].get("garmin_product"))})

			#We init the Device object
			activity.Device = Device(
				manufacturer=actividict["file_id"].get("manufacturer"),
				# If there is a product we take it else we take the garmin_product or None
				product=actividict["file_id"].get("product",actividict["file_id"].get("garmin_product")),
				serial=actividict["file_id"].get("serial_number")
			)

			# And we fill the activity data
			activity.StartTime = actividata.get("start_time")
			activity.EndTime = actividata.get("timestamp")

			# Getting timezone from offset between the TS and local TS.
			# If local TS does not exist UTC is used
			act_data = actividict.get("activity")
			offset_in_minutes = 0
			if act_data != None:
				offset_in_minutes = int((act_data.get("local_timestamp",act_data.get("timestamp"))-act_data.get("timestamp")).total_seconds()/60)
			activity.TZ = pytz.FixedOffset(offset_in_minutes) if offset_in_minutes != 0 else pytz.utc

			# .get() fallback to "generic" to avoid a lot of conditional statement
			subsport_name = actividata.get("sub_sport", "generic")
			sport_name = actividata.get("sport", "generic")

			# .get() fallback to ActivityType.Other : Same purpose as above
			subsport_type = FITIO._subSportMap.get(subsport_name, ActivityType.Other)
			sport_type = FITIO._reverseSportMap.get(sport_name, ActivityType.Other)

			activity.Type = (subsport_type 
				if subsport_type != ActivityType.Other
				else sport_type
			)

			if activity.Name == None : 
				activity.Name = (subsport_name 
					if subsport_name != "generic" and subsport_name != "all"
					else (sport_name
						if sport_name != "generic" and sport_name != "all"
						else "Activity"
					)
				)


			timer_time_to_use = (
				# We should return the elapsed time but for unknown reason it could be 0 and could raise DivisionByZero.
				actividata.get("total_elapsed_time") if actividata.get("total_elapsed_time", 0) != 0 else
				# So just in case we try the timer time value and we also check if it is not 0.
				actividata.get("total_timer_time") if actividata.get("total_timer_time", 0) != 0 else
				# If they're both 0 it's time to try the delta between activity Start/End
				(activity.EndTime - activity.StartTime).total_seconds() if 
					(activity.EndTime - activity.StartTime).total_seconds() != 0 else 1
			)

			moving_time_to_use = (
				# We should return the timer time but for unknown reason it could be 0 and could raise DivisionByZero.
				actividata.get("total_timer_time") if actividata.get("total_timer_time", 0) != 0 else
				# So just in case we try the elapsed time value and we also check if it is not 0.
				actividata.get("total_elapsed_time") if actividata.get("total_elapsed_time", 0) != 0 else
				# If they're both 0 it's time to try the delta between activity Start/End
				(activity.EndTime - activity.StartTime).total_seconds() if 
					(activity.EndTime - activity.StartTime).total_seconds() != 0 else 1
			)
			
			activity.Stats = ActivityStatistics(
				distance=actividata.get("total_distance"), 
				timer_time=timer_time_to_use, 
				# The *3.6 is the m/s to Km/h conversion.
				# Also implemented the usage of "enhanced values" because Garmin prefer using them.
				# Also made an last resort fallback to recalculate the speed if all values are None
				#		and the "filtered_enhanced_speed_msg_data" patch can't get the speed.
				# It's better than returning a 0 Km/h speed to the user.
				# The major drawback is that the max speed will be equal to the average one.
                moving_time=moving_time_to_use,
				avg_speed=(
					actividata.get("avg_speed") if actividata.get("avg_speed") != None else 
					actividata.get("enhanced_avg_speed") if actividata.get("enhanced_avg_speed") != None else 
					actividata.get("total_distance",0) / time_to_use) *3.6, 
				max_speed=(
					actividata.get("max_speed") if actividata.get("max_speed") != None else
					actividata.get("enhanced_max_speed") if actividata.get("enhanced_max_speed") != None else 
					actividata.get("total_distance",0) / time_to_use) *3.6, 
				avg_hr=actividata.get("avg_heart_rate"), 
				max_hr=actividata.get("max_heart_rate"), 
				avg_run_cadence=actividata.get("avg_running_cadence"), 
				max_run_cadence=actividata.get("max_running_cadence"),
				strides=actividata.get("total_strides"),
				kcal=actividata.get("total_calories"),
				avg_temp=actividata.get("avg_temperature"),
				avg_power=actividata.get("avg_power") if actividata.get("avg_power") !=0 else None
			)
		else:
			# TODO handle multiple sessions
			raise NotImplementedError

		# Garmin, on their connect app, can create a manual activity with the same Start/End Time but with a non 0 timer_time
		if activity.StartTime == activity.EndTime and activity.Stats.TimerTime.Value != 0:
			# In that case we update the EndTime to avoid a 0 duration error during the sanity check.
			activity.EndTime = activity.StartTime + timedelta(seconds=activity.Stats.TimerTime.Value)

		# Adding pseudo lap with the start and the end of the activity
		# Because there is no lap in polar fit files and they are needed to store the waypoints
		if len(actividict["laps"]) == 0:
			actividict["laps"].append({
				"start_time":activity.StartTime,
				"timestamp":activity.EndTime
			})

		# Adding a lap because it seems that polar creates laps only every kms.
		# So every wp between last round kilometer and the end of the activity are oprhans
		# And they are not "activitified" so they wont appear in other services.
		if len(actividict["laps"]) != 0 and len(actividict["waypoints"]) != 0:
			last_wp = actividict["waypoints"][-1]
			last_lap = actividict["laps"][-1]
			if last_wp.get("timestamp") > last_lap.get("timestamp"):
				actividict["laps"].append({
					"start_time":last_lap.get("timestamp") + timedelta(seconds=1),
					"timestamp":last_wp.get("timestamp")+ timedelta(seconds=1)
				})

		# Time to fill the activity laps (and waypoints)
		activity.Laps = [
			# A bit like the SELECT SQL clause
			Lap(
				startTime=lapData["start_time"], 
				endTime=lapData["timestamp"],
				stats=activity.Stats if len(actividict["laps"]) == 1 else None,
				waypointList=[
					# SELECT
					Waypoint(
						timestamp=wp.get("timestamp"),
						location=Location(
							lat=wp.get("lat"),
							lon=wp.get("lon"),
							alt=wp.get("altitude")
						),
						hr=wp.get("hr"),
						runCadence=wp.get("cadence"),
						speed=wp.get("speed"),
						distance=wp.get("distance"),
						temp=wp.get("temperature")
					)
					# FROM actividict["waypoints"] as wp
					for wp in actividict["waypoints"]
					# WHERE the wp timestamp is between the lap start and end timestamps.
					if (wp.get("timestamp") >= lapData["start_time"] and wp.get("timestamp") < lapData["timestamp"])
				]
			)
			# FROM actividict["laps"]
			for lapData in actividict["laps"]
		]

		# I set the GPS and the Stationary as they are mandatory for the Sanity Check to succeed. 
		activity.GPS=len(actividict["waypoints"]) != 0
		activity.Stationary=not len(actividict["waypoints"]) != 0

    
		# It is sure that fit send all its timestamps in UCT.
		# So i have to make them all non TZ naives
		# 		else adjustTZ() will assume that the naives DTs are already on local TZ 
		# 		wich leads to time shifts later in the processing. 
		# 		For example :
		#				With a TZ=FixedOffset(120)
		#				A real 2020/01/01 14:30 (In UTC but naive) 
		# 				Can become 2020/01/01 14:30+02:00 after AdjustTZ() (Equivalent to 12:30+00:00) 
		# 				So the FIT dumper will assume it is : 2020/01/01 12:30 after putting it in UTC and making it naive again.
		activity.StartTime = activity.StartTime.replace(tzinfo=pytz.utc)
		activity.EndTime = activity.EndTime.replace(tzinfo=pytz.utc)
		for lap in activity.Laps:
			lap.StartTime = lap.StartTime.replace(tzinfo=pytz.utc)
			lap.EndTime = lap.EndTime.replace(tzinfo=pytz.utc)
			for wp in lap.Waypoints:
				wp.Timestamp = wp.Timestamp.replace(tzinfo=pytz.utc)
		
		
		activity.AdjustTZ()

    
		activity.CheckSanity()

		return activity

	def Dump(act, drop_pauses=False):
		def toUtc(ts):
			if ts.tzinfo:
				return ts.astimezone(pytz.utc).replace(tzinfo=None)
			else:
				raise ValueError("Need TZ data to produce FIT file")
		fmg = FITMessageGenerator()

		# As the keys are the IDs and not the names.
		# So it is usefull to reverse keys and values
		#add decathtlon manufacturer in list
		FIELD_TYPES["manufacturer"].values[310] = "decathlon"
		reversed_key_val_manufacturer = {FIELD_TYPES["manufacturer"].values[man_key]: man_key for man_key in FIELD_TYPES["manufacturer"].values.keys()}

		if act.Device != None:
			creatorInfo = {
				# If we can't reverse the manufacturer (because of an old profile), i put the dev Manufacturer
				"manufacturer": reversed_key_val_manufacturer.get(act.Device.Manufacturer, FITManufacturer.DEVELOPMENT),
				# Looks like it can be anything we want but must be set so fallback to 0 if None
				"serial_number": act.Device.Serial if act.Device.Serial != None else 0,
				# Same here but it was previously 15706 by default and it worked well
				"product": act.Device.Product if act.Device.Product != None else 15706
			}
			devInfo = {
				"manufacturer": reversed_key_val_manufacturer.get(act.Device.Manufacturer, FITManufacturer.DEVELOPMENT),
				"product": act.Device.Product if act.Device.Product != None else 15706,
				"device_index": 0
			}

		else:
			creatorInfo = {
				# If we can't reverse the manufacturer (because of an old profile), i put the dev Manufacturer
				"manufacturer": FITManufacturer.DEVELOPMENT,
				# Looks like it can be anything we want but must be set so fallback to 0 if None
				"serial_number": 0,
				# Same here but it was previously 15706 by default and it worked well
				"product": 15706
			}
			devInfo = {
				"manufacturer": FITManufacturer.DEVELOPMENT,
				"product": 15706,
				"device_index": 0
			}
		

		################################ 
		# Just keeping the old Device management in case of bug
		################################
		# if act.Device:
		# 	# GC can get along with out this, Strava needs it
		# 	devId = DeviceIdentifier.FindEquivalentIdentifierOfType(DeviceIdentifierType.FIT, act.Device.Identifier)
		# 	if devId:
		# 		creatorInfo = {
		# 			"manufacturer": devId.Manufacturer,
		# 			"product": devId.Product,
		# 		}
		# 		devInfo = {
		# 			"manufacturer": devId.Manufacturer,
		# 			"product": devId.Product,
		# 			"device_index": 0 # Required for GC
		# 		}
		# 		if act.Device.Serial:
		# 			creatorInfo["serial_number"] = int(act.Device.Serial) # I suppose some devices might eventually have alphanumeric serial #s
		# 			devInfo["serial_number"] = int(act.Device.Serial)
		# 		if act.Device.VersionMajor is not None:
		# 			assert act.Device.VersionMinor is not None
		# 			devInfo["software_version"] = act.Device.VersionMajor + act.Device.VersionMinor / 100

		fmg.GenerateMessage("file_id", type=FITFileType.Activity, time_created=toUtc(act.StartTime), **creatorInfo)
		fmg.GenerateMessage("device_info", **devInfo)

		sport = FITIO._sportMap[act.Type] if act.Type in FITIO._sportMap else 0
		subSport = FITIO._subSportMap[act.Type] if act.Type in FITIO._subSportMap else 0

		session_stats = {
			# "total_elapsed_time": act.EndTime - act.StartTime,
		}

		# FIT doesn't have different fields for this, but it does have a different interpretation - we eventually need to divide by two in the running case.
		# Further complicating the issue is that most sites don't differentiate the two, so they'll end up putting the run cadence back into the bike field.
		use_run_cadence = act.Type in [ActivityType.Running, ActivityType.Walking, ActivityType.Hiking]
		def _resolveRunCadence(bikeCad, runCad):
			nonlocal use_run_cadence
			if use_run_cadence:
				return runCad if runCad is not None else (bikeCad if bikeCad is not None else None)
			else:
				return bikeCad

		def _mapStat(dict, key, value):
			if value is not None:
				dict[key] = value

        # Yeah it's confusing but fit timer_time is time without pause and it is corresponding to hub moving time
        #   fit's total_elapsed_time includes pauses
		_mapStat(session_stats, "total_timer_time", act.Stats.MovingTime.asUnits(ActivityStatisticUnit.Seconds).Value)
		_mapStat(session_stats, "total_elapsed_time", act.Stats.TimerTime.asUnits(ActivityStatisticUnit.Seconds).Value)
		_mapStat(session_stats, "total_distance", act.Stats.Distance.asUnits(ActivityStatisticUnit.Meters).Value)
		_mapStat(session_stats, "total_calories", act.Stats.Energy.asUnits(ActivityStatisticUnit.Kilocalories).Value)
		_mapStat(session_stats, "avg_speed", act.Stats.Speed.asUnits(ActivityStatisticUnit.MetersPerSecond).Average)
		_mapStat(session_stats, "max_speed", act.Stats.Speed.asUnits(ActivityStatisticUnit.MetersPerSecond).Max)
		_mapStat(session_stats, "avg_heart_rate", act.Stats.HR.Average)
		_mapStat(session_stats, "max_heart_rate", act.Stats.HR.Max)
		_mapStat(session_stats, "avg_cadence", _resolveRunCadence(act.Stats.Cadence.Average, act.Stats.RunCadence.Average))
		_mapStat(session_stats, "max_cadence", _resolveRunCadence(act.Stats.Cadence.Max, act.Stats.RunCadence.Max))
		_mapStat(session_stats, "avg_power", act.Stats.Power.Average)
		_mapStat(session_stats, "max_power", act.Stats.Power.Max)
		_mapStat(session_stats, "total_ascent", act.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Gain)
		_mapStat(session_stats, "total_descent", act.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Loss)
		_mapStat(session_stats, "avg_altitude", act.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Average)
		_mapStat(session_stats, "max_altitude", act.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Max)
		_mapStat(session_stats, "min_altitude", act.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Min)
		_mapStat(session_stats, "avg_temperature", act.Stats.Temperature.asUnits(ActivityStatisticUnit.DegreesCelcius).Average)
		_mapStat(session_stats, "max_temperature", act.Stats.Temperature.asUnits(ActivityStatisticUnit.DegreesCelcius).Max)

		inPause = False
		for lap in act.Laps:

			# Little trick to handle static activities mostly for Strava
			# If there not at least a record msg, Strava will say empty upload ...
			if len(lap.Waypoints) == 0:
				rec_contents = {"timestamp": toUtc(act.StartTime)}
				fmg.GenerateMessage("record", **rec_contents)

			for wp in lap.Waypoints:
				if wp.Type == WaypointType.Resume and inPause:
					fmg.GenerateMessage("event", timestamp=toUtc(wp.Timestamp), event=FITEvent.Timer, event_type=FITEventType.Start)
					inPause = False
				elif wp.Type == WaypointType.Pause and not inPause:
					fmg.GenerateMessage("event", timestamp=toUtc(wp.Timestamp), event=FITEvent.Timer, event_type=FITEventType.Stop)
					inPause = True
				if inPause and drop_pauses:
					continue

				rec_contents = {"timestamp": toUtc(wp.Timestamp)}
				if wp.Location:
					rec_contents.update({"position_lat": wp.Location.Latitude, "position_long": wp.Location.Longitude})
					rec_contents.update({"altitude": wp.Location.Altitude})
				if wp.HR is not None:
					rec_contents.update({"heart_rate": wp.HR})
				if wp.RunCadence is not None:
					# Here we asume we already have the Run_Cadence as batch of 1 left and 1 right step (As the fit ask to)
					rec_contents.update({"cadence": wp.RunCadence})
				if wp.Cadence is not None:
					rec_contents.update({"cadence": wp.Cadence})
				if wp.Power is not None:
					rec_contents.update({"power": wp.Power})
				if wp.Temp is not None:
					rec_contents.update({"temperature": wp.Temp})
				if wp.Calories is not None:
					rec_contents.update({"calories": wp.Calories})
				if wp.Distance is not None:
					rec_contents.update({"distance": wp.Distance})
				if wp.Speed is not None:
					rec_contents.update({"speed": wp.Speed})
				fmg.GenerateMessage("record", **rec_contents)
			# Man, I love copy + paste and multi-cursor editing
			# But seriously, I'm betting that, some time down the road, a stat will pop up in X but not in Y, so I won't feel so bad about the C&P abuse
			lap_stats = {}
			_mapStat(lap_stats, "total_elapsed_time", lap.EndTime - lap.StartTime)
			_mapStat(lap_stats, "total_moving_time", lap.Stats.MovingTime.asUnits(ActivityStatisticUnit.Seconds).Value)
			_mapStat(lap_stats, "total_timer_time", lap.Stats.TimerTime.asUnits(ActivityStatisticUnit.Seconds).Value)
			_mapStat(lap_stats, "total_distance", lap.Stats.Distance.asUnits(ActivityStatisticUnit.Meters).Value)
			_mapStat(lap_stats, "total_calories", lap.Stats.Energy.asUnits(ActivityStatisticUnit.Kilocalories).Value)
			_mapStat(lap_stats, "avg_speed", lap.Stats.Speed.asUnits(ActivityStatisticUnit.MetersPerSecond).Average)
			_mapStat(lap_stats, "max_speed", lap.Stats.Speed.asUnits(ActivityStatisticUnit.MetersPerSecond).Max)
			_mapStat(lap_stats, "avg_heart_rate", lap.Stats.HR.Average)
			_mapStat(lap_stats, "max_heart_rate", lap.Stats.HR.Max)
			_mapStat(lap_stats, "avg_cadence", _resolveRunCadence(lap.Stats.Cadence.Average, lap.Stats.RunCadence.Average))
			_mapStat(lap_stats, "max_cadence", _resolveRunCadence(lap.Stats.Cadence.Max, lap.Stats.RunCadence.Max))
			_mapStat(lap_stats, "avg_power", lap.Stats.Power.Average)
			_mapStat(lap_stats, "max_power", lap.Stats.Power.Max)
			_mapStat(lap_stats, "total_ascent", lap.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Gain)
			_mapStat(lap_stats, "total_descent", lap.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Loss)
			_mapStat(lap_stats, "avg_altitude", lap.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Average)
			_mapStat(lap_stats, "max_altitude", lap.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Max)
			_mapStat(lap_stats, "min_altitude", lap.Stats.Elevation.asUnits(ActivityStatisticUnit.Meters).Min)
			_mapStat(lap_stats, "avg_temperature", lap.Stats.Temperature.asUnits(ActivityStatisticUnit.DegreesCelcius).Average)
			_mapStat(lap_stats, "max_temperature", lap.Stats.Temperature.asUnits(ActivityStatisticUnit.DegreesCelcius).Max)

			# These are some really... stupid lookups.
			# Oh well, futureproofing.
			lap_stats["intensity"] = ({
					LapIntensity.Active: FITLapIntensity.Active,
					LapIntensity.Rest: FITLapIntensity.Rest,
					LapIntensity.Warmup: FITLapIntensity.Warmup,
					LapIntensity.Cooldown: FITLapIntensity.Cooldown,
				})[lap.Intensity]
			lap_stats["lap_trigger"] = ({
					LapTriggerMethod.Manual: FITLapTriggerMethod.Manual,
					LapTriggerMethod.Time: FITLapTriggerMethod.Time,
					LapTriggerMethod.Distance: FITLapTriggerMethod.Distance,
					LapTriggerMethod.PositionStart: FITLapTriggerMethod.PositionStart,
					LapTriggerMethod.PositionLap: FITLapTriggerMethod.PositionLap,
					LapTriggerMethod.PositionWaypoint: FITLapTriggerMethod.PositionWaypoint,
					LapTriggerMethod.PositionMarked: FITLapTriggerMethod.PositionMarked,
					LapTriggerMethod.SessionEnd: FITLapTriggerMethod.SessionEnd,
					LapTriggerMethod.FitnessEquipment: FITLapTriggerMethod.FitnessEquipment,
				})[lap.Trigger]
			fmg.GenerateMessage("lap", timestamp=toUtc(lap.EndTime), start_time=toUtc(lap.StartTime), event=FITEvent.Lap, event_type=FITEventType.Start, sport=sport, **lap_stats)


		# These need to be at the end for Strava
		fmg.GenerateMessage("session", timestamp=toUtc(act.EndTime), start_time=toUtc(act.StartTime), sport=sport, sub_sport=subSport, event=FITEvent.Timer, event_type=FITEventType.Start, **session_stats)
		fmg.GenerateMessage("activity", timestamp=toUtc(act.EndTime), local_timestamp=act.EndTime.replace(tzinfo=None), num_sessions=1, type=FITActivityType.GENERIC, event=FITEvent.Activity, event_type=FITEventType.Stop)

		records = fmg.GetResult()
		header = FITIO._generateHeader(len(records))
		crc = FITIO._calculateCRC(records, FITIO._calculateCRC(header))
		return header + records + struct.pack("<H", crc)
