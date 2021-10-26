from tapiriik.database import db

db.connections.create_index([("ExternalID",1), ("Service",1)], background=True)
db.activity_records.create_index("UserID", background=True)

