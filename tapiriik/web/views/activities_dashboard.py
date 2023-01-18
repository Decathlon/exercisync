from django.shortcuts import render, redirect
from django.http import HttpResponse
from tapiriik.database import db
from tapiriik.settings import WITHDRAWN_SERVICES
import json
import datetime
import os

def _is_migration_finished():
    return os.getenv("MIGRATION_FINISHED", "False").lower() in ("true", "1")

def activities_dashboard(req):
    if not req.user or _is_migration_finished():
        return redirect("/")
    return render(req, "activities-dashboard.html")

def activities_fetch_json(req):
    if not req.user:
        return HttpResponse(status=403)

    retrieve_fields = [
        "Activities.Prescence",
        "Activities.Abscence",
        "Activities.Type",
        "Activities.Name",
        "Activities.StartTime",
        "Activities.EndTime",
        "Activities.Private",
        "Activities.Stationary",
        "Activities.FailureCounts"
    ]
    activityRecords = db.activity_records.find_one({"UserID": req.user["_id"]}, dict([(x, 1) for x in retrieve_fields]))
    if not activityRecords:
        return HttpResponse("[]", content_type="application/json")
    cleanedRecords = []
    for activity in activityRecords["Activities"]:
        activity["Prescence"] = list(activity.get("Prescence").keys())
        activity["Abscence"] = list(activity.get("Abscence").keys())
        # Strip down the record since most of this info isn't displayed
        # for presence in activity["Prescence"]:
        #     del activity["Prescence"][presence]["Exception"]
        # for abscence in activity["Abscence"]:
        #     if activity["Abscence"][abscence]["Exception"]:
        #         del activity["Abscence"][abscence]["Exception"]["InterventionRequired"]
        #         del activity["Abscence"][abscence]["Exception"]["ClearGroup"]
        # # Don't really need these seperate at this point
        # activity["Prescence"].update(activity["Abscence"])
        # for svc in WITHDRAWN_SERVICES:
        #     if svc in activity["Prescence"]:
        #         del activity["Prescence"][svc]
        # del activity["Abscence"]

        diff_date = int((activity['EndTime'] - activity["StartTime"]).total_seconds() / 60.0)
        period = str(diff_date) + " minutes"
        activity['readable_date'] = activity["StartTime"].strftime("%Y-%m-%d")
        activity['period'] = period
        cleanedRecords.append(activity)

    dthandler = lambda obj: obj.isoformat() if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date) else None

    return HttpResponse(json.dumps(cleanedRecords, default=dthandler), content_type="application/json")