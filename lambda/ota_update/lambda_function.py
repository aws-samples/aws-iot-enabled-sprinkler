# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


import json
import boto3
from uuid import uuid4
import os

iot = boto3.client('iot')

def lambda_handler(event, context):
    
    DEVICES_GROUP_ARN= os.environ.get('DEVICES_GROUP_ARN')
    ROLE_ARN= os.environ.get('ROLE_ARN')
    SIGNER_PROFILE_NAME= os.environ.get('SIGNER_PROFILE_NAME')
    
    for record in event['Records']:
        key= record['s3']['object']['key']
        fileName= str(key.split('/')[-1:][0])
        folder= key.replace(fileName,"")
        print(folder)
        version= record['s3']['object']['versionId']
        bucket= record['s3']['bucket']['name']
        
        otaUpdateId= 'IotEnabledSprinklers_OTA_UPDATE_'+str(uuid4())[:8]
        print("OTA UPDATE ID: "+ otaUpdateId)
        
        response = iot.create_ota_update(
            otaUpdateId= otaUpdateId,
            description='IotEnabledSprinklers Firmware Update IoT Job',
            targets=[
                DEVICES_GROUP_ARN
            ],
            protocols=[
                'HTTP'
            ],
            targetSelection='SNAPSHOT',
            awsJobPresignedUrlConfig={
                'expiresInSec': 3600
            },
            files=[
              {
                "fileLocation": {
                  "s3Location": {
                    "bucket": bucket,
                    "key": key,
                    "version": version
                  }
                },
                "codeSigning":{
                  "startSigningJobParameter":{
                    "signingProfileName": SIGNER_PROFILE_NAME,
                    "destination": {
                      "s3Destination": {
                        "bucket": bucket,
                        "prefix": folder+"SignedImages/"
                      }
                    }
                  }
                }  
              }
            ],
            roleArn= ROLE_ARN
        )  
        print()
        print(response)
    
    return {
        'statusCode': 200,
        'body': json.dumps('OTA UPDATE CREATED')
    }
