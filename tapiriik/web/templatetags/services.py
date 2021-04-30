from django import template
from tapiriik.services import Service, ServiceRecord
from tapiriik.database import db
register = template.Library()


@register.filter(name="svc_ids")
def IDs(value):
    return [x["Service"] for x in value]


# This is kept in case of we need to get back
@register.filter(name="svc_providers_except")
def exceptSvc(value):
    connections = [y["Service"] for y in value]
    return [x for x in Service.List() if x.ID not in connections]

# This is kept in case of we need to get back
@register.filter(name="svc_populate_conns")
def fullRecords(conns):
    return [ServiceRecord(x) for x in db.connections.find({"_id": {"$in": [x["ID"] for x in conns]}})]




@register.filter(name="svc_populate_output_conns")
def outputRecords(conns):
    return [ServiceRecord(x) for x in db.connections.find({"_id": {"$in": [x["ID"] for x in conns]}}) if not ServiceRecord(x).Service.SuppliesActivities]


@register.filter(name="svc_output_providers_except")
def exceptOutputSvc(value):
    connections = [y["Service"] for y in value]
    return [x for x in Service.List() if x.ID not in connections and not x.SuppliesActivities]


@register.filter(name="svc_populate_input_conns")
def inputRecords(conns):
    return [ServiceRecord(x) for x in db.connections.find({"_id": {"$in": [x["ID"] for x in conns]}}) if ServiceRecord(x).Service.SuppliesActivities]


@register.filter(name="svc_input_providers_except")
def exceptInputSvc(value):
    connections = [y["Service"] for y in value]
    return [x for x in Service.List() if x.ID not in connections and x.SuppliesActivities]