# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


'''
SAMPLE EVENT
{
    
    "thingName": ""
    
}

WHAT IT DOES:
1. Give thing name in event
2. Get RootCA and RootCA key from S3 
3. Create new certs with custom params 
4. Register Certificate with AWS IoT
5. Attach Certificate ID to thingName
6. Create JSON payload, and send cert and key to device topic
4. Return Cert and Key in json fromat

REQUIREMENT:
1. Thing be already created in Registry
'''


import subprocess # nosec
import os
import boto3
import json

s3 = boto3.resource('s3')
s3_client = boto3.client('s3')
iot = boto3.client('iot')
iot_data = boto3.client('iot-data')


def handler(event, context):
    
    ###################################
    # Define variables
    ###################################
    
    # Thing Name
    THING_NAME= event['thingName']
    
    # S3 Bucket 
    S3_BUCKET_NAME= os.environ.get('S3_BUCKET_NAME')
    
    # RootCA s3 key file names
    ROOT_CERT_FILE_KEY= os.environ.get('ROOT_CERT_FILE_KEY')
    ROOT_KEY_FILE_KEY= os.environ.get('ROOT_KEY_FILE_KEY')
    
    # RootCA file names
    ROOT_CERT_FILE= str(ROOT_CERT_FILE_KEY.split('/')[-1])
    ROOT_KEY_FILE= str(ROOT_KEY_FILE_KEY.split('/')[-1])
    
    # Cert File names
    DEVICE_KEY_FILE= "deviceCert.key"
    DEVICE_CSR_FILE= "deviceCert.csr"
    DEVICE_CERT_FILE= "deviceCert.crt"
    
    # Topic
    TOPIC= "{}/customCa/certificate/create/complete".format(THING_NAME)

    
    ###################################
    # Downlaod and store root certificates+key from S3
    ###################################
    
    
    # Define bucket 
    BUCKET = s3.Bucket(S3_BUCKET_NAME)
    
    localRootCertFile= '/tmp/'+ROOT_CERT_FILE # nosec
    localRootKeyFile= '/tmp/'+ROOT_KEY_FILE # nosec
    
    BUCKET.download_file(ROOT_CERT_FILE_KEY, localRootCertFile)
    BUCKET.download_file(ROOT_KEY_FILE_KEY, localRootKeyFile)

    
    ###################################
    # Create Device Certs using RootCa+Key
    ###################################
    
    # Define randfile
    os.system("RANDFILE=.rnd") # nosec
    os.system("echo $RANDFILE") # nosec
    
    localDeviceKeyFile= '/tmp/'+DEVICE_KEY_FILE # nosec
    localDeviceCsrFile= '/tmp/'+DEVICE_CSR_FILE # nosec
    localDeviceCertFile= '/tmp/'+DEVICE_CERT_FILE # nosec
    
    # openssl genrsa -out deviceCert.key 2048
    subprocess.run(["openssl", "genrsa", "-out", localDeviceKeyFile, "2048"]) # nosec
    # openssl req -new -key deviceCert.key -out deviceCert.csr -subj "/C=IN/ST=Karnataka/L=BLR/O=AMZ/OU=ProServe/CN=IoT Sprinkler Project"
    subj="/C=IN/ST=Karnataka/L=BLR/O=AMZ/OU=IoT Sprinkler Project/CN={}".format(THING_NAME) # nosec
    subprocess.run(["openssl", "req", "-new", "-key", localDeviceKeyFile, "-out", localDeviceCsrFile, "-subj", subj]) # nosec
    # openssl x509 -req -in deviceCert.csr -CA deviceRootCA.pem -CAkey deviceRootCA.key -CAcreateserial -out deviceCert.crt -days 90 -sha256
    subprocess.run(["openssl", "x509", "-req", "-in", localDeviceCsrFile, "-CA", localRootCertFile, "-CAkey", localRootKeyFile, "-CAcreateserial", "-out", localDeviceCertFile, "-days", "360", "-sha256"]) # nosec
    
    ###################################
    # Read cert and key files to string
    ###################################
    
    # Read certificate file to string
    with open(localDeviceCertFile, 'r') as file:
        certFilData = file.read()
        
    # Read key file to string
    with open(localDeviceKeyFile, 'r') as file:
        keyFilData = file.read()
    
    # Read rootCa file to string
    with open(localRootCertFile, 'r') as file:
        rootCertFilData = file.read()
        
    ###################################
    # Register Certificate with AWS IoT - get CertID
    ###################################

    register_response = iot.register_certificate(
        certificatePem= certFilData,
        caCertificatePem= rootCertFilData,
        setAsActive=True
    )
    
    ###################################
    # Attatch certs to thingName
    ###################################
    
    attach_principal_response = iot.attach_thing_principal(
        thingName= THING_NAME,
        principal= register_response['certificateArn']
    )
    
    ###################################
    # Creating json payload to send to device
    ###################################
    
    payload= {
        "certificateId": register_response['certificateId'],
        "certificatePem": certFilData,
        "privateKey": keyFilData
    }
    
    ###################################
    # Publishing payload to correct Topic
    ###################################
    
    print(json.dumps(payload))
    
    publish_response = iot_data.publish(topic=TOPIC, qos=1, payload=json.dumps(payload))
    
    payload['thingName']= THING_NAME
    
    # Return payload
    return {
        'statusCode': 200,
        'body': json.dumps(payload)
    }
    