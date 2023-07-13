# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


import boto3
import json
import os
from cryptography import x509

iot = boto3.client('iot')

def lambda_handler(event, context):
    
    # get from environment variable
    EXPIRING_IOT_CERTS_GROUP_NAME= os.environ.get('EXPIRING_IOT_CERTS_GROUP_NAME')
    EXPIRING_CUSTOM_CERTS_GROUP_NAME= os.environ.get('EXPIRING_CUSTOM_CERTS_GROUP_NAME')
    
    # print(json.dumps(event))
    publishPayloads = []
    myDict = json.loads(event["Records"][0]["Sns"]["Message"])
    
    isIoTCert= False
    isCustomCert= False

    # filter for actionable check violations
    for audit in myDict["auditDetails"]:
        if (audit["checkName"] == "DEVICE_CERTIFICATE_EXPIRING_CHECK") and (audit['checkRunStatus'] == "COMPLETED_NON_COMPLIANT"):
            
            #initialize the list with all impacted things
            auditResults = iot.list_audit_findings(
                taskId=myDict["taskId"],
                checkName=audit["checkName"]
            )

            for finding in auditResults["findings"]:
                myExpiringCert = finding["nonCompliantResource"]["resourceIdentifier"]["deviceCertificateId"]

                #get the ARN for the certificate
                certDescResponse = iot.describe_certificate(
                    certificateId=myExpiringCert
                )
                
                # Fetch the certificate from certDescResponse
                certBytes = bytes(certDescResponse['certificateDescription']['certificatePem'], 'utf-8')
                cert = x509.load_pem_x509_certificate(certBytes)
                # Get CommonName of certificate
                attributeArray= []
                for attribute in cert.subject:
                    attributeArray.append(attribute)
                if (attributeArray[-1].value) != "AWS IoT Certificate" and attributeArray[-2].value == "IoT Sprinkler Project":
                    isCustomCert= True
                elif (attributeArray[-1].value) == "AWS IoT Certificate":
                    isIoTCert= True
                else:
                    print("unknown certificate")
                    return {'statusCode': 400, "message": "unknown certificate"}

                #get things for this cert
                thingsResp = iot.list_principal_things(
                    maxResults=100,
                    principal=certDescResponse["certificateDescription"]["certificateArn"]
                )

                #add things to the correct group
                for thing in thingsResp["things"]:
                    
                    if isIoTCert == True:
                        response = iot.add_thing_to_thing_group(
                            thingGroupName= EXPIRING_IOT_CERTS_GROUP_NAME,
                            thingName= thing,
                        )
                    elif isCustomCert== True:
                        response = iot.add_thing_to_thing_group(
                            thingGroupName= EXPIRING_CUSTOM_CERTS_GROUP_NAME,
                            thingName= thing,
                        )
                    
    return {
        'statusCode': 200,
        'body': json.dumps('Executed Certificate Rotation Initiation Event!')
    }