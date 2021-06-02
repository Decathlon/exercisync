# Stationary activities
Stationary activities do not have sensor data, just summary data. They are handled in the same structures as regular activities. Stationary activities must be marked as such via `Activity.Stationary=[True|False]`. This will disable checks for minimum waypoint count (etc.) and is used by some services in determining the appropriate upload method. Activities should be marked as soon as possible (i.e. if it can be determined in `DownloadActivityList`), and must be set before the time the activity is sanity checked (after `DownloadActivity`). Otherwise, the flag should remain at the default state (`Stationary = None`) to allow effective coalescing when deduplicating activities.

If a service does not support stationary activities, set `ReceivesStationaryActivities = False`.

# Non-GPS activities
Unlike stationary activities, non-GPS (`activity.GPS = False`) activities can still have sensor data recorded in Waypoints (and therefore should not be flagged as Stationary). Services should be written to allow for uploading Waypoints without Location, although they may ignore such waypoints if the remote site does not support them (e.g. GPX export). 

If the service does not support non-GPS activities, set `ReceivesNonGPSActivitiesWithOtherSensorData = False`.

# Activities debuging
The `Activity` object and all it's components like `ActivityStatistics` or `Lap` have an `asdict()` method.
This method avoid returning the `__repr__` or the `__str__` of the object wich looks often like this :

```python
# some json ...
"Laps": [ <tapiriik.service.interchange.Lap.SOME_ID>],
"Stats": [ <tapiriik.service.interchange.ActivityStatistics.SOME_OTHER_ID>]
# ... some more json
```

You will instead have something like this :

```python
# some json ...
"Laps": [{
    "StartTime": datetime(...),
    "EndTime": datetime(...),
    "Stats": [
        "Distance": {
            "Value": 100, # some distance value
            "Unit": "m"
        },
        "Speed": {
            "Max": 20, # some max speed value
            "Average": 12, # and so on
            "Unit": "km/h"
        }
    ],
    # etc.
}],
"Stats": [
    "Distance": {
        "Value": 100, # some distance value
        "Unit": "m"
    },
    "Speed": {
        "Max": 20, # some max speed value
        "Average": 12, # and so on
        "Unit": "km/h"
    }
]
# ... some more json
```

With this you can both print the activity to the console and print it to a file thanks to the JSON library.
```python
# Logging to the console
import logging
logging.info(activity.asdict())

# Printing into a file
import json
with open("MY_FILE_NAME.json", "w") as MY_FILE: 
    MY_FILE.write(json.dumps(activity.asdict(), indent=4, default=str)
```

# [Back to summary](000-summary.md)
## [Back to conception summary](010-conception.md)
