# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import boto3

client = boto3.client('iot-data')

def lambda_handler(event, context):
    
    print(json.dumps(event))
    print("\n")
    
    # Get information from the Payload
    message = json.loads(event['Records'][0]['Sns']['Message'])
    thingName = message['payload']['detector']['keyValue']
    turnOnTime = message['eventTime']
    
    # Create Payload for publishing
    paylaod = {
        "deviceID" : thingName,
        "sprinklerState" : "on"
    }
    paylaod = json.dumps(paylaod)
    
    # Publish Payload to IoT Topic
    response = client.publish(topic='{}/sprinkler/on'.format(thingName), qos=1, payload=paylaod)
    
    # Create payload to update shdaow doc with time when sprinkler was turned on
    shadowDoc = {
        "state": {
            "reported": {
                "sprinklerTurnOnTime": turnOnTime
            },
            "desired": {
                "sprinkler_state": "on"
            }
        }
    }
    paylaod = json.dumps(shadowDoc)
    print(paylaod)
    # Update Thing Shadow with payload
    response = client.update_thing_shadow(
        thingName=thingName,
        payload=paylaod
    )
    return {
        'statusCode': 200,
        'body': json.dumps('Executed Sprinkler Turn On Event!')
    }