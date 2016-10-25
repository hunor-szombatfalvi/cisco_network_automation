#this file is just a modification of an example script to interact with APIC-EM available in the cisco dev-net zone, 
#adapted to be used as a function and with some slight modifications

import requests
import json
import sys

requests.packages.urllib3.disable_warnings()  # Disable warnings for not verifying the SSL certificate

GET = "get"
POST = "post"


def run_api(command, controller='x.x.x.x'):
    ticket = getServiceTicket(controller)
    if command == 'show_run':
        command = 'api/v1/network-device/config'
    if command == 'node_info':
        command = 'api/v1/network-device'
    if ticket:
        return doRestCall(ticket, GET, "https://%s/%s" % (controller, command))

    else:
        print("No service ticket was received.  Ending program!")


def getServiceTicket(controller_ip):
    ticket = None
    url = "https://%s/api/v1/ticket" % controller_ip
    payload = {"username": "x", "password": "x"}
    header = {"content-type": "application/json"}
    response = requests.post(url, data=json.dumps(payload), headers=header, verify=False)
    if not response:
        print("No data returned!")
    else:
        r_json = response.json()
        ticket = r_json["response"]["serviceTicket"]
        print("ticket: ", ticket)
    return ticket


def doRestCall(aTicket, command, url, aData=None):
    payload = None
    try:
        if aData != None:
            payload = json.dumps(aData)
        header = {"X-Auth-Token": aTicket, "content-type": "application/json"}
        if command == GET:
            r = requests.get(url, data=payload, headers=header, verify=False)
        elif command == POST:
            r = requests.post(url, data=payload, headers=header, verify=False)
        else:
            print("Unknown command!")
            return
        if not r:
            print("No data returned!")
        else:
            print("Returned status code: %d" % r.status_code)
            return r.json()
    except:
        err = sys.exc_info()[0]
        msg_det = sys.exc_info()[1]
        print("Error: %s  Details: %s StackTrace: %s" % (err, msg_det, traceback.format_exc()))
