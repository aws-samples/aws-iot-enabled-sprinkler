# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


import json
import boto3
import os
cloudwatch = boto3.client('cloudwatch')

def lambda_handler(event, context):
    
    METRIC_NAME= os.environ.get('METRIC_NAME')
    METRIC_NAMESPACE= os.environ.get('METRIC_NAMESPACE')
    DIMENSIONS_NAME= os.environ.get('DIMENSIONS_NAME')
    DIMENSIONS_VALUE_TOTAL= os.environ.get('DIMENSIONS_VALUE_TOTAL')
    DIMENSIONS_VALUE_DEVICE = os.environ.get('DIMENSIONS_VALUE_DEVICE')
    
    for e in event:
        response_total = cloudwatch.put_metric_data(
            Namespace=METRIC_NAMESPACE,
            MetricData=[
                {
                    'MetricName': "total_" + METRIC_NAME,
                    'Dimensions': [
                        {
                            'Name': DIMENSIONS_NAME,
                            "Value": DIMENSIONS_VALUE_TOTAL
                        },
                    ],
                    'Value': e['waterFlowed_l']
                },
            ]
        )
        response_device_level = cloudwatch.put_metric_data(
            Namespace=METRIC_NAMESPACE,
            MetricData=[
                {
                    'MetricName': "device_" + METRIC_NAME,
                    'Dimensions': [
                        {
                            'Name': DIMENSIONS_NAME,
                            "Value": DIMENSIONS_VALUE_DEVICE + "-" + e['deviceID']  
                        },
                    ],
                    'Value': e['waterFlowed_l']
                },
            ]
        )
        
    
    return event
