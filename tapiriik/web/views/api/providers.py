from django.http.response import HttpResponse, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from tapiriik.services import Service
from tapiriik.settings import WITHDRAWN_SERVICES
import logging

@ensure_csrf_cookie
def providers(req):
    if req.user != None:
        user_connections = req.user.get("ConnectedServices")
        user_connections_name = [connection["Service"] for connection in user_connections]
        user_connections_with_auth_error = [
            connection["Service"]
            for connection in user_connections
            if Service.GetServiceRecordByID(connection["ID"]).HasAuthSyncError() 
        ]

        active_providers = [
            {
                "id": x.ID, 
                "displayName": x.DisplayName, 
                "mustReconnect": x.ID in user_connections_with_auth_error, 
                "isReceiver": x.ReceivesActivities, 
                "isSupplier": x.ProvidesActivities, 
                "isConnected": True if x.ID in user_connections_name else False, 
                "authURI": x.UserAuthorizationURL
            } for x in Service.List() if x.ID not in WITHDRAWN_SERVICES and x.ID != "decathlon"
        ] 

        return JsonResponse({"providers": active_providers})
    else:
        return HttpResponse(content="<h1>Unauthorized</h1>" ,status=403)
