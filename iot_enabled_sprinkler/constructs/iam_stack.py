from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_s3 as s3,
    RemovalPolicy
)
import aws_cdk as cdk
from constructs import Construct

class IamStack(Construct):
    def __init__(self, scope: Construct, construct_id: str, env_params: dict, 
        devices_bucket: s3.Bucket,
        **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Provisioning role for Fleet provisioning template
        provisioning_template_role = iam.Role(self, "PreProvisioningRole",
            assumed_by=iam.ServicePrincipal("iot.amazonaws.com"),
            description="Execution Role for IoT Fleet Provisioning Template",
            managed_policies= [
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSIoTThingsRegistration')
            ]
        )
        
        # Policy that needs attached to lambda role
        lambda_iot_policy_document = iam.PolicyDocument(
            statements=[iam.PolicyStatement(
                actions=[
                    "iot:GetThingShadow",
                    "iot:Publish",
                    "iot:UpdateThingShadow"
                ],
                resources=[
                    "arn:aws:iot:{}:{}:thing/{}".format(env_params['region'], env_params['account_id'], "AWS_*"),
                    "arn:aws:iot:{}:{}:topic/{}".format(env_params['region'], env_params['account_id'], "AWS_*")
                ]
            )]
        )
        lambda_iot_policy = iam.Policy(self, "LambdaIotPolicy",
            document=lambda_iot_policy_document
        )
        
        #IoT Events Execution Role
        iot_events_execution_role_policy = {
           "Version": "2012-10-17",
           "Statement": [
             {
               "Effect": "Allow",
               "Action": "iot:Publish",
               "Resource": "arn:aws:iot:{}:{}:topic/{}".format(env_params['region'], env_params['account_id'], "AWS_*")
             },
             {
               "Effect": "Allow",
               "Action": "iotevents:BatchPutMessage",
               "Resource": "arn:aws:iotevents:{}:{}:input/{}".format(env_params['region'], env_params['account_id'], env_params['name'] + "*")
             },
             {
               "Effect": "Allow",
               "Action": "lambda:InvokeFunction",
               "Resource": "arn:aws:lambda:{}:{}:function:*".format(env_params['region'], env_params['account_id'])
             },
             {
               "Effect": "Allow",
               "Action": "sns:Publish",
               "Resource": "arn:aws:sns:{}:{}:{}".format(env_params['region'], env_params['account_id'], env_params['name'] + "*")
             }
           ]
        }
        iot_events_execution_role = iam.Role(self, "IotEventsExecutionRole",
            assumed_by=iam.ServicePrincipal("iotevents.amazonaws.com"),
            description='Execution Role for AWS IoT Events',
            managed_policies= [
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSIoTLogging'),
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSIoTRuleActions'),
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSIoTThingsRegistration')
            ],
            inline_policies= {
                'iot_events_execution_role_policy': iam.PolicyDocument.from_json(iot_events_execution_role_policy)
            }
        )
        
        # Roles to be assumed for IoT Rules Engine
        iot_events_rules_engine_role_policy = {
          "Version": "2012-10-17",
          "Statement": [
            {
              "Action": [
                "iotevents:BatchPutMessage"
              ],
              "Effect": "Allow",
              "Resource": "arn:aws:iotevents:{}:{}:input/{}".format(env_params['region'], env_params['account_id'], env_params['name'] + "*")
            }
          ]
        }
        iot_events_rules_engine_role = iam.Role(self, "iotEventsRulesEngineRole",
            assumed_by=iam.ServicePrincipal("iot.amazonaws.com"),
            description='Role for AWS IoT Rules Engine to send messages to IoT Events Input',
            inline_policies= {
                'iot_events_rules_engine_role_policy': iam.PolicyDocument.from_json(iot_events_rules_engine_role_policy)
            }
        )
        
        iot_analytics_rules_engine_role_policy = {
          "Version": "2012-10-17",
          "Statement": [
            {
              "Sid": "Stmt1643522718255",
              "Action": [
                "iotanalytics:BatchPutMessage"
              ],
              "Effect": "Allow",
              "Resource": "arn:aws:iotanalytics:{}:{}:channel/{}".format(env_params['region'], env_params['account_id'], env_params['name'] + "*")
            }
          ]
        }
        iot_analytics_rules_engine_role = iam.Role(self, "iotAnalyticsRulesEngineRole",
            assumed_by=iam.ServicePrincipal("iot.amazonaws.com"),
            description='Role for AWS IoT Rules Engine to send messages to IoT Analytics Channel',
            inline_policies= {
                'iot_analytics_rules_engine_role_policy': iam.PolicyDocument.from_json(iot_analytics_rules_engine_role_policy)
            }
        )
        
        # Policy for CW Put Metric Lambda
        lambda_cw_policy_document = iam.PolicyDocument(
            statements=[iam.PolicyStatement(
                actions=[
                    "cloudwatch:PutMetricData",
                ],
                resources=[
                    "*"
                ]
            )]
        )
        lambda_cw_policy = iam.Policy(self, "CWLambdaCwPolicy",
            document=lambda_cw_policy_document
        )
        
        # IAM Role for Device Defender to assume to perform audit checks
        dd_audit_role = iam.Role(self, "DDAuditRole",
            assumed_by= iam.ServicePrincipal("iot.amazonaws.com"),
            description="Role for IoT Device Defender Audit",
            managed_policies= [
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSIoTDeviceDefenderAudit')
            ]
        )
        # Retain Audit Role
        dd_audit_role.apply_removal_policy(RemovalPolicy.RETAIN)
        
        # IAM Role for Device Defender to assume and publish to SNS
        dd_sns_publish_policy = {
          "Version":"2012-10-17",
          "Statement":[
              {
                "Effect":"Allow",
                "Action":[
                  "sns:Publish"
                ],
                "Resource":[
                  "arn:aws:sns:{}:{}:{}".format(env_params['region'], env_params['account_id'], env_params['name'] + env_params['sns']['dd_audit']['topic_name']),
                  "arn:aws:sns:{}:{}:{}".format(env_params['region'], env_params['account_id'], env_params['name'] + env_params['sns']['dd_defend']['topic_name'])
                ]
            }
          ]
        }
        dd_sns_publish_role= iam.Role(self, "iotDDSnsPublishRole",
            assumed_by=iam.ServicePrincipal("iot.amazonaws.com"),
            description='Role for AWS IoT Device Defender to send Alerts to SNS Topic',
            inline_policies= {
                'dd_sns_publish_policy': iam.PolicyDocument.from_json(dd_sns_publish_policy)
            }
        )
        
        # Mitigation Action role for Device Defender
        dd_mitigation_action_policy= {
            "Version":"2012-10-17",
            "Statement":[
                {
                    "Effect":"Allow",
                    "Action":[
                        "iot:ListPrincipalThings",
                        "iot:AddThingToThingGroup"
                    ],
                    "Resource":[
                        "*"
                    ]
                }
            ]
        }
        dd_mitigation_action_role= iam.Role(self, "iotDDMitigationActionRole",
            assumed_by=iam.ServicePrincipal("iot.amazonaws.com"),
            description='Role for AWS IoT Device Defender Mitigation Action',
            inline_policies= {
                'dd_mitigation_action_policy': iam.PolicyDocument.from_json(dd_mitigation_action_policy)
            }
        )
        
        # Role for FleetHub Application
        fleet_hub_app_role = iam.Role(self, "FleetHubAppRole",
            role_name= env_params['fleet_hub']['role'] + "_" + env_params['name'].replace("_", ""),
            assumed_by= iam.ServicePrincipal("iotfleethub.amazonaws.com"),
            description="Role for IoT Fleet Hub Application",
            managed_policies= [
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSIoTFleetHubFederationAccess')
            ]
        )
        
        # Policy that needs attached to certiifcate rotation initiate lambda role
        cert_rotation_initiate_lambda_policy_document = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "iot:ListAuditFindings",
                        "iot:ListPrincipalThings"
                    ],
                    resources=["*"]
                ),
                iam.PolicyStatement(
                    actions=[
                        "iot:DescribeCertificate"
                    ],
                    resources=[
                        "arn:aws:iot:{}:{}:cert/{}".format(env_params['region'], env_params['account_id'], "*")
                    ]
                ),
                iam.PolicyStatement(
                    actions=[
                        "iot:DescribeThing",
                        "iot:AddThingToThingGroup"
                    ],
                    resources=[
                        "arn:aws:iot:{}:{}:thing/{}".format(env_params['region'], env_params['account_id'], "AWS_*"),
                        "arn:aws:iot:{}:{}:thinggroup/{}".format(env_params['region'], env_params['account_id'], env_params['name'] + "*"),
                    ]
                )
            ]
        )
        cert_rotation_initiate_lambda_policy = iam.Policy(self, "CertRotationInitiateLambdaIotPolicy",
            document=cert_rotation_initiate_lambda_policy_document
        )
        
        # Policy that needs attached to certiifcate rotation complete lambda role
        cert_rotation_complete_lambda_policy_document = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "iot:DetachThingPrincipal",
                        "iot:ListThingPrincipals"
                    ],
                    resources=["*"]
                ),
                iam.PolicyStatement(
                    actions=[
                        "iot:UpdateCertificate",
                        "iot:DeleteCertificate",
                        "iot:ListThingPrincipals",
                        "iot:RemoveThingFromThingGroup"
                    ],
                    resources=[
                        "arn:aws:iot:{}:{}:thing/{}".format(env_params['region'], env_params['account_id'], "AWS_*"),
                        "arn:aws:iot:{}:{}:thinggroup/{}".format(env_params['region'], env_params['account_id'], env_params['name'] + "*"),
                        "arn:aws:iot:{}:{}:cert/{}".format(env_params['region'], env_params['account_id'], "*")
                    ]
                )
            ]
        )
        cert_rotation_complete_lambda_policy = iam.Policy(self, "CertRotationCompleteLambdaIotPolicy",
            document=cert_rotation_complete_lambda_policy_document
        )
        
        # Role that will be passed by OTA Update Lambda to OTA Update
        ota_update_role = iam.Role(self, "iotOTAUpdateRole",
            role_name= env_params['iot_jobs']['ota_update_role_name'] + "_" + env_params['name'].replace("_", ""),
            assumed_by= iam.ServicePrincipal("iot.amazonaws.com"),
            description="Role for IoT OTA Update",
            managed_policies= [
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AmazonFreeRTOSOTAUpdate')
            ]
        )
        s3_firmware_files_access_policy_document = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "s3:GetObjectVersion",
                        "s3:PutObject",
                        "s3:GetObject"
                    ],
                    resources=[
                        "arn:aws:s3:::{}".format(devices_bucket.bucket_name),
                        "arn:aws:s3:::{}/*".format(devices_bucket.bucket_name)
                    ]
                ),
                iam.PolicyStatement(
                    actions=[
                        "iam:PassRole"
                    ],
                    resources=[
                        "arn:aws:iam::{}:role/{}".format(env_params['account_id'], env_params['iot_jobs']['ota_update_role_name'] + "_" + env_params['name'].replace("_", ""))
                    ]
                )
                
            ]
        )
        s3_firmware_files_access_policy = iam.Policy(self, "s3FirmwareFilesAccessPolicyDocument",
            document=s3_firmware_files_access_policy_document
        )
        ota_update_role.attach_inline_policy(s3_firmware_files_access_policy)
        
        # Policy that needs to be attached to OTA Update Lambda
        ota_update_lambda_policy_document = iam.PolicyDocument(
            statements=
                [
                    iam.PolicyStatement(
                        actions=[
                            "iot:CreateOTAUpdate"
                        ],
                        resources=[
                            "arn:aws:iot:{}:{}:otaupdate/{}".format(env_params['region'], env_params['account_id'], "IotEnabledSprinklers_*")
                        ]
                    ),
                    iam.PolicyStatement(
                        actions=[
                            "iam:PassRole"
                        ],
                        resources=[
                            "arn:aws:iam::{}:role/{}".format(env_params['account_id'], env_params['iot_jobs']['ota_update_role_name'] + "_" + env_params['name'].replace("_", ""))
                        ]
                    )
                ]
        )
        ota_update_lambda_policy = iam.Policy(self, "otaUpdateLambdaPolicy",
            document=ota_update_lambda_policy_document
        )
        
        # Policy that is attached to lambda that will update thing attribute
        thing_firmware_update_lambda_policy_document = iam.PolicyDocument(
            statements=[iam.PolicyStatement(
                actions=[
                    "iot:GetOtaUpdate",
                    "iot:UpdateThing"
                ],
                resources=[
                    "arn:aws:iot:{}:{}:otaupdate/{}".format(env_params['region'], env_params['account_id'], "IotEnabledSprinklers_*"),
                    "arn:aws:iot:{}:{}:thing/{}".format(env_params['region'], env_params['account_id'], "AWS_*")
                ]
            )]
        )
        thing_firmware_update_lambda_policy = iam.Policy(self, "ThingFirmwareUpdatePolicy",
            document=thing_firmware_update_lambda_policy_document
        )
        
        # Policy for lambda container that rotates certificates
        rotation_lambda_container_policy_document = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "s3:ListBucket",
                        "s3:GetObject"
                    ],
                    resources=[
                        "arn:aws:s3:::{}".format(devices_bucket.bucket_name),
                        "arn:aws:s3:::{}/*".format(devices_bucket.bucket_name)
                    ]
                ),
                iam.PolicyStatement(
                    actions=[
                        "iot:RegisterCertificate",
                        "iot:AttachThingPrincipal"
                    ],
                    resources=[
                        "*"
                    ]
                ),
                iam.PolicyStatement(
                    actions=[
                        "iot:Publish"
                    ],
                    resources=[
                        "arn:aws:iot:{}:{}:topic/{}".format(env_params['region'], env_params['account_id'], "AWS_*")
                    ]
                )
            ]
        )
        rotation_lambda_container_policy = iam.Policy(self, "RotationLambdaContainerPolicy",
            document=rotation_lambda_container_policy_document
        )
        
        # Policy for lambda container that creates certificates
        cert_creation_lambda_container_policy_document = iam.PolicyDocument(
            statements=[iam.PolicyStatement(
                actions=[
                    "s3:ListBucket",
                    "s3:GetObject"
                ],
                resources= [
                    "arn:aws:s3:::{}".format(devices_bucket.bucket_name),
                    "arn:aws:s3:::{}/*".format(devices_bucket.bucket_name)
                ]
            )]
        )
        cert_creation_lambda_container_policy = iam.Policy(self, "CreationLambdaContainerPolicy",
            document=cert_creation_lambda_container_policy_document
        )
        
        # Policy for lambda container that creates verification certificate
        verification_cert_creation_lambda_container_policy_document = iam.PolicyDocument(
            statements=[iam.PolicyStatement(
                actions=[
                    "iot:GetRegistrationCode"
                ],
                resources=["*"]
            )]
        )
        verification_cert_creation_lambda_container_policy = iam.Policy(self, "VerificationCreationLambdaContainerPolicy",
            document=verification_cert_creation_lambda_container_policy_document
        )
        
        
        # Role for JITP Template
        iot_jitp_template_role = iam.Role(self, "IotJitpTemplateRole",
            assumed_by=iam.ServicePrincipal("iot.amazonaws.com"),
            description='Role for JITP Template',
            role_name= env_params['name'] + env_params['jitp']['role_name'],
            managed_policies= [
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSIoTLogging'),
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSIoTRuleActions'),
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSIoTThingsRegistration')
            ]
        )
        iot_jitp_template_role.apply_removal_policy(RemovalPolicy.DESTROY)
        
        
        self.provisioning_template_role= provisioning_template_role
        self.lambda_iot_policy= lambda_iot_policy
        self.iot_events_execution_role= iot_events_execution_role
        self.iot_events_rules_engine_role= iot_events_rules_engine_role
        self.iot_analytics_rules_engine_role= iot_analytics_rules_engine_role
        self.lambda_cw_policy= lambda_cw_policy
        self.dd_audit_role= dd_audit_role
        self.dd_sns_publish_role= dd_sns_publish_role
        self.dd_mitigation_action_role= dd_mitigation_action_role
        self.fleet_hub_app_role= fleet_hub_app_role
        self.cert_rotation_initiate_lambda_policy= cert_rotation_initiate_lambda_policy
        self.cert_rotation_complete_lambda_policy= cert_rotation_complete_lambda_policy
        self.ota_update_role= ota_update_role
        self.ota_update_lambda_policy= ota_update_lambda_policy
        self.thing_firmware_update_lambda_policy= thing_firmware_update_lambda_policy
        self.rotation_lambda_container_policy= rotation_lambda_container_policy
        self.cert_creation_lambda_container_policy= cert_creation_lambda_container_policy
        self.iot_jitp_template_role= iot_jitp_template_role
        self.verification_cert_creation_lambda_container_policy= verification_cert_creation_lambda_container_policy