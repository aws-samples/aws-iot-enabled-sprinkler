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
    sprinklerTurnOffTime = message['eventTime']
    
    # Get the Turn On Time and Flow Rate from reported State
    response = client.get_thing_shadow(thingName=thingName)
    respone_json = json.loads(response['payload'].read())
    sprinklerTurnOnTime = respone_json['state']['reported']['sprinklerTurnOnTime']
    flowRate = respone_json['state']['reported']['flow_rate']
    
    # Create payload to update shdaow doc with empty
    shadowDoc = {
        "state": {
            "reported": {
                "sprinklerTurnOnTime": None
            },
            "desired": {
                "sprinkler_state": "off"
            }
        }
    }
    paylaod = json.dumps(shadowDoc)
    
    # Update Thing Shadow with payload
    response = client.update_thing_shadow(
        thingName=thingName,
        payload=paylaod
    )
    
    # Calculate Duration
    duration =  sprinklerTurnOffTime - sprinklerTurnOnTime
    
    # Calculate amount of water that flowed
    litresPerSecond = flowRate*1000
    
    timeInSeconds = duration/1000
    litresFlowed = litresPerSecond*timeInSeconds
    litresFlowed = float("{:.2f}".format(litresFlowed))
    
    # Create Payload and send to topic
    # paylaod = {
    #     "deviceID" : thingName,
    #     "sprinklerState" : "off",
    #     "duration_s" : timeInSeconds,
    #     "duration_ms" : duration,
    #     "waterFlowed_l" : litresFlowed,
    #     "flow_rate": flowRate
    # }
    
    # Sending less data to showcase how we can do math in IoT Analytics
    paylaod = {
        "deviceID" : thingName,
        "sprinklerState" : "off",
        "duration_ms" : duration,
        "flow_rate": flowRate
    }
    print(paylaod)
    paylaod = json.dumps(paylaod)
    response = client.publish(topic='{}/sprinkler/off'.format(thingName), qos=1, payload=paylaod)
    
    
    return {
        'statusCode': 200,
        'body': json.dumps('Executed Sprinkler Turn Off Event!')
    }