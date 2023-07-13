# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


import json
import requests
import boto3
import os
import time as t
from uuid import uuid4
import botocore

iot = boto3.client('iot')
s3 = boto3.resource('s3')
s3_client = boto3.client('s3')
acm = boto3.client('acm')
signer = boto3.client('signer')
_lambda = boto3.client('lambda')

def lambda_handler(event, context):
    # TODO implement
    
    # Get variables from environment variable
    TEMPLATE_NAME= os.environ.get('TEMPLATE_NAME')
    CLAIM_POLICY_NAME= os.environ.get('CLAIM_POLICY_NAME')
    ROOTCA_URL= os.environ.get('ROOTCA_URL')
    S3_BUCKET_NAME= os.environ.get('S3_BUCKET_NAME')
    GROUP_NAME= os.environ.get('GROUP_NAME')
    GROUP_POLICY= os.environ.get('GROUP_POLICY')
    IOTJOBS_POLICY= os.environ.get('IOTJOBS_POLICY')
    QUARANTINE_GROUP_NAME= os.environ.get('QUARANTINE_GROUP_NAME')
    QUARANTINE_GROUP_POLICY= os.environ.get('QUARANTINE_GROUP_POLICY')
    DD_AUDIT_ROLE= os.environ.get('DD_AUDIT_ROLE')
    DD_AUDIT_TOPIC= os.environ.get('DD_AUDIT_TOPIC')
    DD_SNS_PUBLISH_ROLE= os.environ.get('DD_SNS_PUBLISH_ROLE')
    THING_TYPE_NAME= os.environ.get('THING_TYPE_NAME')
    
    # For creating signer profile
    CERT_FILE= "codeSigningCert.crt"
    KEY_FILE= "codeSigningCert.key"
    signerUUID = str(uuid4())[:8].replace('-','_')
    SIGNER_PROFILE_NAME= os.environ.get('SIGNER_PROFILE_NAME') + signerUUID
    OTA_UPDATE_LAMBDA_NAME= os.environ.get('OTA_UPDATE_LAMBDA_NAME')
    OTA_UPDATE_ROLE_ARN= os.environ.get('OTA_UPDATE_ROLE_ARN')
    
    # For iot cert rotation
    EXPIRING_IOT_CERTS_GROUP_NAME= os.environ.get('EXPIRING_IOT_CERTS_GROUP_NAME')
    IOT_CERTIFICATE_ROTATION_JOBS_TEMPLATE_ARN= os.environ.get('IOT_CERTIFICATE_ROTATION_JOBS_TEMPLATE_ARN')
    IOT_CERTIFICATE_ROTATION_JOB_ID= os.environ.get('IOT_CERTIFICATE_ROTATION_JOB_ID')
    
    # For custom cert rotation
    EXPIRING_CUSTOM_CERTS_GROUP_NAME= os.environ.get('EXPIRING_CUSTOM_CERTS_GROUP_NAME')
    CUSTOM_CERTIFICATE_ROTATION_JOBS_TEMPLATE_ARN= os.environ.get('CUSTOM_CERTIFICATE_ROTATION_JOBS_TEMPLATE_ARN')
    CUSTOM_CERTIFICATE_ROTATION_JOB_ID= os.environ.get('CUSTOM_CERTIFICATE_ROTATION_JOB_ID')
    
    # For registering customRootCa to AWS IoT
    CUSTOM_ROOT_CERT_FILE= "customRootCA.pem"
    CUSTOM_ROOT_KEY_FILE= "customRootCA.key"
    VERIFICATION_LAMBDA_CONTAINER_NAME= os.environ.get('VERIFICATION_LAMBDA_CONTAINER_NAME')
    
    # Define bucket 
    BUCKET = s3.Bucket(S3_BUCKET_NAME)
    
    if event['RequestType']=='Create':
        ###################################
        # Downlaod and store root certificate
        ###################################
        root_ca_response = requests.get(ROOTCA_URL, allow_redirects=True) # nosec
        open('/tmp/AmazonRootCA1.pem', 'wb').write(root_ca_response.content) # nosec
            # Uplaod to provisioning files folder
        bucket_object = BUCKET.Object("devices/sample_device/provisioning_files/AmazonRootCA1.pem")
        bucket_object.upload_file("/tmp/AmazonRootCA1.pem") # nosec
            # Upload to certificates folder
        bucket_object = BUCKET.Object("devices/sample_device/certificates/AmazonRootCA1.pem")
        bucket_object.upload_file("/tmp/AmazonRootCA1.pem") # nosec
        
        ###################################
        # Create keys and certificate
        ###################################
        keys_certs_response = iot.create_keys_and_certificate(
            setAsActive=True
        )
        
        ###################################
        # Store certificate in /tmp
        ###################################
        with open("/tmp/claim.certificate.pem", "w") as text_file: # nosec
            text_file.write(keys_certs_response['certificatePem'])
        text_file.close()
        ###################################
        # Upload certificate to S3
        ###################################
        bucket_object = BUCKET.Object("devices/sample_device/provisioning_files/claim.certificate.pem")
        bucket_object.upload_file("/tmp/claim.certificate.pem") # nosec
        
        ###################################
        # Store private cert in /tmp
        ###################################
        with open("/tmp/claim.private.key", "w") as text_file: # nosec
            text_file.write(keys_certs_response['keyPair']['PrivateKey'])
        text_file.close()
        ###################################
        # Upload certificate to S3
        ###################################
        bucket_object = BUCKET.Object("devices/sample_device/provisioning_files/claim.private.key")
        bucket_object.upload_file("/tmp/claim.private.key") # nosec
        
        ###################################
        # Attach policy to certificate
        ###################################
        attach_policy_resposne = iot.attach_policy(
            policyName=CLAIM_POLICY_NAME,
            target=keys_certs_response['certificateArn']
        )
        
        ###################################
        # Create Thing Group
        ###################################
        thing_group_response = iot.create_thing_group(
            thingGroupName=GROUP_NAME
        )
        
        ###################################
        # Attach Policies to Group
        ###################################
        attach_group_policy_resposne = iot.attach_policy(
            policyName=GROUP_POLICY,
            target=thing_group_response['thingGroupArn']
        )
        attach_group_iotjobs_policy_resposne = iot.attach_policy(
            policyName=IOTJOBS_POLICY,
            target=thing_group_response['thingGroupArn']
        )
        
        ###################################
        # Create Group for devices with expiring iot certs
        ###################################
        expiring_iot_certs_group_response = iot.create_thing_group(
            thingGroupName= EXPIRING_IOT_CERTS_GROUP_NAME
        )
        
        ###################################
        # Create a continuous job that will perform certificate rotation when device is added to cert rotation group
        ###################################
        response = iot.create_job(
            jobId= IOT_CERTIFICATE_ROTATION_JOB_ID,
            targets=[
                expiring_iot_certs_group_response['thingGroupArn'],
            ],
            description='Continuous job to that will execute iot certificate rotation',
            targetSelection= 'CONTINUOUS',
            jobTemplateArn= IOT_CERTIFICATE_ROTATION_JOBS_TEMPLATE_ARN,
        )
        
        ################################### 
        # Create Group for devices with expiring custom certs
        ###################################
        expiring_custom_certs_group_response = iot.create_thing_group(
            thingGroupName= EXPIRING_CUSTOM_CERTS_GROUP_NAME
        )
        
        ###################################
        # Create a continuous job that will perform certificate rotation when device is added to cert rotation group
        ###################################
        response = iot.create_job(
            jobId= CUSTOM_CERTIFICATE_ROTATION_JOB_ID,
            targets=[
                expiring_custom_certs_group_response['thingGroupArn'],
            ],
            description='Continuous job to that will execute custom certificate rotation',
            targetSelection= 'CONTINUOUS',
            jobTemplateArn= CUSTOM_CERTIFICATE_ROTATION_JOBS_TEMPLATE_ARN
        )
        
        ###################################
        # Create Quarantine Thing Group
        ###################################
        quarantine_thing_group_response = iot.create_thing_group(
            thingGroupName=QUARANTINE_GROUP_NAME
        )
        
        ###################################
        # Attach Quarantine Policy to Quarantine Group
        ###################################
        attach_quarantine_group_policy_resposne = iot.attach_policy(
            policyName=QUARANTINE_GROUP_POLICY,
            target=quarantine_thing_group_response['thingGroupArn']
        )
        
        ###################################
        # Update Indexing Configuration to turn on everything for FleetHub
        ###################################
        update_indexing_config_response = iot.update_indexing_configuration(
            thingIndexingConfiguration={
                'thingIndexingMode': 'REGISTRY_AND_SHADOW',
                'thingConnectivityIndexingMode': 'STATUS',
                # 'deviceDefenderIndexingMode': 'VIOLATIONS',
                'customFields': [
                    {
                        'name': 'shadow.reported.sprinkler_state',
                        'type': 'String'
                    },
                    {
                        'name': 'shadow.reported.sprinkler_trigger_percentage',
                        'type': 'String'
                    }
                ]
            },
            thingGroupIndexingConfiguration={
                'thingGroupIndexingMode': 'ON'
            }
        )
        
        ###################################
        # Enable Audit Settings in Region
        ###################################
        update_audit_settings_response = iot.update_account_audit_configuration(
            roleArn= DD_AUDIT_ROLE,
            auditNotificationTargetConfigurations={
                'SNS': {
                    'targetArn': DD_AUDIT_TOPIC,
                    'roleArn': DD_SNS_PUBLISH_ROLE,
                    'enabled': True
                }
            },
            auditCheckConfigurations={
                'CONFLICTING_CLIENT_IDS_CHECK': {
                    'enabled': True
                },
                'DEVICE_CERTIFICATE_SHARED_CHECK': {
                    'enabled': True
                },
                'DEVICE_CERTIFICATE_KEY_QUALITY_CHECK': {
                    'enabled': True
                },
                'IOT_POLICY_OVERLY_PERMISSIVE_CHECK': {
                    'enabled': True
                },
                'DEVICE_CERTIFICATE_EXPIRING_CHECK': {
                    'enabled': True
                },
                'REVOKED_DEVICE_CERTIFICATE_STILL_ACTIVE_CHECK': {
                    'enabled': True
                },
                'LOGGING_DISABLED_CHECK': {
                    'enabled': True
                }
            }
        )
        
        ###################################
        # Enable IoT Jobs Execution Events
        ###################################
        
        response = iot.update_event_configurations(
            eventConfigurations={
                'JOB_EXECUTION': {
                    'Enabled': True
                }
            }
        )
        
        ###################################
        # Create thing type
        ###################################
        response = iot.create_thing_type(
            thingTypeName= THING_TYPE_NAME,
            thingTypeProperties={
                'thingTypeDescription': 'Thing Type for IoT Enabled Sprinklers',
                'searchableAttributes': [
                    'SensorType',
                    'PlantId'
                ]
            }
        )
        
        ###################################
        # Get signer certificate and key from s3
        ###################################
        s3Cert= "firmware_files/"+CERT_FILE
        s3Key= "firmware_files/"+KEY_FILE
        
        localCertFile= '/tmp/'+CERT_FILE # nosec
        loclaKeyFile= '/tmp/'+KEY_FILE # nosec
        
        BUCKET.download_file(s3Cert, localCertFile)
        BUCKET.download_file(s3Key, loclaKeyFile)
        
        bucket_object = BUCKET.Object("devices/sample_device/firmware_files/"+CERT_FILE)
        bucket_object.upload_file(localCertFile)
        
        ###################################
        # Import cert to ACM
        ###################################
        acm_response= acm.import_certificate(
            Certificate= open(localCertFile, 'rb').read(),
            PrivateKey= open(loclaKeyFile, 'rb').read()
        )
        
        ###################################
        # Create signer profile
        ###################################
        create_signer_response= signer.put_signing_profile(
            profileName= SIGNER_PROFILE_NAME,
            signingMaterial={
                'certificateArn': acm_response['CertificateArn']
            },
            platformId= 'AmazonFreeRTOS-Default',
            overrides={
                'signingConfiguration': {
                    'encryptionAlgorithm': 'ECDSA',
                    'hashAlgorithm': 'SHA256'
                },
                'signingImageFormat': 'JSONEmbedded'
            },
            signingParameters={
                'certificatePathOnDevice': 'firmware_files/codeSigningCert.crt'
            }
        )
        
        ###################################
        # Update Lambda ENVIRONMENT Variable
        #  with Signer Profile Name
        ###################################
        
        update_lambda_env_response = _lambda.update_function_configuration(
            FunctionName= OTA_UPDATE_LAMBDA_NAME,
            Environment={
                'Variables': {
                    'SIGNER_PROFILE_NAME': SIGNER_PROFILE_NAME,
                    'DEVICES_GROUP_ARN': thing_group_response['thingGroupArn'],
                    'ROLE_ARN': OTA_UPDATE_ROLE_ARN
                }
            }
        )
        
        ###################################
        # Get customRootCa key and cert from s3
        ###################################
        
        s3Cert= "custom_cert_files/"+CUSTOM_ROOT_CERT_FILE
        s3Key= "custom_cert_files/"+CUSTOM_ROOT_KEY_FILE
        
        localCustomRootCertFile= '/tmp/'+CUSTOM_ROOT_CERT_FILE # nosec
        localCustomRootKeyFile= '/tmp/'+CUSTOM_ROOT_KEY_FILE # nosec
        
        BUCKET.download_file(s3Cert, localCustomRootCertFile)
        BUCKET.download_file(s3Key, localCustomRootKeyFile)
        
        
        ###################################
        # Call container lambda to get verificate cert
        ###################################
        
        # Read root certificate file to string
        with open(localCustomRootCertFile, 'r') as file:
            rootCaPemData = file.read()
        file.close()
            
        # Read root key file to string
        with open(localCustomRootKeyFile, 'r') as file:
            rootCaKeyData = file.read()
        file.close()
        
        event= {
            "rootCaPem": rootCaPemData,
            "rootCaKey": rootCaKeyData
        }
        
        get_verification_cert_response = _lambda.invoke(
            FunctionName= VERIFICATION_LAMBDA_CONTAINER_NAME,
            InvocationType= 'RequestResponse',
            Payload=json.dumps(event)
        )
        
        response_body= json.loads(json.loads(get_verification_cert_response['Payload'].read())['body'])

        
        ###################################
        # Download tempalte 
        ###################################
        
        s3Template= "jitp_template/template.json"
        localTemplateFile= '/tmp/template.json' # nosec
        BUCKET.download_file(s3Template, localTemplateFile)
        
        with open(localTemplateFile, 'r') as file:
            template = json.load(file)
        file.close()
        
        ###################################
        # Register root ca to AWS IoT 
        ###################################
        
        register_ca_response = iot.register_ca_certificate(
            caCertificate= rootCaPemData,
            allowAutoRegistration=True,
            registrationConfig={
                'templateBody': template['templateBody'],
                'roleArn': template['roleArn']
            },
            verificationCertificate= response_body['verificationCert'],
            setAsActive=True
        )
        
        print("CUSTOM ROOT CA CERTIFICATE ID: "+ register_ca_response['certificateId'])
        
        return {
            'statusCode': 200,
            'body': json.dumps('Executing Custom Resource!')
        }
        
    if event['RequestType']=='Delete':
        
        ###################################
        # Get claim certificate
        ###################################
        list_target_response = iot.list_targets_for_policy(
            policyName=CLAIM_POLICY_NAME,
        )
        CERTIFICATE_ARN= list_target_response['targets'][0]
        CERTIFICATE_ID= CERTIFICATE_ARN.split('/')[1]
        
        ###################################
        # Detach policy from certificate
        ###################################
        response = iot.detach_policy(
            policyName=CLAIM_POLICY_NAME,
            target=CERTIFICATE_ARN
        )
        
        ###################################
        # Deactivate Certificate
        ###################################
        update_certificate_response = iot.update_certificate(
            certificateId=CERTIFICATE_ID,
            newStatus='INACTIVE'
        )
        
        ###################################
        # Delete Certificate
        ###################################
        response = iot.delete_certificate(
            certificateId=CERTIFICATE_ID,
            forceDelete=True
        )
        
        ###################################
        # Delete object and the bucket
        ###################################
        
        # !!!!! Not deleting bucket. Please delete manually as versioning is enabled
        
        # print("Deleting objects and S3 bucket")
        # BUCKET.objects.all().delete()
        # BUCKET.delete()
        # print("Objects and S3 bucket deleted")
        
        ###################################
        # Delete the continuous job created for rotating certificates
        ###################################
        
        cancel_job_response = iot.cancel_job(
            jobId= IOT_CERTIFICATE_ROTATION_JOB_ID,
            force= True
        )
        cancel_job_response = iot.cancel_job(
            jobId= CUSTOM_CERTIFICATE_ROTATION_JOB_ID,
            force= True
        )
        
        delete_job_response = iot.delete_job(
            jobId= IOT_CERTIFICATE_ROTATION_JOB_ID,
            force= True
        )
        delete_job_response = iot.delete_job(
            jobId= CUSTOM_CERTIFICATE_ROTATION_JOB_ID,
            force= True
        )
                
        t.sleep(3)
        
        ###################################
        # Delete Group for devices with expiring certs
        ###################################
        response = iot.delete_thing_group(
            thingGroupName= EXPIRING_IOT_CERTS_GROUP_NAME,
        )
        t.sleep(1)
        response = iot.delete_thing_group(
            thingGroupName= EXPIRING_CUSTOM_CERTS_GROUP_NAME,
        )
        t.sleep(1)
        
        ###################################
        # Delete Static Thing Group
        ###################################
        response = iot.delete_thing_group(
            thingGroupName= GROUP_NAME,
        )
        t.sleep(1)
        
        ###################################
        # Delete Quarantine Static Thing Group
        ###################################
        response = iot.delete_thing_group(
            thingGroupName= QUARANTINE_GROUP_NAME,
        )
        t.sleep(1)
        
        ###################################
        # Update Indexing Configuration to turn off everything
        ###################################
        
        try:
            response = iot.update_indexing_configuration(
                thingIndexingConfiguration={
                    'thingIndexingMode': 'OFF',
                    'thingConnectivityIndexingMode': 'OFF',
                    # 'deviceDefenderIndexingMode': 'VIOLATIONS'
                },
                thingGroupIndexingConfiguration={
                    'thingGroupIndexingMode': 'OFF'
                }
            )
        except botocore.exceptions.ClientError as err:
            print("\n" + str(err) + "\n")
        
        ###################################
        # Disable Audit settings in region
        ###################################
        
        try:
            response = iot.update_account_audit_configuration(
                auditNotificationTargetConfigurations={
                    'SNS': {
                        'enabled': False
                    }
                },
                auditCheckConfigurations={
                    'CONFLICTING_CLIENT_IDS_CHECK': {
                        'enabled': False
                    },
                    'DEVICE_CERTIFICATE_SHARED_CHECK': {
                        'enabled': False
                    },
                    'DEVICE_CERTIFICATE_KEY_QUALITY_CHECK': {
                        'enabled': False
                    },
                    'IOT_POLICY_OVERLY_PERMISSIVE_CHECK': {
                        'enabled': False
                    },
                    'DEVICE_CERTIFICATE_EXPIRING_CHECK': {
                        'enabled': False
                    },
                    'REVOKED_DEVICE_CERTIFICATE_STILL_ACTIVE_CHECK': {
                        'enabled': False
                    },
                    'LOGGING_DISABLED_CHECK': {
                        'enabled': False
                    }
                }
            )
        except botocore.exceptions.ClientError as err:
            print("\n" + str(err) + "\n")
        
        ###################################
        # Disable IoT Jobs Execution Events
        ###################################
        
        response = iot.update_event_configurations(
            eventConfigurations={
                'JOB_EXECUTION': {
                    'Enabled': False
                }
            }
        )
        
        ###################################
        # Delete thing type
        ###################################
        # 1. Depricate
        # response= iot.deprecate_thing_type(
        #     thingTypeName= THING_TYPE_NAME
        # )
        
        # 2. List all things and update them to remove thing type
        list_things_response= iot.list_things(
            thingTypeName= THING_TYPE_NAME
        )
        
        for thing in list_things_response['things']:
            response= iot.update_thing(
                thingName= thing['thingName'],
                removeThingType= True
            )
        
        # # 3. Delete thing type. CANNOT DELETE AS IT NEEDS 5 MINUTES
        # response = iot.delete_thing_type(
        #     thingTypeName= THING_TYPE_NAME
        # )
        
        return {
            'statusCode': 200,
            'body': json.dumps('Executing Custom Resource!')
        }
    
    return {
        'statusCode': 200,
        'body': json.dumps('Executing Custom Resource!')
    }