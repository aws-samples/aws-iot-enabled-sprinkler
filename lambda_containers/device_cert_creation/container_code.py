# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

'''
SAMPLE EVENT
{
    
    "thingName": "",
    "days": 90
    
}

WHAT IT DOES:
1. Give thing name in event
2. Get RootCA and RootCA key from S3 
3. Create new certs with custom params 
4. Return Cert and Key in json fromat
'''


import subprocess # nosec
import os
import boto3
import json

s3 = boto3.resource('s3')
s3_client = boto3.client('s3')

def handler(event, context):
    
    ###################################
    # Define variables
    ###################################
    
    # Thing Name
    THING_NAME= event['thingName']
    
    # Validity of certificate (days)
    DAYS= str(event['days'])
    
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
    DEVICE_AND_ROOT_CA_CERT_FILE= "deviceCertAndCACert.crt"
    
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
    localDeviceAndRootCaFile= '/tmp/'+DEVICE_AND_ROOT_CA_CERT_FILE # nosec
    
    # openssl genrsa -out deviceCert.key 2048
    subprocess.run(["openssl", "genrsa", "-out", localDeviceKeyFile, "2048"]) # nosec
    # openssl req -new -key deviceCert.key -out deviceCert.csr -subj "/C=IN/ST=Karnataka/L=BLR/O=AMZ/OU=ProServe/CN=IoT Sprinkler Project"
    subj="/C=IN/ST=Karnataka/L=BLR/O=AMZ/OU=IoT Sprinkler Project/CN={}".format(THING_NAME) # nosec
    subprocess.run(["openssl", "req", "-new", "-key", localDeviceKeyFile, "-out", localDeviceCsrFile, "-subj", subj]) # nosec
    # openssl x509 -req -in deviceCert.csr -CA deviceRootCA.pem -CAkey deviceRootCA.key -CAcreateserial -out deviceCert.crt -days 90 -sha256
    subprocess.run(["openssl", "x509", "-req", "-in", localDeviceCsrFile, "-CA", localRootCertFile, "-CAkey", localRootKeyFile, "-CAcreateserial", "-out", localDeviceCertFile, "-days", DAYS, "-sha256"]) # nosec
    # cat deviceCert.crt deviceRootCA.pem > deviceCertAndCACert.crt
    os.system("cat {} {} > {}".format(localDeviceCertFile, localRootCertFile, localDeviceAndRootCaFile)) # nosec
    # subprocess.run(["cat", localDeviceCertFile, localRootCertFile, ">", localDeviceAndRootCaFile])
    
    ###################################
    # Read cert and key files to string
    ###################################
    
    # Read certificate file to string
    with open(localDeviceCertFile, 'r') as file:
        certFilData = file.read()
        
    # Read key file to string
    with open(localDeviceKeyFile, 'r') as file:
        keyFilData = file.read()
    
    # Read deviceAndRootCaFile to string
    with open(localDeviceAndRootCaFile, 'r') as file:
        deviceAndRootCaFileData = file.read()
    
    ###################################
    # Creating json payload to send to device
    ###################################
    
    payload= {
        "thingName": THING_NAME,
        "certificatePem": certFilData,
        "privateKey": keyFilData,
        "deviceAndRootCa": deviceAndRootCaFileData
    }
    
    print(json.dumps(payload))
    
    ###################################
    # Return Payload
    ###################################
    
    # Return payload
    return {
        'statusCode': 200,
        'body': json.dumps(payload)
    }
    