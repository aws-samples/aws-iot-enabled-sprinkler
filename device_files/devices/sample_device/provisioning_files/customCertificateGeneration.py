# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import json
import argparse

# Initialize parser
parser = argparse.ArgumentParser()
_lambda = boto3.client('lambda')

# Adding optional argument
parser.add_argument("--thingName", help = "Thing Name", required= True)
parser.add_argument("--functionName", help = "Function Name", required= True)
parser.add_argument("--days", help = "Number of Days for how long the certificate is valid", required= False, default=90)

# Read arguments from command line
args = parser.parse_args()

event= {
    "thingName": args.thingName,
    "days": args.days
}
        
get_device_certs_response = _lambda.invoke(
    FunctionName= args.functionName,
    InvocationType= 'RequestResponse',
    Payload=json.dumps(event)
)

device_certs = json.loads(json.loads(get_device_certs_response['Payload'].read())['body'])
# print(device_certs)

# Store certs and keys to device certificates folder
with open("devices/{}/certificates/{}_certificate.pem.crt".format(args.thingName, args.thingName), "w") as text_file:
    text_file.write(device_certs['certificatePem'])
text_file.close()

with open("devices/{}/certificates/{}_private.pem.key".format(args.thingName, args.thingName), "w") as text_file:
    text_file.write(device_certs['privateKey'])
text_file.close()

with open("devices/{}/certificates/{}_deviceAndRootCa.pem".format(args.thingName, args.thingName), "w") as text_file:
    text_file.write(device_certs['deviceAndRootCa'])
text_file.close()

