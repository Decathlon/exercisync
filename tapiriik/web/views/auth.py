from tapiriik.services.service_record import ServiceRecord
from django.http import HttpResponse
from django.http.response import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from tapiriik.services import Service
from tapiriik.auth import User
import json
import logging
from pymongo.errors import WriteError


def auth_login(req, service):
    return redirect("/#/auth/%s" % service)


@require_POST
def auth_login_ajax(req, service):
    res = auth_do(req, service)
    return HttpResponse(json.dumps({"success": res == True, "result": res}), content_type='application/json')


def auth_do(req, service):
    svc = Service.FromID(service)
    from tapiriik.services.api import APIException
    try:
        if svc.RequiresExtendedAuthorizationDetails:
            uid, authData, extendedAuthData = svc.Authorize(req.POST["username"], req.POST["password"])
        else:
            uid, authData = svc.Authorize(req.POST["username"], req.POST["password"])
    except APIException as e:
        if e.UserException is not None:
            return {"type": e.UserException.Type, "extra": e.UserException.Extra}
        return False
    if authData is not None:
        serviceRecord = Service.EnsureServiceRecordWithAuth(svc, uid, authData, extendedAuthDetails=extendedAuthData if svc.RequiresExtendedAuthorizationDetails else None, persistExtendedAuthDetails=bool(req.POST.get("persist", None)))
        # auth by this service connection
        existingUser = User.AuthByService(serviceRecord)
        # only log us in as this different user in the case that we don't already have an account
        if existingUser is not None and req.user is None:
            User.Login(existingUser, req)
        else:
            User.Ensure(req)
        # link service to user account, possible merge happens behind the scenes (but doesn't effect active user)
        User.ConnectService(req.user, serviceRecord)
        return True
    return False

@require_POST
def auth_persist_extended_auth_ajax(req, service):
    svc = Service.FromID(service)
    svcId = [x["ID"] for x in req.user["ConnectedServices"] if x["Service"] == svc.ID]
    if len(svcId) == 0:
        return HttpResponse(status=404)
    else:
        svcId = svcId[0]
    svcRec = Service.GetServiceRecordByID(svcId)
    if svcRec.HasExtendedAuthorizationDetails():
        Service.PersistExtendedAuthDetails(svcRec)
    return HttpResponse()

def auth_disconnect(req, service):
    if not req.user:
        return redirect("dashboard")
    if "action" in req.POST:
        if req.POST["action"] == "disconnect":
            auth_disconnect_do(req, service)
        return redirect("dashboard")
    return render(req, "auth/disconnect.html", {"serviceid": service, "service": Service.FromID(service)})


@require_POST  # don't want this getting called by just anything
def auth_disconnect_ajax(req, service):
    # if req.user == None:
    #     return JsonResponse({"success": False, "error": "No user provided"},status=403)
    try:
        svcRec = User.GetConnectionRecord(req.user, service)
        if svcRec is None:
            User.DisconnectServiceByName(req.user.get("_id"), service)
            logging.warning("HUB ID user %s had no connection to %s but the ref to this connection has been removed" % (req.user.get("_id"), service))
            
        else:
            # Trying to remove the reference to the connection before the connection itself to avoid errors
            User.DisconnectService(svcRec)
            Service.DeleteServiceRecord(svcRec)
    except WriteError as e:
        logging.error("Got mongo WriteError while disconnecting user %s from %s. WriteError: %s, code: %s, details: %s" % (
            req.user.get("_id"),
            service,
            e,
            e.code,
            e.details
        ))
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    except Exception as e:
        logging.error("An error occured while diconnecting user %s from %s. Exception : %s" % (req.user.get("_id"), service, e))
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    return JsonResponse({"success": True})


def auth_disconnect_do(req, service):
    svc = Service.FromID(service)
    svcId = [x["ID"] for x in req.user["ConnectedServices"] if x["Service"] == svc.ID]
    if len(svcId) == 0:
        logging.error("The user %s can't disconnect %s service - Here is the list of his actual services %s" % (
            req.user["_id"], 
            service, 
            str(req.user.get("ConnectedServices","Can't find services"))
        ))
        return redirect('/')
    else:
        svcId = svcId[0]
    svcRec = Service.GetServiceRecordByID(svcId)
    Service.DeleteServiceRecord(svcRec)
    User.DisconnectService(svcRec)
    response = redirect('/')
    return response

@csrf_exempt
@require_POST
def auth_disconnect_garmin_health(req):
    if req.body.decode("UTF-8") != "":
        data = json.loads(req.body.decode("UTF-8"))
        external_user_ids = data['deregistrations']

        svc = Service.FromID("garminhealth")

        for external_user_id in external_user_ids:
            if external_user_id['userId'] is not None:
                serviceRecord = Service.EnsureServiceRecordWithAuth(svc, external_user_id['userId'], external_user_id['userAccessToken'])
                # auth by this service connection
                existingUser = User.AuthByService(serviceRecord)
                if req.user is None and existingUser is not None:
                    svcId = [x["ID"] for x in existingUser["ConnectedServices"] if x["Service"] == svc.ID]
                    svcId = svcId[0]
                    svcRec = Service.GetServiceRecordByID(svcId)
                    #Service.DeleteServiceRecord(svcRec)
                    User.DisconnectService(svcRec)

    return HttpResponse(status=200)
    

@require_POST
def auth_logout(req):
    User.Logout(req)
    return redirect("/")
