from tapiriik.database import db

db.connections.create_index([("ExternalID",1), ("Service",1)], background=True)
db.activity_records.create_index("UserID", background=True)
db.users.create_index([("ConnectedServices.ID",1), ("ConnectedServices.Service",1)], background=True)

