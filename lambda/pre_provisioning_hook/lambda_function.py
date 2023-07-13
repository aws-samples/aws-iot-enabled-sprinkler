# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
from datetime import date

provision_response = {
    # "parameterOverrides": {"CertDate": date.today().strftime("%m/%d/%y")},
    'allowProvisioning': False
    
}

def lambda_handler(event, context):

    ## Stringent validation before proceeding
    if event['parameters']['SerialNumber'].startswith('AWS_'):

        provision_response["allowProvisioning"] = True
    
    print(provision_response["allowProvisioning"])
  
    return provision_response