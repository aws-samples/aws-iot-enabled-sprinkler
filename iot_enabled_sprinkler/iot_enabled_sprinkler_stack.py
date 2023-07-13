from aws_cdk import (
    # Duration,
    Stack,
    Tags
)
from constructs import Construct
from uuid import uuid4

from iot_enabled_sprinkler.constructs.iam_stack import IamStack
from iot_enabled_sprinkler.constructs.lambda_stack import LambdaStack
from iot_enabled_sprinkler.constructs.sns_stack import SnsStack
from iot_enabled_sprinkler.constructs.iot_provisioning_stack import IotProvisioningStack
from iot_enabled_sprinkler.constructs.iot_events_stack import IotEventsStack
from iot_enabled_sprinkler.constructs.iot_analytics_stack import IotAnalyticsStack
from iot_enabled_sprinkler.constructs.iot_rules_engine_stack import IotRulesEngineStack
from iot_enabled_sprinkler.constructs.s3_stack import S3Stack
from iot_enabled_sprinkler.constructs.custom_resource_stack import CustomResourceStack
from iot_enabled_sprinkler.constructs.iot_device_defender_stack import IotDeviceDefenderStack
from iot_enabled_sprinkler.constructs.iot_fleet_hub_stack import IotFleetHubStack
from iot_enabled_sprinkler.constructs.iot_jobs_stack import IotJobsStack
from iot_enabled_sprinkler.constructs.lambda_container_stack import LambdaContainerStack

class IotEnabledSprinklerStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, env_params: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
    
        s3_stack = S3Stack(
            self, "S3", env_params=env_params
        )
        
        iam_stack = IamStack(
            self, "Iam", env_params=env_params,
            devices_bucket= s3_stack.devices_bucket
        )
        
        
        lambda_stack = LambdaStack(
            self, "Lambda", env_params=env_params,
            lambda_iot_policy=iam_stack.lambda_iot_policy,
            lambda_cw_policy=iam_stack.lambda_cw_policy,
            cert_rotation_initiate_lambda_policy= iam_stack.cert_rotation_initiate_lambda_policy,
            cert_rotation_complete_lambda_policy= iam_stack.cert_rotation_complete_lambda_policy,
            ota_update_lambda_policy= iam_stack.ota_update_lambda_policy,
            ota_update_role= iam_stack.ota_update_role,
            devices_bucket= s3_stack.devices_bucket,
            thing_firmware_update_lambda_policy= iam_stack.thing_firmware_update_lambda_policy
        )
        
        lambda_container_stack= LambdaContainerStack(
            self, "LambdaContainers", env_params=env_params,
            devices_bucket= s3_stack.devices_bucket,
            rotation_lambda_container_policy= iam_stack.rotation_lambda_container_policy,
            cert_creation_lambda_container_policy= iam_stack.cert_creation_lambda_container_policy,
            verification_cert_creation_lambda_container_policy= iam_stack.verification_cert_creation_lambda_container_policy
        )
        
        sns_stack = SnsStack(
            self, "Sns", env_params=env_params,
            sprinkler_off_lambda=lambda_stack.sprinkler_off_lambda,
            sprinkler_on_lambda=lambda_stack.sprinkler_on_lambda,
            cert_rotation_initiate_lambda= lambda_stack.cert_rotation_initiate_lambda
        )
        
        iot_provisioning_stack = IotProvisioningStack(
            self, "IotProvisioning", env_params=env_params, 
            provisioning_template_role=iam_stack.provisioning_template_role,
            pre_provisioning_lambda=lambda_stack.pre_provisioning_lambda
        )
        
        iot_events_stack = IotEventsStack(
            self, "IotEvents", env_params=env_params, 
            iot_events_execution_role= iam_stack.iot_events_execution_role,
            sprinkler_off_topic= sns_stack.sprinkler_off_topic,
            sprinkler_on_topic= sns_stack.sprinkler_on_topic,
            sprinkler_off_lambda= lambda_stack.sprinkler_off_lambda,
            sprinkler_on_lambda= lambda_stack.sprinkler_on_lambda
        )
        
        iot_analytics_stack = IotAnalyticsStack(
            self, "IotAnalytics", env_params=env_params,
            cw_put_metric_lambda= lambda_stack.cw_put_metric_lambda
        )
        
        iot_rules_engine_stack = IotRulesEngineStack(
            self, "IotRulesEngine", env_params=env_params,
            iot_events_rules_engine_role= iam_stack.iot_events_rules_engine_role,
            iot_analytics_rules_engine_role= iam_stack.iot_analytics_rules_engine_role,
            iot_events_input= iot_events_stack.iot_events_input,
            sensor_data_channel= iot_analytics_stack.sensor_data_channel,
            sprinkler_off_channel= iot_analytics_stack.sprinkler_off_channel,
            sprinkler_on_channel= iot_analytics_stack.sprinkler_on_channel,
            cert_rotation_complete_lambda= lambda_stack.cert_rotation_complete_lambda,
            thing_firmware_update_lambda= lambda_stack.thing_firmware_update_lambda,
            device_cert_rotation_container= lambda_container_stack.device_cert_rotation_container
        )
        
        iot_jobs_stack= IotJobsStack(
            self, "IotJobs", env_params=env_params,
            devices_bucket= s3_stack.devices_bucket,
            devices_bucket_deploy= s3_stack.devices_bucket_deploy
        )
        
        custom_resource_stack = CustomResourceStack(
            self, "CustomResource", env_params=env_params,
            devices_bucket= s3_stack.devices_bucket,
            claim_policy= iot_provisioning_stack.claim_policy,
            provisioning_template= iot_provisioning_stack.provisioning_template,
            group_policy= iot_provisioning_stack.group_policy,
            dd_audit_role= iam_stack.dd_audit_role,
            dd_audit_topic= sns_stack.dd_audit_topic,
            dd_sns_publish_role= iam_stack.dd_sns_publish_role,
            iot_jobs_policy= iot_provisioning_stack.iot_jobs_policy,
            iot_cert_rotation_job_template= iot_jobs_stack.iot_cert_rotation_job_template,
            custom_cert_rotation_job_template= iot_jobs_stack.custom_cert_rotation_job_template,
            ota_update_lambda= lambda_stack.ota_update_lambda,
            verification_lambda_container= lambda_container_stack.verification_lambda_container,
            iot_jitp_template_role= iam_stack.iot_jitp_template_role,
            ota_update_role= iam_stack.ota_update_role
        )
        
        iot_device_defender_stack = IotDeviceDefenderStack(
            self, "IotDeviceDefender", env_params=env_params,
            custom_resource= custom_resource_stack.custom_resource,
            dd_sns_publish_role= iam_stack.dd_sns_publish_role,
            dd_mitigation_action_role= iam_stack.dd_mitigation_action_role,
            dd_audit_role= iam_stack.dd_audit_role,
            dd_audit_topic= sns_stack.dd_audit_topic,
            dd_defend_topic= sns_stack.dd_defend_topic
        )
        
        iot_fleet_hub_stack= IotFleetHubStack(
            self, "IotFleetHub", env_params=env_params,
            fleet_hub_app_role= iam_stack.fleet_hub_app_role,
            custom_resource= custom_resource_stack.custom_resource
        )