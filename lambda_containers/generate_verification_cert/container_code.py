# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

'''
SAMPLE EVENT
{
    "rootCaPem": "",
    "rootCaKey": ""
}

WHAT IT DOES:
1. Give RootCAPem and RootCAKey in event payload
2. Writes them to files
3. Creates verification cert with CN as AWS IoT Registration code
4. Converts Verification cert and key files to json payload
5. Return json
'''

import subprocess # nosec
import os
import boto3
import json

s3 = boto3.resource('s3')
s3_client = boto3.client('s3')
iot = boto3.client('iot')


def handler(event, context):
    
    
    ###################################
    # get rootCa cert and key from event and store in files
    ###################################
    
    with open("/tmp/deviceRootCA.key", "w") as text_file: # nosec
        text_file.write(event['rootCaKey'])
    text_file.close()
    
    with open("/tmp/deviceRootCA.pem", "w") as text_file: # nosec
        text_file.write(event['rootCaPem'])
    text_file.close()
    
    
    ###################################
    # Get registration code for region
    ###################################
    
    response= iot.get_registration_code()
    
    ###################################
    # Create verification cert
    ###################################
    
    subprocess.run(["openssl", "genrsa", "-out", "/tmp/verificationCert.key", "2048"]) # nosec
    subj="/C=IN/ST=Karnataka/L=BLR/O=AMZ/OU=IoT Sprinkler Project/CN={}".format(response['registrationCode']) # nosec
    subprocess.run(["openssl", "req", "-new", "-key", "/tmp/verificationCert.key", "-out", "/tmp/verificationCert.csr", "-subj", subj]) # nosec
    subprocess.run(["openssl", "x509", "-req", "-in", "/tmp/verificationCert.csr", "-CA", "/tmp/deviceRootCA.pem", "-CAkey", "/tmp/deviceRootCA.key", "-CAcreateserial", "-out", "/tmp/verificationCert.crt", "-days", "360", "-sha256"]) # nosec
    
    ###################################
    # Generate payload with verification cert
    ###################################
    
    # Read certificate file to string
    with open("/tmp/verificationCert.crt", 'r') as file:
        verificationCertFileData = file.read()
        
    # Read key file to string
    with open("/tmp/verificationCert.key", 'r') as file:
        verificationKeyFileData = file.read()
        
    payload= {
        "verificationCert": verificationCertFileData,
        "verificationKey": verificationKeyFileData
    }
    
    print(json.dumps(payload))
    
    # Return payload
    return {
        'statusCode': 200,
        'body': json.dumps(payload)
    }
    