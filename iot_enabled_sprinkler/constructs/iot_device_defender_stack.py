from aws_cdk import (
    Stack,
    aws_iot as iot,
    aws_iam as iam,
    aws_sns as sns,
    aws_cloudformation as cloudformation,
    CfnOutput, CfnDeletionPolicy, CfnTag, CfnOutput
)
from constructs import Construct
import json

class IotDeviceDefenderStack(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
                    dd_sns_publish_role: iam.Role, 
                    dd_mitigation_action_role: iam.Role,
                    dd_audit_role: iam.Role,
                    dd_audit_topic: sns.Topic,
                    dd_defend_topic: sns.Topic,
                    custom_resource: cloudformation.CfnCustomResource,
                    env_params: dict, 
                    **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create Device Defender (DD) Audit Schedule
        dd_scheduled_audit = iot.CfnScheduledAudit(self, "DDScheduledAudit",
            scheduled_audit_name= env_params['name'] + env_params['device_defender']['scheduled_audit_name'],
            frequency="DAILY",
            target_check_names=[
              "CONFLICTING_CLIENT_IDS_CHECK",
              "DEVICE_CERTIFICATE_EXPIRING_CHECK",
              "DEVICE_CERTIFICATE_KEY_QUALITY_CHECK",
              "DEVICE_CERTIFICATE_SHARED_CHECK",
              "IOT_POLICY_OVERLY_PERMISSIVE_CHECK",
              "LOGGING_DISABLED_CHECK",
              "REVOKED_DEVICE_CERTIFICATE_STILL_ACTIVE_CHECK",
            ],
            tags= [
                CfnTag(
                key= "Environment",
                value= env_params['tags']['Environment']
                ),
                CfnTag(
                key= "Project",
                value= env_params['tags']['Project']
                ),
            ]
        )
        # Add dependency
        dd_scheduled_audit.node.add_dependency(custom_resource)
        
        # Create DD ML Security Profile
        
        dd_ml_security_profile = iot.CfnSecurityProfile(self, "DDMlSecurityProfile",
            target_arns=[
                "arn:aws:iot:{}:{}:thinggroup/{}".format(env_params['region'], env_params['account_id'], env_params['name'] + env_params['static_thing_group']['group_name'])
            ],
            security_profile_name= env_params['name'] + env_params['device_defender']['ml_security_profile_name'],
            security_profile_description= "ML Security Profile for IoT Enabled Sprinklers",
            behaviors= [
                iot.CfnSecurityProfile.BehaviorProperty(
                    name= "Message_size_ML_behavior",
                    metric= "aws:message-byte-size",
                    criteria= iot.CfnSecurityProfile.BehaviorCriteriaProperty(
                        consecutive_datapoints_to_alarm= 1,
                        consecutive_datapoints_to_clear= 1,
                        ml_detection_config= iot.CfnSecurityProfile.MachineLearningDetectionConfigProperty(
                            confidence_level="HIGH"
                        )
                    ),
                    suppress_alerts=False
                ),
                iot.CfnSecurityProfile.BehaviorProperty(
                    name= "Messages_sent_ML_behavior",
                    metric= "aws:num-messages-sent",
                    criteria= iot.CfnSecurityProfile.BehaviorCriteriaProperty(
                        consecutive_datapoints_to_alarm= 1,
                        consecutive_datapoints_to_clear= 1,
                        ml_detection_config= iot.CfnSecurityProfile.MachineLearningDetectionConfigProperty(
                            confidence_level="HIGH"
                        )
                    ),
                    suppress_alerts=False
                ),
                iot.CfnSecurityProfile.BehaviorProperty(
                    name= "Authorization_failures_ML_behavior",
                    metric= "aws:num-authorization-failures",
                    criteria= iot.CfnSecurityProfile.BehaviorCriteriaProperty(
                        consecutive_datapoints_to_alarm= 1,
                        consecutive_datapoints_to_clear= 1,
                        ml_detection_config= iot.CfnSecurityProfile.MachineLearningDetectionConfigProperty(
                            confidence_level="HIGH"
                        )
                    ),
                    suppress_alerts=False
                )
            ],
            alert_targets = {
                "SNS": iot.CfnSecurityProfile.AlertTargetProperty(
                    alert_target_arn=dd_defend_topic.topic_arn,
                    role_arn= dd_sns_publish_role.role_arn
                )
            },
            tags= [
                CfnTag(
                key= "Environment",
                value= env_params['tags']['Environment']
                ),
                CfnTag(
                key= "Project",
                value= env_params['tags']['Project']
                ),
            ]
        )
        # Add dependency
        dd_ml_security_profile.node.add_dependency(custom_resource)
        
        # Create DD Mitigation Action
        dd_mitigation_action = iot.CfnMitigationAction(self, "DDMitigationAction",
            action_name= env_params['name'] + env_params['device_defender']['mitigation_action'],
            action_params=iot.CfnMitigationAction.ActionParamsProperty(
                add_things_to_thing_group_params=iot.CfnMitigationAction.AddThingsToThingGroupParamsProperty(
                    thing_group_names=[
                        env_params['name'] + env_params['device_defender']['quarantine_group']
                    ]
                )
            ),
            role_arn= dd_mitigation_action_role.role_arn,
            tags= [
                CfnTag(
                key= "Environment",
                value= env_params['tags']['Environment']
                ),
                CfnTag(
                key= "Project",
                value= env_params['tags']['Project']
                ),
            ]
        )
        # Add dependency
        dd_mitigation_action.node.add_dependency(custom_resource)
        