from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from tapiriik.auth import User
from tapiriik.services import Service

@ensure_csrf_cookie
def dashboard(req):
    if req.user is None and req.COOKIES.get("device_support") == "mobile" or req.user is None and "mobile" in req.GET:
        return render(req, "static/onboarding.html")
    else:
        if req.user is not None:
            current_user_decathlon_connection_id = next((svc["ID"] for svc in req.user.get("ConnectedServices") if svc.get("Service") == "decathlon"), None)
            if current_user_decathlon_connection_id is not None:
                current_user_dkt_svc_record = Service.GetServiceRecordByID(current_user_decathlon_connection_id)
                if current_user_dkt_svc_record is not None and current_user_dkt_svc_record.HasAuthSyncError():
                    User.Logout(req)
                    return redirect(current_user_dkt_svc_record.Service.UserAuthorizationURL)
        return render(req, "dashboard.html")