from bson.objectid import ObjectId
from tapiriik.database import db
from tapiriik.services import Service
import random
from tapiriik.auth import User
import argparse
import requests
import time
from statistics import median, quantiles, mean


def generateServiceExtID(svc_id):
    if svc_id == "strava":
        return str(random.randint(10000000, 99999999))
    elif svc_id == "decathlon":
        return "eu"+hex(random.getrandbits(72))[2:]
    elif svc_id == "polarflow":
        return str(random.randint(10000000, 99999999))
    else:
        return str(random.randint(10000000, 99999999))


def createSvcRecord(svc_id, user):
    svc = Service.FromID(svc_id)
    authData = {
        "AccessToken": 'meh',
        "AccessTokenExpiresAt": 2620654339,
        "RefreshToken": 'meh'
    }
    uid = generateServiceExtID(svc_id)
    serviceRecord = Service.EnsureServiceRecordWithAuth(svc, uid, authData)
    User.ConnectService(user, serviceRecord)


parser = argparse.ArgumentParser(description='Create user in database')
parser.add_argument('--nbUser', type=int, dest='nbUser', required=True,
                    help='The number of User you want to create')

args = parser.parse_args()
cpt = 0


user_creation_perf_table = []
user_connecting_perf_table = []

if args.nbUser != None:

    print("Creating %s users connected to BlackHole and WebhookSavage" % args.nbUser)
    begin_time = time.perf_counter_ns()

    while cpt < args.nbUser:

        begin_new_user_time = time.perf_counter_ns()
        new_user = User.Create()
        end_new_user_time = time.perf_counter_ns()
        user_creation_perf_table.append(end_new_user_time - begin_new_user_time)


        begin_new_user_connections_time = time.perf_counter_ns()
        createSvcRecord("blackhole", new_user)
        createSvcRecord("webhooksavage", new_user)
        end_new_user_connections_time = time.perf_counter_ns()
        user_connecting_perf_table.append(end_new_user_connections_time-begin_new_user_connections_time)

        cpt +=1
        if (cpt % 100 == 0):
            print("%s/%s users has actually been created" % (cpt, args.nbUser))

    print("Database populated, now the Webhook controlled spam is beginning press Ctrl+C to exit !")


    user_creation_perf_table_quartiles = quantiles(data=user_creation_perf_table)
    print("User creation performance")
    print("\tThe 1st user took %s ms to be created" % (user_creation_perf_table[0]//1000000))
    print("\tThe last user took %s ms to be created" % (user_creation_perf_table[-2]//1000000))
    print("\tThe 1st quartile of user creation time value is %s ms " % (user_creation_perf_table_quartiles[0]//1000000))
    print("\tThe median of user creation time value is %s ms " % (user_creation_perf_table_quartiles[1]//1000000))
    print("\tThe 3rd quartile of user creation time value is %s ms " % (user_creation_perf_table_quartiles[2]//1000000))
    print("\tThe sum of all user creation time is %s ms" % (sum(user_creation_perf_table)//1000000))


    user_connection_creation_perf_table_quartiles = quantiles(data=user_connecting_perf_table)
    print("User connection creation performance")
    print("\tThe 1st connections took %s ms to be created" % (user_connecting_perf_table[0]//1000000))
    print("\tThe last connections took %s ms to be created" % (user_connecting_perf_table[-2]//1000000))
    print("\tThe 1st quartile of user connection creation time value is %s ms " % (user_connection_creation_perf_table_quartiles[0]//1000000))
    print("\tThe median of user connection creation time value is %s ms " % (user_connection_creation_perf_table_quartiles[1]//1000000))
    print("\tThe 3rd quartile of user connection creation time value is %s ms " % (user_connection_creation_perf_table_quartiles[2]//1000000))
    print("\tThe sum of all user connection creation time is %s ms" % (sum(user_connecting_perf_table)//1000000))

    # conn_id_list = [str(conn['_id']) for conn in db.connections.find({"Service": {"$eq":"webhooksavage"}}, {"_id": True})]

    # for conn_id in conn_id_list:
    #     requests.post("http://localhost:8000/sync/remote_callback/trigger_partial_sync/webhooksavage",data={"id":conn_id})