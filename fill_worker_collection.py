from tapiriik.database import db
from datetime import datetime, timedelta

now_less_one_year = datetime.now()-timedelta(days=365)

for i in range(52560):
    heartbeat_time = now_less_one_year+timedelta(minutes=i*10)
    db.sync_workers.insert_one(
        {
            'Host': 'junk', 
            'Process': i, 
            'Heartbeat': heartbeat_time, 
            'Index': 0, 
            'Startup': heartbeat_time-timedelta(minutes=1), 
            'State': 'ready', 
            'Version': b'junk', 
            'User': None if i%10 != 0 else "junk"
        })
