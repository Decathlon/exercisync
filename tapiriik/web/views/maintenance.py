from django.shortcuts import render

def maintenance(req, *args):
    return render(req, "maintenance.html")