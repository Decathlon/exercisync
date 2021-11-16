from tapiriik.services import Service
from tapiriik.auth import User
from tapiriik.sync import Sync
from tapiriik.settings import SITE_VER, PP_WEBSCR, PP_BUTTON_ID, SOFT_LAUNCH_SERVICES, DISABLED_SERVICES, CONNECTION_SERVICES, WITHDRAWN_SERVICES, CELEBRATION_MODES, VUE_URL, DECAT_CLUB_ENV_LINK
from tapiriik.database import db
from datetime import datetime
from random import randint
import json

def providers(req):
    return {"service_providers": Service.List()}

def config(req):
    in_diagnostics = "diagnostics" in req.path
    _sync = Sync()
    return {
        "config": {
            "minimumSyncInterval": _sync.MinimumSyncInterval.seconds,
            "siteVer": SITE_VER,
            "pp": {
                "url": PP_WEBSCR,
                "buttonId": PP_BUTTON_ID
            },
            "connection_services": CONNECTION_SERVICES,
            "soft_launch": SOFT_LAUNCH_SERVICES,
            "disabled_services": DISABLED_SERVICES,
            "withdrawn_services": WITHDRAWN_SERVICES,
            "in_diagnostics": in_diagnostics
        },
        "hidden_infotips": req.COOKIES.get("infotip_hide", None)
    }

def user(req):
    return {"user":req.user}

def js_bridge(req):
    serviceInfo = {}

    for svc in Service.List():
        if svc.ID in WITHDRAWN_SERVICES:
            continue
        if req.user is not None:
            svcRec = User.GetConnectionRecord(req.user, svc.ID)  # maybe make the auth handler do this only once?
        else:
            svcRec = None
        info = {
            "DisplayName": svc.DisplayName,
            "DisplayAbbreviation": svc.DisplayAbbreviation,
            "AuthenticationType": svc.AuthenticationType,
            "UsesExtendedAuth": svc.RequiresExtendedAuthorizationDetails,
            "AuthorizationURL": svc.UserAuthorizationURL,
            "NoFrame": svc.AuthenticationNoFrame,
            "ReceivesActivities": svc.ReceivesActivities,
            "Configurable": svc.Configurable,
            "RequiresConfiguration": False  # by default
        }
        if svcRec:
            if svc.Configurable:
                if svc.ID == "dropbox":  # dirty hack alert, but better than dumping the auth details in their entirety
                    info["AccessLevel"] = "full" if svcRec.Authorization["Full"] else "normal"
                    info["RequiresConfiguration"] = svc.RequiresConfiguration(svcRec)
            info["Config"] = svcRec.GetConfiguration()
            info["HasExtendedAuth"] = svcRec.HasExtendedAuthorizationDetails()
            info["PersistedExtendedAuth"] = svcRec.HasExtendedAuthorizationDetails(persisted_only=True)
            info["ExternalID"] = svcRec.ExternalID
        info["BlockFlowTo"] = []
        info["Connected"] = svcRec is not None
        serviceInfo[svc.ID] = info
    if req.user is not None:
        flowExc = User.GetFlowExceptions(req.user)
        for exc in flowExc:
            if exc["Source"]["Service"] not in serviceInfo or exc["Target"]["Service"] not in serviceInfo:
                continue # Withdrawn services
            if "ExternalID" in serviceInfo[exc["Source"]["Service"]] and exc["Source"]["ExternalID"] != serviceInfo[exc["Source"]["Service"]]["ExternalID"]:
                continue  # this is an old exception for a different connection
            if "ExternalID" in serviceInfo[exc["Target"]["Service"]] and exc["Target"]["ExternalID"] != serviceInfo[exc["Target"]["Service"]]["ExternalID"]:
                continue  # same as above
            serviceInfo[exc["Source"]["Service"]]["BlockFlowTo"].append(exc["Target"]["Service"])
    return {"js_bridge_serviceinfo": json.dumps(serviceInfo)}


def stats(req):
    return {"stats": db.stats.find_one()}


def celebration_mode(req):
    active_config = None
    now = datetime.now()
    for date_range, config in CELEBRATION_MODES.items():
        if date_range[0] <= now and date_range[1] >= now:
            active_config = config
            break
    return {"celebration_mode": active_config}


def device_support(req):
    device_support = "web"
    if 'device_support' in req.COOKIES:
        device_support = req.COOKIES.get('device_support')
    else:
        if 'mobile' in req.GET:
            if req.GET['mobile'] is True or req.GET['mobile'] == 1 or req.GET['mobile'] == '1' or req.GET['mobile'] == 'true':
                device_support = 'mobile'
    return {"device_support": device_support}


def is_user_from_dkt_club(req):
    COOKIE_NAME = "is_user_from_dkt_club"

    is_user_from_dkt_club = False
    if COOKIE_NAME in req.COOKIES:
        is_user_from_dkt_club = req.COOKIES.get(COOKIE_NAME)
    else:
        if 'utm_source' in req.GET:
            if req.GET['utm_source'] == "decatclub":
                is_user_from_dkt_club = True
    return {COOKIE_NAME: is_user_from_dkt_club}


def background_use(req):
    return {'background_use': randint(1, 5)}


def vue_link(req):
    return {"VUE_URL": VUE_URL}

def decat_club_env_link(req):
    return {"DECAT_CLUB_ENV_LINK": DECAT_CLUB_ENV_LINK}