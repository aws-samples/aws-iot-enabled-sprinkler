from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_s3 as s3,
    aws_sqs as sqs,
    aws_s3_notifications as s3_notify,
    RemovalPolicy,
    aws_cloudformation as cloudformation
)
from constructs import Construct

class LambdaStack(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
                env_params: dict, 
                lambda_iot_policy: iam.Policy,
                lambda_cw_policy: iam.Policy,
                cert_rotation_initiate_lambda_policy: iam.Policy,
                cert_rotation_complete_lambda_policy: iam.Policy,
                ota_update_lambda_policy: iam.Policy,
                ota_update_role: iam.Role,
                devices_bucket: s3.Bucket,
                thing_firmware_update_lambda_policy: iam.Policy,
                **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        
        # Create SQS DLQ for Async Lambdas
        dead_letter_queue = sqs.Queue(self, "deadLetterQueue")
        
        dlq_destination_config = _lambda.DlqDestinationConfig(
            destination= dead_letter_queue.queue_arn
        )
        
        # Pre Provisioning Hook for IoT Provisioning Template 
        pre_provisioning_lambda = _lambda.Function(self, 'PreProvisioningLambda',
            description= "Pre Provisioning Hook for fleet provisioning template",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset('lambda/pre_provisioning_hook'),
            handler='lambda_function.lambda_handler',
        )
        pre_provisioning_lambda.grant_invoke(iam.ServicePrincipal('iot.amazonaws.com'))
        
        # Sprinkler Turn Off Event Lambda
        sprinkler_off_lambda = _lambda.Function(self, 'SprinklerOffLambda',
            description= "Sprinkler Turn Off Event Lambda Function",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset('lambda/iot_enabled_sprinkler_publish_off'),
            handler='lambda_function.lambda_handler',
        )
        sprinkler_off_lambda.grant_invoke(iam.ServicePrincipal('iotevents.amazonaws.com'))
        sprinkler_off_lambda.role.attach_inline_policy(lambda_iot_policy)
        
        # Sprinkler Turn On Event Lambda
        sprinkler_on_lambda = _lambda.Function(self, 'SprinklerOnLambda',
            description= "Sprinkler Turn On Event Lambda Function",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset('lambda/iot_enabled_sprinkler_publish_on'),
            handler='lambda_function.lambda_handler',
        )
        sprinkler_on_lambda.grant_invoke(iam.ServicePrincipal('iotevents.amazonaws.com'))
        sprinkler_on_lambda.role.attach_inline_policy(lambda_iot_policy)
        
        # CW Put Metric Data Lambda
        cw_put_metric_lambda = _lambda.Function(self, 'CwPutMetricLambda',
            description= "Updates CW Metrics with water consumption",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset('lambda/cw_put_metric'),
            handler='lambda_function.lambda_handler',
            environment= {
                "METRIC_NAME": env_params['name'] + env_params['cloudwatch']['metric_name'],
                "METRIC_NAMESPACE": env_params['name'] + env_params['cloudwatch']['metric_namespace'],
                "DIMENSIONS_NAME": env_params['name'] + env_params['cloudwatch']['dimensions_name'],
                "DIMENSIONS_VALUE_TOTAL": env_params['name'] + env_params['cloudwatch']['dimensions_value_total'],
                "DIMENSIONS_VALUE_DEVICE": env_params['name'] + env_params['cloudwatch']['dimensions_value_device']
            }
        )
        cw_put_metric_lambda.grant_invoke(iam.ServicePrincipal('iotanalytics.amazonaws.com'))
        cw_put_metric_lambda.role.attach_inline_policy(lambda_cw_policy)
        
        
        # Create lambda layer for cryptography
        cryptography_layer = _lambda.LayerVersion(self, 'cryptography_layer',
            code=_lambda.Code.from_asset("lambda_layer/cryptography"),
            description='Cryptography library files',
            compatible_runtimes=[
                _lambda.Runtime.PYTHON_3_9,
            ],
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Certificate rotation initiate lambda - invoked by SNS Topic
        cert_rotation_initiate_lambda = _lambda.Function(self, 'CertRotationInitiateLambda',
            description= "Initiates Certificate Rotation. Invoked by DD Audit via SNS",
            runtime=_lambda.Runtime.PYTHON_3_7,
            code=_lambda.Code.from_asset('lambda/certificate_rotation_initiate'),
            handler='lambda_function.lambda_handler',
            environment= {
                "EXPIRING_IOT_CERTS_GROUP_NAME": env_params['name'] + env_params['iot_jobs']['expiring_iot_certs_group'],
                "EXPIRING_CUSTOM_CERTS_GROUP_NAME": env_params['name'] + env_params['iot_jobs']['expiring_custom_certs_group'],
            },
            layers= [
                cryptography_layer
            ]
        )
        cert_rotation_initiate_lambda.role.attach_inline_policy(cert_rotation_initiate_lambda_policy)
        
        # Certificate rotation complete lambda - invoked by IoT Rule
        cert_rotation_complete_lambda = _lambda.Function(self, 'CertRotationCompleteLambda',
            description= "Completes Certificate Rotation. Invoked by Device via IoT Rule",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset('lambda/certificate_rotation_complete'),
            handler='lambda_function.lambda_handler',
            environment= {
                "EXPIRING_IOT_CERTS_GROUP_NAME": env_params['name'] + env_params['iot_jobs']['expiring_iot_certs_group'],
                "EXPIRING_CUSTOM_CERTS_GROUP_NAME": env_params['name'] + env_params['iot_jobs']['expiring_custom_certs_group'],
                "REGION": env_params['region'],
                "ACCOUNT_ID": env_params['account_id']
            }
        )
        cert_rotation_complete_lambda.grant_invoke(iam.ServicePrincipal('iot.amazonaws.com'))
        cert_rotation_complete_lambda.role.attach_inline_policy(cert_rotation_complete_lambda_policy)
        
        
        # Lambda that will trigger when firmware file is added to the firmware image folder in S3 and create an OTA Job
        ota_update_lambda = _lambda.Function(self, 'otaUpdateLambda',
            description= "Creates an OTA Update when new firmware files are added to bucket",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset('lambda/ota_update'),
            handler='lambda_function.lambda_handler',
            environment= {
                "SIGNER_PROFILE_NAME":  env_params['name'] + env_params['iot_jobs']['signer_profile_name'],
                "DEVICES_GROUP_ARN": "arn:aws:iot:{}:{}:thinggroup/{}".format(env_params['region'], env_params['account_id'], env_params['name'] + env_params['static_thing_group']['group_name']),
                "ROLE_ARN": ota_update_role.role_arn
            }
        )
        ota_update_lambda.role.attach_inline_policy(ota_update_lambda_policy)
        
            # Add Trigger to S3 bucket to invoke this Lambda
        notification = s3_notify.LambdaDestination(ota_update_lambda)
        notification.bind(self, devices_bucket)
        devices_bucket.add_object_created_notification(
           notification, s3.NotificationKeyFilter(prefix="firmware_files/firmware_v", suffix=".zip")
        )
        
        # Lambda that will update firmware version in thing attributes when a job is successful
        thing_firmware_update_lambda = _lambda.Function(self, 'ThingFirmwareUpdateLambda',
            description= "Updates firmware version on thing attribute after successful ota update",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset('lambda/update_thing_firmware_version'),
            handler='lambda_function.lambda_handler'
        )
        thing_firmware_update_lambda.role.attach_inline_policy(thing_firmware_update_lambda_policy)
        thing_firmware_update_lambda.grant_invoke(iam.ServicePrincipal('iot.amazonaws.com'))
        
        self.pre_provisioning_lambda= pre_provisioning_lambda
        self.sprinkler_off_lambda= sprinkler_off_lambda
        self.sprinkler_on_lambda= sprinkler_on_lambda
        self.cw_put_metric_lambda= cw_put_metric_lambda
        self.cert_rotation_initiate_lambda= cert_rotation_initiate_lambda
        self.cert_rotation_complete_lambda= cert_rotation_complete_lambda
        self.thing_firmware_update_lambda= thing_firmware_update_lambda
        self.ota_update_lambda= ota_update_lambda