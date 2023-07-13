from aws_cdk import (
    Stack,
    custom_resources as cr,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_iot as iot,
    aws_iam as iam,
    aws_logs as logs,
    aws_sns as sns,
    RemovalPolicy, Duration,
    aws_cloudformation as cloudformation
)
import aws_cdk as cdk
from constructs import Construct

class CustomResourceStack(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
            devices_bucket: s3.Bucket,
            claim_policy: iot.CfnPolicy,
            group_policy: iot.CfnPolicy,
            iot_jobs_policy: iot.CfnPolicy,
            provisioning_template: iot.CfnProvisioningTemplate,
            dd_audit_role: iam.Role,
            dd_audit_topic: sns.Topic,
            dd_sns_publish_role: iam.Role, 
            iot_jitp_template_role: iam.Role,
            iot_cert_rotation_job_template: iot.CfnJobTemplate,
            custom_cert_rotation_job_template: iot.CfnJobTemplate,
            ota_update_lambda: _lambda.Function,
            verification_lambda_container: _lambda.Function,
            ota_update_role: iam.Role,
            env_params: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create lambda layer for requests library
        requests_layer = _lambda.LayerVersion(self, 'requests_layer',
            code=_lambda.Code.from_asset("lambda_layer/requests"),
            description='Uses a 3rd party library called requsts',
            compatible_runtimes=[
                _lambda.Runtime.PYTHON_3_7,
            ],
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Create lambda layer for openssl
        openssl_layer = _lambda.LayerVersion(self, 'openssl_layer',
            code=_lambda.Code.from_asset("lambda_layer/openssl"),
            description='Openssl library files',
            compatible_runtimes=[
                _lambda.Runtime.PYTHON_3_7,
            ],
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Create lambda policy
        custom_resource_lambda_policy_statement = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "iot:DeleteCertificate",
                        "iot:AttachPolicy",
                        "iot:DeletePolicy",
                        "iot:DetachPolicy",
                        "iot:UpdateCertificate",
                        "iot:ListTargetsForPolicy",
                        "iot:CreateJob",
                        "iot:CancelJob",
                        "iot:DeleteJob",
                        "iot:CreateThingType",
                        "iot:DeprecateThingType",
                        "iot:UpdateThing",
                        "iot:DeleteThingType"
                    ],
                    resources=[
                        "arn:aws:iot:{}:{}:cert/{}".format(env_params['region'], env_params['account_id'], "*"),
                        "arn:aws:iot:{}:{}:thinggroup/{}".format(env_params['region'], env_params['account_id'], env_params['name'] + "*"),
                        "arn:aws:iot:{}:{}:job/{}".format(env_params['region'], env_params['account_id'], env_params['name'] + "*"),
                        "arn:aws:iot:{}:{}:thingtype/{}".format(env_params['region'], env_params['account_id'], env_params['name'] + "*"),
                        "arn:aws:iot:{}:{}:thing/{}".format(env_params['region'], env_params['account_id'], "AWS_*"),
                        "arn:aws:iot:{}:{}:policy/{}".format(env_params['region'], env_params['account_id'], env_params['name'] + "*"),
                        "arn:aws:iot:{}:{}:jobtemplate/{}".format(env_params['region'], env_params['account_id'], env_params['name'] + "*")
                        
                    ]
                ),
                iam.PolicyStatement(
                    actions=[
                        "iam:PassRole"
                    ],
                    resources=[
                        dd_audit_role.role_arn,
                        dd_sns_publish_role.role_arn,
                        iot_jitp_template_role.role_arn
                    ]
                ),
                iam.PolicyStatement(
                    actions=[
                        "iot:CreateThingGroup",
                        "iot:DeleteThingGroup"
                    ],
                    resources=[
                        "arn:aws:iot:{}:{}:thinggroup/{}".format(env_params['region'], env_params['account_id'], env_params['name'] + "*")
                    ]
                )
            ]
        )
        custom_resource_lambda_policy = iam.Policy(self, "LambdaCustomResourcePolicy",
            document=custom_resource_lambda_policy_statement
        )
        
        
        custom_resource_lambda_policy_statement_2 = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:DeleteBucket",
                        "s3:ListBucket",
                        "s3:GetObject",
                        "acm:ImportCertificate",
                        "signer:PutSigningProfile",
                        "lambda:InvokeFunction",
                        "lambda:InvokeFunctionUrl",
                        "lambda:UpdateFunctionConfiguration",
                    ],
                    resources=["*"]
                ),
                iam.PolicyStatement(
                    actions=[
                        "iot:CreateKeysAndCertificate",
                        "iot:UpdateIndexingConfiguration",
                        "iot:UpdateAccountAuditConfiguration",
                        "iot:ListThings",
                        "iot:UpdateEventConfigurations",
                        "iot:RegisterCACertificate"
                    ],
                    resources=["*"]
                )
            ]
        )
        custom_resource_lambda_policy_2 = iam.Policy(self, "LambdaCustomResourcePolicy2",
            document=custom_resource_lambda_policy_statement_2
        )
        
        
        # Create custom resource lambda function
        onEvent = _lambda.Function(self, 'CustomResourceFunction',
            description= "Custom Resource Lambda function",
            runtime= _lambda.Runtime.PYTHON_3_7,
            handler= 'lambda_function.lambda_handler',
            timeout= Duration.seconds(50),
            memory_size= 512,
            code= _lambda.Code.from_asset('lambda/custom_resource'),
            layers= [
                requests_layer,
                openssl_layer
            ],
            environment= {
                "ROOTCA_URL": env_params['rootCa']['url'],
                "CLAIM_POLICY_NAME": claim_policy.policy_name,
                "S3_BUCKET_NAME": devices_bucket.bucket_name,
                "TEMPLATE_NAME": provisioning_template.template_name,
                "GROUP_NAME": env_params['name'] + env_params['static_thing_group']['group_name'],
                "GROUP_POLICY": group_policy.policy_name,
                "IOTJOBS_POLICY": iot_jobs_policy.policy_name,
                "QUARANTINE_GROUP_NAME": env_params['name'] + env_params['device_defender']['quarantine_group'],
                "QUARANTINE_GROUP_POLICY": env_params['name'] + env_params['device_defender']['quarantine_group_policy'],
                "DD_AUDIT_ROLE": dd_audit_role.role_arn,
                "DD_AUDIT_TOPIC": dd_audit_topic.topic_arn,
                "DD_SNS_PUBLISH_ROLE": dd_sns_publish_role.role_arn,
                "EXPIRING_IOT_CERTS_GROUP_NAME": env_params['name'] + env_params['iot_jobs']['expiring_iot_certs_group'],
                "IOT_CERTIFICATE_ROTATION_JOBS_TEMPLATE_ARN": iot_cert_rotation_job_template.attr_arn,
                "IOT_CERTIFICATE_ROTATION_JOB_ID": env_params['name'] + env_params['iot_jobs']['iot_certificate_rotation_job_id'],
                "THING_TYPE_NAME": env_params['name'] + env_params['thing_type']['thing_type_name'],
                "SIGNER_PROFILE_NAME": env_params['name'] + env_params['iot_jobs']['signer_profile_name'],
                "OTA_UPDATE_LAMBDA_NAME": ota_update_lambda.function_name,
                "OTA_UPDATE_ROLE_ARN": ota_update_role.role_arn,
                "EXPIRING_CUSTOM_CERTS_GROUP_NAME": env_params['name'] + env_params['iot_jobs']['expiring_custom_certs_group'],
                "CUSTOM_CERTIFICATE_ROTATION_JOBS_TEMPLATE_ARN": custom_cert_rotation_job_template.attr_arn,
                "CUSTOM_CERTIFICATE_ROTATION_JOB_ID": env_params['name'] + env_params['iot_jobs']['custom_certificate_rotation_job_id'],
                "VERIFICATION_LAMBDA_CONTAINER_NAME": verification_lambda_container.function_name
            }
        )
        onEvent.role.attach_inline_policy(custom_resource_lambda_policy)
        onEvent.role.attach_inline_policy(custom_resource_lambda_policy_2)
        
        # Add dependency
        onEvent.node.add_dependency(claim_policy)
        onEvent.node.add_dependency(devices_bucket)
        onEvent.node.add_dependency(provisioning_template)
        onEvent.node.add_dependency(group_policy)
        onEvent.node.add_dependency(iot_cert_rotation_job_template)
        onEvent.node.add_dependency(custom_cert_rotation_job_template)
        onEvent.node.add_dependency(verification_lambda_container)
        onEvent.node.add_dependency(ota_update_lambda)
        
        # Create custom resource
        provider = cr.Provider(self, "CustomResourceProvider",
            on_event_handler=onEvent,
            log_retention= logs.RetentionDays.ONE_DAY
        )
        custom_resource = cloudformation.CfnCustomResource(self, "CfnCustomResource",
            service_token=provider.service_token
        )
        
        self.custom_resource = custom_resource