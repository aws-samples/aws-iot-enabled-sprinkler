from aws_cdk import (
    Stack,
    aws_iotanalytics as iotanalytics,
    aws_iam as iam,
    aws_iotevents as iotevents,
    aws_iot as iot,
    aws_lambda as _lambda,
)
import aws_cdk as cdk
from constructs import Construct

class IotRulesEngineStack(Construct):
    def __init__(self, scope: Construct, construct_id: str,
                iot_events_rules_engine_role: iam.Role,
                iot_analytics_rules_engine_role: iam.Role,
                iot_events_input: iotevents.CfnInput,
                sensor_data_channel: iotanalytics.CfnChannel,
                sprinkler_off_channel: iotanalytics.CfnChannel,
                sprinkler_on_channel: iotanalytics.CfnChannel,
                cert_rotation_complete_lambda: _lambda.Function,
                thing_firmware_update_lambda: _lambda.Function,
                device_cert_rotation_container: _lambda.Function,
                env_params: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        
        soil_moisture_events_sensordata_rule = iot.CfnTopicRule(self, "SoilMoistureEventsSensorData",
            rule_name= env_params['name'] + env_params['iot_rules_engine']['soil_moisture_events_sensordata_rule_name'],
            topic_rule_payload= iot.CfnTopicRule.TopicRulePayloadProperty(
                sql= "select * from '+/sensordata/soil_moisture'",
                aws_iot_sql_version="2016-03-23",
                actions= [
                    iot.CfnTopicRule.ActionProperty(
                        iot_events= iot.CfnTopicRule.IotEventsActionProperty(
                            input_name= iot_events_input.input_name,
                            role_arn= iot_events_rules_engine_role.role_arn
                        )
                    )
                ],
                rule_disabled= False
            )
        )
        # Add dependency
        soil_moisture_events_sensordata_rule.node.add_dependency(iot_events_input)
        
        soil_moisture_analytics_sensordata_rule= iot.CfnTopicRule(self, "SoilMoistureAnalyticsSensorData",
            rule_name= env_params['name'] + env_params['iot_rules_engine']['soil_moisture_analytics_sensordata_rule_name'],
            topic_rule_payload= iot.CfnTopicRule.TopicRulePayloadProperty(
                sql= "SELECT *, parse_time(\"yyyy-MM-dd'T'HH:mm:ss.SSSZ\", timestamp()) as RealTime FROM '+/sensordata/soil_moisture'",
                aws_iot_sql_version="2016-03-23",
                actions= [
                    iot.CfnTopicRule.ActionProperty(
                        iot_analytics= iot.CfnTopicRule.IotAnalyticsActionProperty(
                            channel_name= sensor_data_channel.channel_name,
                            role_arn= iot_analytics_rules_engine_role.role_arn
                        )
                    )
                ],
                rule_disabled= False
            )
        )
        # Add dependency
        soil_moisture_analytics_sensordata_rule.node.add_dependency(sensor_data_channel)
        
        sprinkler_off_rule= iot.CfnTopicRule(self, "SprinklerOff",
            rule_name= env_params['name'] + env_params['iot_rules_engine']['sprinkler_off_rule_name'],
            topic_rule_payload= iot.CfnTopicRule.TopicRulePayloadProperty(
                sql= "SELECT *, parse_time(\"yyyy-MM-dd'T'HH:mm:ss.SSSZ\", timestamp()) as RealTime FROM '+/sprinkler/off'",
                aws_iot_sql_version="2016-03-23",
                actions= [
                    iot.CfnTopicRule.ActionProperty(
                        iot_analytics= iot.CfnTopicRule.IotAnalyticsActionProperty(
                            channel_name= sprinkler_off_channel.channel_name,
                            role_arn= iot_analytics_rules_engine_role.role_arn
                        )
                    )
                ],
                rule_disabled= False
            )
        )
        # Add dependency
        sprinkler_off_rule.node.add_dependency(sprinkler_off_channel)
        
        sprinkler_on_rule= iot.CfnTopicRule(self, "SprinklerOn",
            rule_name= env_params['name'] + env_params['iot_rules_engine']['sprinkler_on_rule_name'],
            topic_rule_payload= iot.CfnTopicRule.TopicRulePayloadProperty(
                sql= "SELECT *, parse_time(\"yyyy-MM-dd'T'HH:mm:ss.SSSZ\", timestamp()) as RealTime FROM '+/sprinkler/on'",
                aws_iot_sql_version="2016-03-23",
                actions= [
                    iot.CfnTopicRule.ActionProperty(
                        iot_analytics= iot.CfnTopicRule.IotAnalyticsActionProperty(
                            channel_name= sprinkler_on_channel.channel_name,
                            role_arn= iot_analytics_rules_engine_role.role_arn
                        )
                    )
                ],
                rule_disabled= False
            )
        )
        # Add dependency
        sprinkler_on_rule.node.add_dependency(sprinkler_on_channel)
        
        cert_rotation_complete_rule= iot.CfnTopicRule(self, "CertificateRotationCompleteRule",
            rule_name= env_params['name'] + env_params['iot_rules_engine']['cert_rotation_complete_rule_name'],
            topic_rule_payload= iot.CfnTopicRule.TopicRulePayloadProperty(
                sql= "SELECT * FROM '+/certificate/rotation/complete'",
                aws_iot_sql_version="2016-03-23",
                actions= [
                    iot.CfnTopicRule.ActionProperty(
                        lambda_=iot.CfnTopicRule.LambdaActionProperty(
                            function_arn= cert_rotation_complete_lambda.function_arn
                        )
                    )
                ],
                rule_disabled= False
            )
        )
        # Add dependency
        cert_rotation_complete_rule.node.add_dependency(cert_rotation_complete_lambda)
    
        cert_rotation_complete_rule= iot.CfnTopicRule(self, "UpdateFirmwareAttribute",
            rule_name= env_params['name'] + env_params['iot_rules_engine']['update_firmware_attribute_rule_name'],
            topic_rule_payload= iot.CfnTopicRule.TopicRulePayloadProperty(
                sql= "SELECT * FROM '$aws/events/jobExecution/+/succeeded' WHERE startswith(topic(4),'AFR_OTA-IotEnabledSprinklers_OTA_UPDATE_') = true",
                aws_iot_sql_version="2016-03-23",
                actions= [
                    iot.CfnTopicRule.ActionProperty(
                        lambda_=iot.CfnTopicRule.LambdaActionProperty(
                            function_arn= thing_firmware_update_lambda.function_arn
                        )
                    )
                ],
                rule_disabled= False
            )
        )
        # Add dependency
        cert_rotation_complete_rule.node.add_dependency(thing_firmware_update_lambda)
        
        
        # Rule to create new certs using custom root ca
        custom_cert_creation_create_rule= iot.CfnTopicRule(self, "CustomCaCreateCert",
            rule_name= env_params['name'] + env_params['iot_rules_engine']['custom_cert_creation_create_rule'],
            topic_rule_payload= iot.CfnTopicRule.TopicRulePayloadProperty(
                sql= 'SELECT {"thingName": topic(1)} FROM "+/customCa/certificate/create/initiate" ',
                aws_iot_sql_version="2016-03-23",
                actions= [
                    iot.CfnTopicRule.ActionProperty(
                        lambda_=iot.CfnTopicRule.LambdaActionProperty(
                            function_arn= device_cert_rotation_container.function_arn
                        )
                    )
                ],
                rule_disabled= False
            )
        )
        # Add dependency
        cert_rotation_complete_rule.node.add_dependency(device_cert_rotation_container)