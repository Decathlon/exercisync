from tapiriik.auth import User
from tapiriik.sync import Sync
from tapiriik.services import Service
from django.shortcuts import render, redirect
from django import forms
from django.http import HttpResponse
import json

Sync = Sync()

def config_save(req, service):
    if not req.user:
        return HttpResponse(status=403)

    conn = User.GetConnectionRecord(req.user, service)
    if not conn:
        return HttpResponse(status=404)
    conn.SetConfiguration(json.loads(req.POST["config"]))
    Sync.SetNextSyncIsExhaustive(req.user, True) # e.g. if they opted to sync private activities.
    return HttpResponse()


def config_flow_save(req, service):
    if not req.user:
        return HttpResponse(status=403)
    conns = User.GetConnectionRecordsByUser(req.user)
    if service not in [x.Service.ID for x in conns]:
        return HttpResponse(status=404)
    sourceSvc = [x for x in conns if x.Service.ID == service][0]
    #  the JS doesn't resolve the flow exceptions, it just passes in the expanded config flags for the edited service (which will override other flowexceptions)
    flowFlags = json.loads(req.POST["flowFlags"])
    for destSvc in [x for x in conns if x.Service.ID != service]:
        User.SetFlowException(req.user, sourceSvc, destSvc, destSvc.Service.ID in flowFlags["forward"], None)
    Sync.SetNextSyncIsExhaustive(req.user, True)  # to pick up any activities left behind
    return HttpResponse()


class DropboxConfigForm(forms.Form):
    path = forms.CharField(label="Dropbox sync path")
    syncUntagged = forms.BooleanField(label="Sync untagged activities", required=False)


def dropbox(req):
    if not req.user:
        return HttpResponse(status=403)
    conn = User.GetConnectionRecord(req.user, "dropbox")
    if req.method == "POST":
        form = DropboxConfigForm(req.POST)
        if form.is_valid():
            conn.SetConfiguration({"SyncRoot": form.cleaned_data['path'], "UploadUntagged": form.cleaned_data['syncUntagged']})
            return redirect("dashboard")
    else:
        conf = conn.GetConfiguration()
        form = DropboxConfigForm({"path": conf["SyncRoot"], "syncUntagged": conf["UploadUntagged"]})
    return render(req, "config/dropbox.html", {"form": form})


class AerobiaConfigForm(forms.Form):
    pass

def aerobia(req):
    if not req.user:
        return HttpResponse(status=403)
    conn = User.GetConnectionRecord(req.user, "aerobia")

    config = conn.GetConfiguration()
    gearRules = config["gearRules"] if "gearRules" in config else []
    props = {
        'aerobiaId': conn.ExternalID,
        'userToken': conn.Authorization["OAuthToken"],
        'sportTypes': conn.Service.SupportedActivities,
        'config': {
                'gearRules': gearRules
            }
    }

    if req.method == "POST":
        form = AerobiaConfigForm(req.POST)
        if form.is_valid():
            configRaw = req.POST.get('config')
            config = json.loads(configRaw)
            conn.SetConfiguration(config)
            return redirect("dashboard")

    return render(req, "config/aerobia.html", {'props': props})
