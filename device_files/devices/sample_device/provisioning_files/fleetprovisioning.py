# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


import argparse
from awscrt import auth, http, io, mqtt
from awsiot import iotidentity
from awsiot import mqtt_connection_builder
from concurrent.futures import Future
import sys
import threading
import time
import traceback
from uuid import uuid4
import json
import os
from datetime import date

def provision_device(device_name, endpoint, root_ca, templateName, performCertificateRotation=False,
                version=None, sensor_type=None, plant_id=None, firmwareVersion= '13.3.4',
                client_id="test-"+str(uuid4()), verbosity=io.LogLevel.NoLogs.name):

    cert= "devices/{}/provisioning_files/claim.certificate.pem".format(device_name)
    key= "devices/{}/provisioning_files/claim.private.key".format(device_name)
    
    today = date.today()
    
    if performCertificateRotation==True:
        print('Attempting to rotate certificates')
        templateParameters = {
            "ThingName": device_name,
            "CertificateCreatedOn": str(today)
        }
    else:
        print("Provisioning device")
        templateParameters = {
            "SerialNumber": device_name,
            "CertificateCreatedOn": str(today),
            "SensorType": sensor_type,
            "PlantId": plant_id,
            "FirmwareVersion": firmwareVersion
        }
    
    # Using globals to simplify sample code
    is_sample_done = threading.Event()

    io.init_logging(getattr(io.LogLevel, verbosity), 'stderr')
    mqtt_connection = None
    identity_client = None

    global createKeysAndCertificateResponse
    createKeysAndCertificateResponse = None
    
    global registerThingResponse
    registerThingResponse = None
    
    global certificateID
    certificateID = None

    class LockedData:
        def __init__(self):
            self.lock = threading.Lock()
            self.disconnect_called = False

    locked_data = LockedData()

    # Function for gracefully quitting this sample
    def exit(msg_or_exception):
        if isinstance(msg_or_exception, Exception):
            print("Exiting Provisioning due to exception.")
            traceback.print_exception(msg_or_exception.__class__, msg_or_exception, sys.exc_info()[2])
        else:
            print("Exiting Provisioning:", msg_or_exception)

        with locked_data.lock:
            if not locked_data.disconnect_called:
                print("Disconnecting...")
                locked_data.disconnect_called = True
                future = mqtt_connection.disconnect()
                future.add_done_callback(on_disconnected)

    def on_disconnected(disconnect_future):
        # type: (Future) -> None
        print("Disconnected.")

        # Signal that sample is finished
        is_sample_done.set()

    def on_publish_register_thing(future):
        # type: (Future) -> None
        try:
            future.result() # raises exception if publish failed
            print("Published RegisterThing request..")

        except Exception as e:
            print("Failed to publish RegisterThing request.")
            exit(e)

    def on_publish_create_keys_and_certificate(future):
        # type: (Future) -> None
        try:
            future.result() # raises exception if publish failed
            print("Published CreateKeysAndCertificate request..")

        except Exception as e:
            print("Failed to publish CreateKeysAndCertificate request.")
            exit(e)

    def createkeysandcertificate_execution_accepted(response):
        # type: (iotidentity.CreateKeysAndCertificateResponse) -> None
        try:
            global createKeysAndCertificateResponse
            createKeysAndCertificateResponse = response
            print("Received a new message {}".format(createKeysAndCertificateResponse))
            
            if performCertificateRotation==True:
                device_name = templateParameters['ThingName']
            else:
                device_name = templateParameters['SerialNumber']

            # Set device as new device in parameters file
            with open('devices/{}/parameters.json'.format(device_name), 'r+') as f:
                data = json.load(f)
                data['new_device'] = True
                f.seek(0)  # rewind
                json.dump(data, f)
                f.truncate()

            # Write certificates in certificates folder
            with open("devices/{}/certificates/{}_certificate.pem.crt".format(device_name, device_name), "w") as text_file:
                text_file.write(createKeysAndCertificateResponse.certificate_pem)

            with open("devices/{}/certificates/{}_private.pem.key".format(device_name, device_name), "w") as text_file:
                text_file.write(createKeysAndCertificateResponse.private_key)
            
            # Getting value of Certificate ID that will be used during rotation
            global certificateID
            certificateID = createKeysAndCertificateResponse.certificate_id

            return

        except Exception as e:
            exit(e)

    def createkeysandcertificate_execution_rejected(rejected):
        # type: (iotidentity.RejectedError) -> None
        exit("CreateKeysAndCertificate Request rejected with code:'{}' message:'{}' statuscode:'{}'".format(
            rejected.error_code, rejected.error_message, rejected.status_code))

    def registerthing_execution_accepted(response):
        # type: (iotidentity.RegisterThingResponse) -> None
        try:
            global registerThingResponse
            registerThingResponse = response
            print("Received a new message {} ".format(registerThingResponse))
            return

        except Exception as e:
            exit(e)

    def registerthing_execution_rejected(rejected):
        # type: (iotidentity.RejectedError) -> None
        exit("RegisterThing Request rejected with code:'{}' message:'{}' statuscode:'{}'".format(
            rejected.error_code, rejected.error_message, rejected.status_code))

    # Callback when connection is accidentally lost.
    def on_connection_interrupted(connection, error, **kwargs):
        print("Connection interrupted. error: {}".format(error))


    # Callback when an interrupted connection is re-established.
    def on_connection_resumed(connection, return_code, session_present, **kwargs):
        print("Connection resumed. return_code: {} session_present: {}".format(return_code, session_present))

        if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
            print("Session did not persist. Resubscribing to existing topics...")
            resubscribe_future, _ = connection.resubscribe_existing_topics()

            # Cannot synchronously wait for resubscribe result because we're on the connection's event-loop thread,
            # evaluate result with a callback instead.
            resubscribe_future.add_done_callback(on_resubscribe_complete)

    def on_resubscribe_complete(resubscribe_future):
        resubscribe_results = resubscribe_future.result()
        print("Resubscribe results: {}".format(resubscribe_results))

        for topic, qos in resubscribe_results['topics']:
            if qos is None:
                sys.exit("Server rejected resubscribe to topic: {}".format(topic))

    def waitForCreateKeysAndCertificateResponse():
        # Wait for the response.
        loopCount = 0
        while loopCount < 12 and createKeysAndCertificateResponse is None:
            if createKeysAndCertificateResponse is not None:
                break
            print('Waiting... CreateKeysAndCertificateResponse: ' + json.dumps(createKeysAndCertificateResponse))
            loopCount += 1
            time.sleep(1)

    def waitForRegisterThingResponse():
        # Wait for the response.
        loopCount = 0
        while loopCount < 20 and registerThingResponse is None:
            if registerThingResponse is not None:
                break
            loopCount += 1
            print('Waiting... RegisterThingResponse: ' + json.dumps(registerThingResponse))
            time.sleep(1)

    # Spin up resources
    event_loop_group = io.EventLoopGroup(1)
    host_resolver = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

    mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint=endpoint,
        cert_filepath=cert,
        pri_key_filepath=key,
        client_bootstrap=client_bootstrap,
        ca_filepath=root_ca,
        client_id=client_id,
        on_connection_interrupted=on_connection_interrupted,
        on_connection_resumed=on_connection_resumed,
        clean_session=False,
        keep_alive_secs=30
    )
    print("Connecting to {} with client ID '{}'...".format(
        endpoint, client_id))

    connected_future = mqtt_connection.connect()

    identity_client = iotidentity.IotIdentityClient(mqtt_connection)

    connected_future.result()
    print("Connected!")

    try:
        createkeysandcertificate_subscription_request = iotidentity.CreateKeysAndCertificateSubscriptionRequest()

        print("Subscribing to CreateKeysAndCertificate Accepted topic...")
        createkeysandcertificate_subscribed_accepted_future, _ = identity_client.subscribe_to_create_keys_and_certificate_accepted(
            request=createkeysandcertificate_subscription_request,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=createkeysandcertificate_execution_accepted)

        # Wait for subscription to succeed
        createkeysandcertificate_subscribed_accepted_future.result()

        print("Subscribing to CreateKeysAndCertificate Rejected topic...")
        createkeysandcertificate_subscribed_rejected_future, _ = identity_client.subscribe_to_create_keys_and_certificate_rejected(
            request=createkeysandcertificate_subscription_request,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=createkeysandcertificate_execution_rejected)

        # Wait for subscription to succeed
        createkeysandcertificate_subscribed_rejected_future.result()

        registerthing_subscription_request = iotidentity.RegisterThingSubscriptionRequest(template_name=templateName)

        print("Subscribing to RegisterThing Accepted topic...")
        registerthing_subscribed_accepted_future, _ = identity_client.subscribe_to_register_thing_accepted(
            request=registerthing_subscription_request,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=registerthing_execution_accepted)

        # Wait for subscription to succeed
        registerthing_subscribed_accepted_future.result()

        print("Subscribing to RegisterThing Rejected topic...")
        registerthing_subscribed_rejected_future, _ = identity_client.subscribe_to_register_thing_rejected(
            request=registerthing_subscription_request,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=registerthing_execution_rejected)
        # Wait for subscription to succeed
        registerthing_subscribed_rejected_future.result()

        print("Publishing to CreateKeysAndCertificate...")
        publish_future = identity_client.publish_create_keys_and_certificate(
            request=iotidentity.CreateKeysAndCertificateRequest(), qos=mqtt.QoS.AT_LEAST_ONCE)
        publish_future.add_done_callback(on_publish_create_keys_and_certificate)

        waitForCreateKeysAndCertificateResponse()

        if createKeysAndCertificateResponse is None:
            raise Exception('CreateKeysAndCertificate API did not succeed')
        
        registerThingRequest = iotidentity.RegisterThingRequest(
            template_name=templateName,
            certificate_ownership_token=createKeysAndCertificateResponse.certificate_ownership_token,
            parameters=templateParameters)
        
        print("Publishing to RegisterThing topic...")
        registerthing_publish_future = identity_client.publish_register_thing(registerThingRequest, mqtt.QoS.AT_LEAST_ONCE)
        registerthing_publish_future.add_done_callback(on_publish_register_thing)

        waitForRegisterThingResponse()
        exit("success")

    except Exception as e:
        exit(e)

    is_sample_done.wait()
    
    response = {
        "status" : "Done",
        "certificateID" : certificateID
    }
    # return 'Done'
    return response