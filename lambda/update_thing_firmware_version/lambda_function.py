# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


import json
import boto3

iot = boto3.client('iot')

def lambda_handler(event, context):
    
    response = iot.get_ota_update(
        otaUpdateId= event['jobId'].split('-')[1]
    )
    firmwareVersion= str(str(response['otaUpdateInfo']['otaUpdateFiles'][0]['fileLocation']['s3Location']['key'].split('/')[-1:][0]).replace('.zip','').split('_v')[1])
    thingName= str(event['thingArn'].split('/')[1])
    
    print("Thing Name: " + thingName + "|| Firmware Version: " + firmwareVersion)
    response = iot.update_thing(
        thingName= thingName,
        attributePayload={
            'attributes': {
                'FirmwareVersion': firmwareVersion
            },
            'merge': True
        }
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps('Thing attribute updated!')
    }
