from aws_cdk import (
    Stack,
    aws_iot as iot,
    aws_iam as iam,
    aws_lambda as _lambda,
    CfnOutput, CfnDeletionPolicy
)
from constructs import Construct
import json

# Import provisioning template
f = open('provisioning_template/provisioning_template.json')
provisioning_template_body= json.load(f)

f = open('provisioning_template/certificate_rotation_template.json')
certificate_rotation_template_body= json.load(f)

class IotProvisioningStack(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
                    provisioning_template_role: iam.Role, 
                    env_params: dict, 
                    pre_provisioning_lambda: _lambda.Function,
                    **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
    
        
        # Define Thing Policy Document
        group_policy_document = {
            "Version": "2012-10-17",
            "Statement": [{
                    "Effect": "Allow",
                    "Action": [
                        "iot:Connect"
                    ],
                    "Resource": [
                        "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":client/${iot:Connection.Thing.ThingName}"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "iot:Publish"
                    ],
                    "Resource": [
                        "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topic/${iot:Connection.Thing.ThingName}/sensordata/*",
                        "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topic/$aws/things/${iot:Connection.Thing.ThingName}/shadow/update",
                        "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topic/$aws/things/${iot:Connection.Thing.ThingName}/shadow/get",
                        "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topic/${iot:Connection.Thing.ThingName}/certificate/rotation/complete",
                        "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topic/${iot:Connection.Thing.ThingName}/customCa/certificate/create/initiate",
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "iot:Subscribe"
                    ],
                    "Resource": [
                        "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topicfilter/$aws/things/${iot:Connection.Thing.ThingName}/shadow/update/delta",
                        "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topicfilter/$aws/things/${iot:Connection.Thing.ThingName}/shadow/get/accepted",
                        "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topicfilter/${iot:Connection.Thing.ThingName}/customCa/certificate/create/complete"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "iot:Receive"
                    ],
                    "Resource": [
                        "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topic/$aws/things/${iot:Connection.Thing.ThingName}/shadow/update/delta",
                        "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topic/$aws/things/${iot:Connection.Thing.ThingName}/shadow/get/accepted",
                        "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topic/${iot:Connection.Thing.ThingName}/customCa/certificate/create/complete"
                    ]
                }
            ]
        }
        
        # Create Thing Policy
        group_policy = iot.CfnPolicy(self, "GroupPolicy",
            policy_document=group_policy_document,
            policy_name= env_params['name'] + env_params['group_policy']['policy_name']
        )
        
        # Add group name to template
        provisioning_template_body["Resources"]["thing"]["Properties"]["ThingGroups"][0] = env_params['name'] + env_params['static_thing_group']['group_name']
        provisioning_template_body["Resources"]["thing"]["Properties"]["ThingTypeName"] = env_params['name'] + env_params['thing_type']['thing_type_name']      
        
        # Create Provisioning Template
        provisioning_template = iot.CfnProvisioningTemplate(self, "ProvisioningTemplate",
            provisioning_role_arn=provisioning_template_role.role_arn,
            template_body=json.dumps(provisioning_template_body),
            description="Template to Rotate Certificates on IoT Enabled Sprinklers",
            enabled=True,
            pre_provisioning_hook=iot.CfnProvisioningTemplate.ProvisioningHookProperty(
                target_arn=pre_provisioning_lambda.function_arn
            ),
            template_name= env_params['name'] + env_params['template']['provisioning_template_name']
        )
        # Add dependency
        provisioning_template.node.add_dependency(group_policy)
        
        # Create Policy document that will be attached to Claim Certificate
        claim_policy_document = {
          "Version": "2012-10-17",
          "Statement": [
            {
              "Effect": "Allow",
              "Action": "iot:Connect",
              "Resource": "*"
            },
            {
              "Effect": "Allow",
              "Action": [
                "iot:Publish",
                "iot:Receive"
              ],
              "Resource": [
                "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topic/$aws/certificates/create/*",
                "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topic/$aws/provisioning-templates/" + env_params['name'] + env_params['template']['provisioning_template_name'] + "/provision/*",
                "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topic/$aws/provisioning-templates/" + env_params['name'] + env_params['template']['rotation_template_name'] + "/provision/*"
              ]
            },
            {
              "Effect": "Allow",
              "Action": "iot:Subscribe",
              "Resource": [
                "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topicfilter/$aws/certificates/create/*",
                "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topicfilter/$aws/provisioning-templates/" + env_params['name'] + env_params['template']['provisioning_template_name'] + "/provision/*",
                "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topicfilter/$aws/provisioning-templates/" + env_params['name'] + env_params['template']['rotation_template_name'] + "/provision/*"
              ]
            }
          ]
        }
        
        # Create Claim Policy
        claim_policy = iot.CfnPolicy(self, "ClaimPolicy",
            policy_document=claim_policy_document,
            policy_name= env_params['name'] + env_params['claim_policy']['policy_name']
        )
        # Add dependency
        claim_policy.node.add_dependency(provisioning_template)
        
        # Create Policy that will be attached to the Quarantined Devices Group
        quarantine_group_policy_document = {"Version": "2012-10-17",
          "Statement": [
            {"Effect": "Deny",
              "Action": "iot:*",
              "Resource": "*",
            }
          ]
        }
        quarantine_group_policy = iot.CfnPolicy(self, "QuarantineGroupPolicy",
            policy_document=quarantine_group_policy_document,
            policy_name= env_params['name'] + env_params['device_defender']['quarantine_group_policy']
        )
        
        # Add group name to template
        certificate_rotation_template_body["Resources"]["thing"]["Properties"]["ThingGroups"][0] = env_params['name'] + env_params['static_thing_group']['group_name']
        
        # Create Fleet Provisioning Template for Certificate Rotation
        certificate_rotation_template = iot.CfnProvisioningTemplate(self, "CertificateRotationTemplate",
            provisioning_role_arn=provisioning_template_role.role_arn,
            template_body=json.dumps(certificate_rotation_template_body),
            description="Template to Provision an IoT Enabled Sprinklers",
            enabled=True,
            template_name= env_params['name'] + env_params['template']['rotation_template_name']
        )
        # Add dependency
        certificate_rotation_template.node.add_dependency(group_policy)
        
        
        # Policy to allow device to interact with AWS IoT Jobs
        iot_jobs_policy_document = {
          "Version": "2012-10-17",
          "Statement": [
            {
              "Effect": "Allow",
              "Action": [
                "iot:Publish"
              ],
              "Resource": [
                "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topic/$aws/things/${iot:Connection.Thing.ThingName}/jobs/start-next",
                "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topic/$aws/things/${iot:Connection.Thing.ThingName}/jobs/*/update"
              ]
            },
            {
              "Effect": "Allow",
              "Action": [
                "iot:Receive"
              ],
              "Resource": [
                "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topic/$aws/things/${iot:Connection.Thing.ThingName}/jobs/notify-next",
                "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topic/$aws/things/${iot:Connection.Thing.ThingName}/jobs/start-next/accepted",
                "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topic/$aws/things/${iot:Connection.Thing.ThingName}/jobs/start-next/rejected",
                "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topic/$aws/things/${iot:Connection.Thing.ThingName}/jobs/*/update/accepted",
                "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topic/$aws/things/${iot:Connection.Thing.ThingName}/jobs/*/update/rejected"
              ]
            },
            {
              "Effect": "Allow",
              "Action": [
                "iot:Subscribe"
              ],
              "Resource": [
                "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topicfilter/$aws/things/${iot:Connection.Thing.ThingName}/jobs/notify-next",
                "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topicfilter/$aws/things/${iot:Connection.Thing.ThingName}/jobs/start-next/accepted",
                "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topicfilter/$aws/things/${iot:Connection.Thing.ThingName}/jobs/start-next/rejected",
                "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topicfilter/$aws/things/${iot:Connection.Thing.ThingName}/jobs/*/update/accepted",
                "arn:aws:iot:" + env_params['region'] + ":" + env_params['account_id'] + ":topicfilter/$aws/things/${iot:Connection.Thing.ThingName}/jobs/*/update/rejected"
              ]
            }
          ]
        }
        # Create IoT Jobs Policy
        iot_jobs_policy = iot.CfnPolicy(self, "IotJobsPolicy",
            policy_document=iot_jobs_policy_document,
            policy_name= env_params['name'] + env_params['group_policy']['iot_jobs_policy_name']
        )
        
        self.provisioning_template= provisioning_template
        self.claim_policy= claim_policy
        self.group_policy= group_policy
        self.quarantine_group_policy= quarantine_group_policy
        self.certificate_rotation_template= certificate_rotation_template
        self.iot_jobs_policy= iot_jobs_policy
        