from django.core.exceptions import MiddlewareNotUsed
import tapiriik.settings
import subprocess


class ServiceWebStartup:
    def __init__(self, get_response):
        from tapiriik.services import Service
        Service.WebInit()
        raise MiddlewareNotUsed


class Startup:
    def __init__(self, get_response):
        tapiriik.settings.SITE_VER = subprocess.Popen(["git", "rev-parse", "HEAD"], stdout=subprocess.PIPE).communicate()[0].strip()
        raise MiddlewareNotUsed
