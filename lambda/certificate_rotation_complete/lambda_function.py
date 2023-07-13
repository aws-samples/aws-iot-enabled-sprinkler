# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import boto3
import os
iot = boto3.client('iot')

def lambda_handler(event, context):
    # print(json.dumps(event))
    
    # get from environment variable
    EXPIRING_IOT_CERTS_GROUP_NAME= os.environ.get('EXPIRING_IOT_CERTS_GROUP_NAME')
    EXPIRING_CUSTOM_CERTS_GROUP_NAME= os.environ.get('EXPIRING_CUSTOM_CERTS_GROUP_NAME')
    REGION= os.environ.get('REGION')
    ACCOUNT_ID= os.environ.get('ACCOUNT_ID')
    
    # Define variables
    thingName = event['thingName']
    newCertificateID= event['newCertificateId']
    # Build certificate ARN
    newCertificateArn= "arn:aws:iot:{}:{}:cert/{}".format(REGION, ACCOUNT_ID, newCertificateID)
    
    # Fetch all certificates attached to the Thing
    response = iot.list_thing_principals(
        thingName= thingName
    )
    certificateArns = response['principals']
    
    # Check if the new cert is in the list of attached things
    for certificateArn in certificateArns:
        if certificateArn != newCertificateArn:
            # If it is not the new cert, detach, revoke, and delete old cert
            
            expiredCertificateArn= certificateArn
            expiredCertificateId= certificateArn.split('/')[1]
            
            # Detach
            try:
                response = iot.detach_thing_principal(
                    thingName=thingName,
                    principal=expiredCertificateArn
                )
            except Exception as e: 
                print("Could not detatch cert due to error ... \n")
                print(e)
            print("Detatched Cert: {}".format(certificateArn))
            
            # Revoke
            try:
                response = iot.update_certificate(
                    certificateId=expiredCertificateId,
                    newStatus='REVOKED'
                )
            except Exception as e: 
                print("Could not revoke cert due to error ... \n")
                print(e)
            print("Revoked Cert: {}".format(certificateArn))
            
            # Delete
            try:
                response = iot.delete_certificate(
                    certificateId=expiredCertificateId,
                    forceDelete=True
                )
            except Exception as e: 
                print("Could not delete cert due to error ... \n")
                print(e)
            print("Deleted Cert {}".format(certificateArn))
    
    # Once all expired certs are deleted, remove device from expiring certs group
    response = iot.remove_thing_from_thing_group(
        thingGroupName= EXPIRING_IOT_CERTS_GROUP_NAME,
        thingName= thingName
    )
    
    response = iot.remove_thing_from_thing_group(
        thingGroupName= EXPIRING_CUSTOM_CERTS_GROUP_NAME,
        thingName= thingName
    )
            
    return {
        'statusCode': 200,
        'body': json.dumps('All certs except new certificate deleted!')
    }
