# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


#### Import dependencies
from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder
from awsiot import iotjobs
from concurrent.futures import Future
import time as t
import json
import random
import os
from os.path import exists
import argparse
import sys
import threading
import time
import traceback
from uuid import uuid4
import requests # install explicitly

#### Import provisioning_files/fleetprovisioning.py file
from provisioning_files.fleetprovisioning import *

parser = argparse.ArgumentParser(description="IoT Enabled Sprinkler Script.")
parser.add_argument('--endpoint', required=True, help="Your AWS IoT custom endpoint, not including a port. " +
                                                      "Ex: \"w6zbse3vjd5b4p-ats.iot.us-west-2.amazonaws.com\"")
parser.add_argument('--device_name', required=True, help="Device Name for MQTT connection.")
args = parser.parse_args()

# Using globals to simplify sample code
is_sample_done = threading.Event()

#### Check if parameters file exists. If not exit.
if exists('parameters.json'):
    print("Found parameters file.")
    parameter_path='parameters.json'
    f = open('parameters.json')
    parameters = json.load(f)
elif exists('devices/{}/parameters.json'.format(args.device_name)):
    print("Found parameters file.")
    parameter_path='devices/{}/parameters.json'.format(args.device_name)
    f = open('devices/{}/parameters.json'.format(args.device_name))
    parameters = json.load(f)
else:
    print("Parameters file does not exist... Exiting")
    exit(0)

#### Check if certificate files exist and assign to variables. If not, provision device
if exists("certificates/{}_certificate.pem.crt".format(args.device_name)) : 
    print("Found certificate files")
    PATH_TO_CERT = "certificates/{}_certificate.pem.crt".format(args.device_name)
    PATH_TO_KEY = "certificates/{}_private.pem.key".format(args.device_name)
    PATH_TO_ROOT = "certificates/AmazonRootCA1.pem"

elif exists("devices/{}/certificates/{}_certificate.pem.crt".format(args.device_name, args.device_name)):
    print("Found certificate files")
    PATH_TO_CERT = "devices/{}/certificates/{}_certificate.pem.crt".format(args.device_name, args.device_name)
    PATH_TO_KEY = "devices/{}/certificates/{}_private.pem.key".format(args.device_name, args.device_name)
    PATH_TO_ROOT = "devices/{}/certificates/AmazonRootCA1.pem".format(args.device_name)

else:
    print("Did not find certificate files. Attempting to provision device ...")
    try:
        performCertificateRotation=False
        PATH_TO_ROOT = "devices/{}/certificates/AmazonRootCA1.pem".format(args.device_name)
        response = provision_device(args.device_name, args.endpoint, PATH_TO_ROOT, parameters['provisioningTemplateName'], performCertificateRotation,
                        parameters['version'], parameters['sensor_type'], parameters['plant_id'])
        if response['status'] != 'Done':
            print("Certificate Creation Failed")
        PATH_TO_CERT = "devices/{}/certificates/{}_certificate.pem.crt".format(args.device_name, args.device_name)
        PATH_TO_KEY = "devices/{}/certificates/{}_private.pem.key".format(args.device_name, args.device_name)
    except:
        print("Unexpected Error. \nPlease make sure of the following: \n1. You have provided --cert, --key, and --templateName for provisioning the device \n2. You are in the iot_enabled_sprinkler/ directory")
        exit(0)

#### Define ENDPOINT, CLIENT_ID, PATH_TO_CERT, PATH_TO_KEY, and PATH_TO_ROOT ####
ENDPOINT = args.endpoint
DEVICE_NAME = args.device_name
CLIENT_ID = DEVICE_NAME
MESSAGE_INTERVAL=parameters['message_interval']
DELAY=parameters['message_interval']
ABS_HYDRATED_STATE_VALUE=parameters['abs_hydrated_state_value']
ABS_DRY_STATE_VALUE=parameters['abs_dry_state_value']
SPRINKLER_TRIGGER_PERCENTAGE=parameters['sprinkler_trigger_percentage']

#### Define Topics to publish/subscribe ####
## PUBLISH TOPICS ##
TOPIC_PUB_SENSOR_SM = "{}/sensordata/soil_moisture".format(DEVICE_NAME)
print("TOPIC_PUB_SENSOR_SM: {}".format(TOPIC_PUB_SENSOR_SM))
# Update when sprinkler is turned on or off
TOPIC_PUB_SHADOW_UPDATE = "$aws/things/{}/shadow/update".format(DEVICE_NAME)
print("TOPIC_PUB_SHADOW_UPDATE: {}".format(TOPIC_PUB_SHADOW_UPDATE))
# Publish to GET topic to receive shadow document
TOPIC_PUB_SHADOW_GET = "$aws/things/{}/shadow/get".format(DEVICE_NAME)
print("TOPIC_PUB_SHADOW_GET: {}".format(TOPIC_PUB_SHADOW_GET))
# Publish Topic after completing Certificate Rotation
TOPIC_PUB_ROTATION_COMPLETE = "{}/certificate/rotation/complete".format(DEVICE_NAME)
print("TOPIC_PUB_ROTATION_COMPLETE: {}".format(TOPIC_PUB_ROTATION_COMPLETE))
# Publish to Topic to initiate custom certificate rotation flow
TOPIC_PUB_CUSTOM_CERT_CREATE_INITIATE = "{}/customCa/certificate/create/initiate".format(DEVICE_NAME)
print("TOPIC_PUB_CUSTOM_CERT_CREATE_INITIATE: {}".format(TOPIC_PUB_CUSTOM_CERT_CREATE_INITIATE))
## SUBSCRIBE TOPICS ## 
# Listen when sprinkler needs to turn on or off
TOPIC_SUB_SHADOW_DELTA = "$aws/things/{}/shadow/update/delta".format(DEVICE_NAME)
print("TOPIC_SUB_SHADOW_DELTA: {}".format(TOPIC_SUB_SHADOW_DELTA))
# Listen to GET shadow topic to receive updated parameters
TOPIC_SUB_SHADOW_GET = "$aws/things/{}/shadow/get/accepted".format(DEVICE_NAME)
print("TOPIC_SUB_SHADOW_GET: {}".format(TOPIC_SUB_SHADOW_GET))
# Listen to receive the new certificate and private key when rotating custom certificates
TOPIC_SUB_CUSTOM_CERT_CREATE_COMPLETE = "{}/customCa/certificate/create/complete".format(DEVICE_NAME)
print("TOPIC_SUB_CUSTOM_CERT_CREATE_COMPLETE: {}".format(TOPIC_SUB_CUSTOM_CERT_CREATE_COMPLETE))

""" 
    Define all the callback functions for subscribe calls 
"""

# Function for gracefully quitting this code
def exit(msg_or_exception):
    if isinstance(msg_or_exception, Exception):
        print("Exiting due to exception.")
        traceback.print_exception(msg_or_exception.__class__, msg_or_exception, sys.exc_info()[2])
    else:
        print("Exiting:", msg_or_exception)

    with locked_data.lock:
        if not locked_data.disconnect_called:
            print("Disconnecting...")
            locked_data.disconnect_called = True
            future = mqtt_connection.disconnect()
            future.add_done_callback(on_disconnected)

##  IOT JOBS CALLBACK FUNCTIONS ##

class LockedData:
    def __init__(self):
        self.lock = threading.Lock()
        self.disconnect_called = False
        self.is_working_on_job = False
        self.is_next_job_waiting = False

locked_data = LockedData()

def try_start_next_job():
    print("Trying to start the next job...")
    with locked_data.lock:
        if locked_data.is_working_on_job:
            print("Nevermind, already working on a job.")
            return

        if locked_data.disconnect_called:
            print("Nevermind, disconnecting.")
            return

        locked_data.is_working_on_job = True
        locked_data.is_next_job_waiting = False

    print("Publishing request to start next job...")
    request = iotjobs.StartNextPendingJobExecutionRequest(thing_name=DEVICE_NAME)
    publish_future = jobs_client.publish_start_next_pending_job_execution(request, mqtt.QoS.AT_LEAST_ONCE)
    publish_future.add_done_callback(on_publish_start_next_pending_job_execution)

def done_working_on_job():
    with locked_data.lock:
        locked_data.is_working_on_job = False
        try_again = locked_data.is_next_job_waiting

    if try_again:
        try_start_next_job()

def on_disconnected(disconnect_future):
    # type: (Future) -> None
    print("Disconnected.")

    # Signal that sample is finished
    is_sample_done.set()

def on_next_job_execution_changed(event):
    # type: (iotjobs.NextJobExecutionChangedEvent) -> None
    try:
        execution = event.execution
        if execution:
            print("Received Next Job Execution Changed event. job_id:{} job_document:{}".format(
                execution.job_id, execution.job_document))

            # Start job now, or remember to start it when current job is done
            start_job_now = False
            with locked_data.lock:
                if locked_data.is_working_on_job:
                    locked_data.is_next_job_waiting = True
                else:
                    start_job_now = True

            if start_job_now:
                try_start_next_job()

        else:
            print("Received Next Job Execution Changed event: None. Waiting for further jobs...")

    except Exception as e:
        exit(e)

def on_publish_start_next_pending_job_execution(future):
    # type: (Future) -> None
    try:
        future.result() # raises exception if publish failed

        print("Published request to start the next job.")

    except Exception as e:
        exit(e)

def on_start_next_pending_job_execution_accepted(response):
    # type: (iotjobs.StartNextJobExecutionResponse) -> None
    try:
        if response.execution:
            execution = response.execution
            print("Request to start next job was accepted. job_id:{} job_document:{}".format(
                execution.job_id, execution.job_document))

            # To emulate working on a job, spawn a thread that sleeps for a few seconds
            job_thread = threading.Thread(
                target=lambda: job_thread_fn(execution.job_id, execution.job_document),
                name='job_thread')
            job_thread.start()
        else:
            print("Request to start next job was accepted, but there are no jobs to be done. Waiting for further jobs...")
            done_working_on_job()

    except Exception as e:
        exit(e)

def on_start_next_pending_job_execution_rejected(rejected):
    # type: (iotjobs.RejectedError) -> None
    exit("Request to start next pending job rejected with code:'{}' message:'{}'".format(
        rejected.code, rejected.message))

def update_root_ca(url):
    # sample job document:
    # {
    #     "task": "UPDATE_DEVICE_ROOTCA_CERTIFICATE",
    #     "payload": {
    #         "url": "https://www.amazontrust.com/repository/AmazonRootCA1.pem"
    #     }
    # }
    # Getch RootCA Cert from URL
    print("Fetching new RootCA from url")
    urlResponse = requests.get(url) # nosec
    certData = urlResponse.text
    # Replace data in RootCa cert file
    print("Replaceing old RootCA with new RootCA")
    with open("devices/{}/certificates/AmazonRootCA1.pem".format(DEVICE_NAME), "w") as text_file:
        text_file.write(certData)
    # Replacement of root Ca is complete
    print("RootCA Rotation Complete")
    return

def update_device_iot_certificates():
    # sample job document:
    # {
    #     "task": "UPDATE_DEVICE_IOT_CERTIFICATES"
    # }
    templateName= parameters['rotationTemplateName']
    performCertificateRotation= True
    # Call the provisioning code to get and replace to new certs
    response = provision_device(DEVICE_NAME, ENDPOINT, PATH_TO_ROOT, templateName, performCertificateRotation)
    if response["status"] != 'Done':
        print("Certificate Rotation Failed")
        print("##======================================##\n\n")
        return
    payload = {
        "thingName" : DEVICE_NAME,
        "newCertificateId" : response["certificateID"]
    }
    mqtt_connection.publish(topic=TOPIC_PUB_ROTATION_COMPLETE, payload=json.dumps(payload), qos=mqtt.QoS.AT_LEAST_ONCE)
    # This will invoke a function that will remove, revoke, delete all certs except for the new one.
    print("Certificate Rotation Completed")
    print("##======================================##\n\n")
    return

def update_device_custom_certificates():
    # sample job document:
    # {
    #     "task": "UPDATE_DEVICE_CUSTOM_CERTIFICATES"
    # }
    
    # make a publish call to get new cert 
    payload = {
        "thingName" : DEVICE_NAME
    }
    print("Requesting new certificates")
    mqtt_connection.publish(topic=TOPIC_PUB_CUSTOM_CERT_CREATE_INITIATE, payload=json.dumps(payload), qos=mqtt.QoS.AT_LEAST_ONCE)
    
    return

def get_firmware_files_http(s3PresignedUrl):
    # os.system('wget -P devices/{}/firmware_files {} --trust-server-names'.format(DEVICE_NAME, s3PresignedUrl))
    return

def execute_ota_update():
    return

def job_thread_fn(job_id, job_document):
    try:
        print("Starting local work on job...")
        
        # For root ca update or cert update
        try:
            if job_document['task']=="UPDATE_DEVICE_ROOTCA_CERTIFICATE":
                update_root_ca(job_document['payload']['url'])
            elif job_document['task']=="UPDATE_DEVICE_IOT_CERTIFICATES":
                update_device_iot_certificates()
            elif job_document['task']=="UPDATE_DEVICE_CUSTOM_CERTIFICATES":
                update_device_custom_certificates()
        except Exception as e:
            print(e)
        
        # For ota update
        try: 
            # Download firmware files
            s3PresignedUrl= job_document['afr_ota']['files']['update_data_url']
            print("Downloading Firmware files")
            get_firmware_files_http(s3PresignedUrl)
            # Execute OTA Update
            print("Executing OTA Update")
            execute_ota_update
            print("OTA Update Executed successfully!")
        except Exception as e:
            print(e)
        print("Done working on job.")

        print("Publishing request to update job status to SUCCEEDED...")
        request = iotjobs.UpdateJobExecutionRequest(
            thing_name=DEVICE_NAME,
            job_id=job_id,
            status=iotjobs.JobStatus.SUCCEEDED)
        publish_future = jobs_client.publish_update_job_execution(request, mqtt.QoS.AT_LEAST_ONCE)
        publish_future.add_done_callback(on_publish_update_job_execution)

    except Exception as e:
        exit(e)

def on_publish_update_job_execution(future):
    # type: (Future) -> None
    try:
        future.result() # raises exception if publish failed
        print("Published request to update job.")

    except Exception as e:
        exit(e)

def on_update_job_execution_accepted(response):
    # type: (iotjobs.UpdateJobExecutionResponse) -> None
    try:
        print("Request to update job was accepted.")
        done_working_on_job()
    except Exception as e:
        exit(e)

def on_update_job_execution_rejected(rejected):
    # type: (iotjobs.RejectedError) -> None
    exit("Request to update job status was rejected. code:'{}' message:'{}'.".format(
        rejected.code, rejected.message))
        

##  CUSTOM CALLBACK FUNCTIONS ##

# Callback when the delta topic receives a message. 
def on_delta_message_received(topic, payload, **kwargs):
    print("\n##======================================##")
    print("Received message from topic '{}'".format(topic))
    # print(json.dumps(json.loads(payload)))
    payload = json.loads(payload)
    desired_state = payload['state']['sprinkler_state']
    print("DESIRED SPRINKLER STATE: {}".format(desired_state))

    if desired_state=="on":
        ##
        # Code to turn the sprinkler on...
        ##
        print("Sprinkler Turned On")
        shadowDoc = {
            "state": {
                "reported": {
                    "sprinkler_state": "on"
                }
            }
        }
        mqtt_connection.publish(topic=TOPIC_PUB_SHADOW_UPDATE, payload=json.dumps(shadowDoc), qos=mqtt.QoS.AT_LEAST_ONCE)
        print("Updated Shadow Document")

    if desired_state=="off":
        ##
        # Code to turn the sprinkler off...
        ##
        print("Sprinkler Turned Off")
        shadowDoc = {
            "state": {
                "reported": {
                    "sprinkler_state": "off"
                }
            }
        }
        mqtt_connection.publish(topic=TOPIC_PUB_SHADOW_UPDATE, payload=json.dumps(shadowDoc), qos=mqtt.QoS.AT_LEAST_ONCE)
        print("Updated Shadow Document")

    print("##======================================##\n\n")

#  Callback that updates the ABS_HYDRATED_STATE_VALUE and ABS_DRY_STATE_VALUE from shadow doc
def on_get_message_received(topic, payload, **kwargs):
    print("\n##======================================##")
    print("Received message from topic '{}'".format(topic))
    payload = json.loads(payload)

    global ABS_HYDRATED_STATE_VALUE
    global ABS_DRY_STATE_VALUE
    global SPRINKLER_TRIGGER_PERCENTAGE

    ABS_HYDRATED_STATE_VALUE = payload['state']['reported']['abs_hydrated_state_value']
    ABS_DRY_STATE_VALUE = payload['state']['reported']['abs_dry_state_value']
    SPRINKLER_TRIGGER_PERCENTAGE = payload['state']['reported']['sprinkler_trigger_percentage']
    
    print("Updated 'ABS_HYDRATED_STATE_VALUE' and 'ABS_DRY_STATE_VALUE' with ShadowDoc")
    print("##======================================##\n\n")

# Callback that updates device's certificates on receiving fresh certs

def on_custom_certificate_create_complete(topic, payload, **kwargs):
    print("\n##======================================##")
    print("Received message from topic '{}'".format(topic))
    payload = json.loads(payload)
    
    # take payload and store certs to certificate folder
    with open("devices/{}/certificates/{}_certificate.pem.crt".format(DEVICE_NAME, DEVICE_NAME), "w") as text_file:
        text_file.write(payload['certificatePem'])
    text_file.close()
    
    with open("devices/{}/certificates/{}_private.pem.key".format(DEVICE_NAME, DEVICE_NAME), "w") as text_file:
        text_file.write(payload['privateKey'])
    text_file.close()
    
    # Certs rotated, inititate rotation completion flow
    payload = {
        "thingName" : DEVICE_NAME,
        "newCertificateId" : payload['certificateId']
    }
    mqtt_connection.publish(topic=TOPIC_PUB_ROTATION_COMPLETE, payload=json.dumps(payload), qos=mqtt.QoS.AT_LEAST_ONCE)
    # This will invoke a function that will remove, revoke, delete all certs except for the new one.
    print("Certificate Rotation Completed")
    print("\n##======================================##")

""" 
    Define Publish Function 
"""
# Calculate Soil Moisture % using map function
def _map(x, in_min, in_max, out_min, out_max):
    return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

# Function that sends our sensor data to the cloud
def publish(data):
    # if (data>=ABS_HYDRATED_STATE_VALUE) and (data<ABS_DRY_STATE_VALUE-95):
    #     sensorReportedState = "hydrated"
    # else:
    #     sensorReportedState = "dry"
    
    soil_moisture_percentage = _map(data, ABS_HYDRATED_STATE_VALUE, ABS_DRY_STATE_VALUE, 100, 0)    
    
    if (soil_moisture_percentage<=SPRINKLER_TRIGGER_PERCENTAGE):
        sensorReportedState = "dry"
    else:
        sensorReportedState = "hydrated"
    
    message ={
        "sensorType": "SoilMoistureSensor",
        "deviceID": DEVICE_NAME,
        "sensorReportedState": sensorReportedState,
        "sensorReportedMoisturePercentage": soil_moisture_percentage,
        # "exactValue": data #DELETE
    }
    mqtt_connection.publish(topic=TOPIC_PUB_SENSOR_SM, payload=json.dumps(message), qos=mqtt.QoS.AT_LEAST_ONCE)
    print("\n=========> Published: '" + json.dumps(message) + "' to the topic: '" + TOPIC_PUB_SENSOR_SM + "'")


"""
    Establishing connection and executing device code
"""

if __name__ == '__main__':
    io.init_logging(io.LogLevel.Error, 'stderr')
    #### Spin up resources #### 
    event_loop_group = io.EventLoopGroup(1)
    host_resolver = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
    mqtt_connection = mqtt_connection_builder.mtls_from_path(
                endpoint=ENDPOINT,
                cert_filepath=PATH_TO_CERT,
                pri_key_filepath=PATH_TO_KEY,
                client_bootstrap=client_bootstrap,
                ca_filepath=PATH_TO_ROOT,
                client_id=CLIENT_ID,
                clean_session=True,
                keep_alive_secs=6
                )
    
    #### Attempt connecting to AWS IoT #### 
    print("Connecting to {} with client ID '{}'...".format(
            ENDPOINT, CLIENT_ID))
    # Make the connect() call
    connect_future = mqtt_connection.connect()
    # Establish Jobs Client
    jobs_client = iotjobs.IotJobsClient(mqtt_connection)
    # Future.result() waits until a result is available
    connect_future.result()
    print("Connected!")
    
    #### Check if this is new device. If yes, report device params #### 
    if parameters['new_device']==True:
        print("Updating shadow document with sensor parameters ...")
        shadowDoc = {
                "state": {
                    "reported": {
                        "flow_rate": parameters['flow_rate'],
                        "abs_hydrated_state_value": parameters['abs_hydrated_state_value'],
                        "abs_dry_state_value": parameters['abs_dry_state_value'],
                        "sprinkler_trigger_percentage": parameters['sprinkler_trigger_percentage']
                    }
                }
            }
        mqtt_connection.publish(topic=TOPIC_PUB_SHADOW_UPDATE, payload=json.dumps(shadowDoc), qos=mqtt.QoS.AT_LEAST_ONCE)
        with open(parameter_path, 'r+') as f:
            data = json.load(f)
            data['new_device'] = False
            f.seek(0)  # rewind
            json.dump(data, f)
            f.truncate()
    
    
    #### Subscribe to Topics #### 
    print('Begin Subscribe')
    try:
        print("Subscribing to topic '{}'...".format(TOPIC_SUB_SHADOW_DELTA))
        subscribe_topic, packet_id = mqtt_connection.subscribe(
                topic=TOPIC_SUB_SHADOW_DELTA,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=on_delta_message_received
        )
        subscribe_topic.result()
        #### Subscribe to Shadow Get Topic
        print("Subscribing to topic '{}'...".format(TOPIC_SUB_SHADOW_GET))
        subscribe_topic, packet_id = mqtt_connection.subscribe(
                topic=TOPIC_SUB_SHADOW_GET,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=on_get_message_received
        )
        subscribe_topic.result()
        
        #### Subscribe to Custom Cert rotation topic
        print("Subscribing to topic '{}'...".format(TOPIC_SUB_CUSTOM_CERT_CREATE_COMPLETE))
        subscribe_topic, packet_id = mqtt_connection.subscribe(
                topic=TOPIC_SUB_CUSTOM_CERT_CREATE_COMPLETE,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=on_custom_certificate_create_complete
        )
        subscribe_topic.result()
        
        #### Subscribe to Job Topics
        print("\nBegin Jobs Topics Subscriptions")
        
        print("Subscribing to Next Changed events...")
        changed_subscription_request = iotjobs.NextJobExecutionChangedSubscriptionRequest(
            thing_name=DEVICE_NAME)
        subscribed_future, _ = jobs_client.subscribe_to_next_job_execution_changed_events(
            request=changed_subscription_request,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_next_job_execution_changed)
        # Wait for subscription to succeed
        subscribed_future.result()
        
        print("Subscribing to Start responses...")
        start_subscription_request = iotjobs.StartNextPendingJobExecutionSubscriptionRequest(
            thing_name=DEVICE_NAME)
        subscribed_accepted_future, _ = jobs_client.subscribe_to_start_next_pending_job_execution_accepted(
            request=start_subscription_request,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_start_next_pending_job_execution_accepted)
    
        subscribed_rejected_future, _ = jobs_client.subscribe_to_start_next_pending_job_execution_rejected(
            request=start_subscription_request,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_start_next_pending_job_execution_rejected)
    
        # Wait for subscriptions to succeed
        subscribed_accepted_future.result()
        subscribed_rejected_future.result()
        
        print("Subscribing to Update responses...")
        # Note that we subscribe to "+", the MQTT wildcard, to receive
        # responses about any job-ID.
        update_subscription_request = iotjobs.UpdateJobExecutionSubscriptionRequest(
                thing_name=DEVICE_NAME,
                job_id='+')
    
        subscribed_accepted_future, _ = jobs_client.subscribe_to_update_job_execution_accepted(
            request=update_subscription_request,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_update_job_execution_accepted)
    
        subscribed_rejected_future, _ = jobs_client.subscribe_to_update_job_execution_rejected(
            request=update_subscription_request,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_update_job_execution_rejected)
    
        # Wait for subscriptions to succeed
        subscribed_accepted_future.result()
        subscribed_rejected_future.result()
        
    except Exception as e:
        exit(e)
    print('Subscribe End')
    
    #### Publish to shadow GET topic to receive the abs_hydrated_state_value & abs_dry_state_value value. #### 
    empty_payload={}
    mqtt_connection.publish(topic=TOPIC_PUB_SHADOW_GET, payload=json.dumps(empty_payload), qos=mqtt.QoS.AT_LEAST_ONCE)
    print("\n=========> Published: '" + json.dumps(empty_payload) + "' to the topic: '" + TOPIC_PUB_SHADOW_GET + "'")
    t.sleep(1)
    
    #### Make attempat to start job
    try_start_next_job()
    
    #### Begin infinite publish of Soil Moisture Sensor Data #### 
    print('Begin Infinite Publish')
    while True:
        var = ABS_HYDRATED_STATE_VALUE
        delimiter = random.randrange(4, 20, 2) # nosec
        
        while(var<ABS_DRY_STATE_VALUE):
            var = var+delimiter
            publish(var)
            t.sleep(DELAY)
        
        delimiter = random.randrange(4, 20, 2) # nosec
        while(var>ABS_HYDRATED_STATE_VALUE):
            var = var-delimiter
            publish(var)
            t.sleep(DELAY)
            
    # Wait for the sample to finish (won't finish)
    is_sample_done.wait()