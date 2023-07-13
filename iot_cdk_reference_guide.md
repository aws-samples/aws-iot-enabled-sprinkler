
# IoT CDK Reference Guide

This document provides information on how to create resources in AWS IoT and AWS IoT Services using the AWS CDK.

---

<details>
  <summary>AWS IoT Policy Document</summary>
  
  ## AWS IoT Policy Document

Python CDK documentation link: https://docs.aws.amazon.com/cdk/api/v1/python/aws_cdk.aws_iot/CfnPolicy.html

Sample from project:

```
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

# Create Group Policy
group_policy = iot.CfnPolicy(self, "GroupPolicy",
    policy_document=group_policy_document,
    policy_name=env_params['group_policy']['policy_name']
)
```
</details>

---

<details>
  <summary>AWS IoT Fleet Provisining Template</summary>
  
  ## AWS IoT Fleet Provisining Template

Python CDK documentation link: https://docs.aws.amazon.com/cdk/api/v1/python/aws_cdk.aws_iot/CfnProvisioningTemplate.html

Sample from project:
```
# Import provisioning template
f = open('provisioning_template/provisioning_template.json')
provisioning_template_body= json.load(f)


# Add group name to template
provisioning_template_body["Resources"]["thing"]["Properties"]["ThingGroups"][0] = env_params['static_thing_group']['group_name']
provisioning_template_body["Resources"]["thing"]["Properties"]["ThingTypeName"] = env_params['thing_type']['thing_type_name']


provisioning_template = iot.CfnProvisioningTemplate(self, "ProvisioningTemplate",
    provisioning_role_arn=provisioning_template_role.role_arn,
    template_body=json.dumps(provisioning_template_body),
    description="Template to Rotate Certificates on IoT Enabled Sprinklers",
    enabled=True,
    pre_provisioning_hook=iot.CfnProvisioningTemplate.ProvisioningHookProperty(
        target_arn=pre_provisioning_lambda.function_arn
    ),
    template_name=env_params['template']['provisioning_template_name']
)
# Add dependency
provisioning_template.node.add_dependency(group_policy)
```

Provisioning Template File *provisioning_template.json*:
```
{
    "Parameters": {
        "CertificateCreatedOn": {
            "Type": "String"
        },
        "SerialNumber": {
            "Type": "String"
        },
        "AWS::IoT::Certificate::Id": {
            "Type": "String"
        },
        "SensorType": {
            "Type": "String"
        },
        "PlantId": {
            "Type": "String"
        },
        "FirmwareVersion": {
            "Type": "String"
        }
    },
    "Resources": {
        "certificate": {
            "Type": "AWS::IoT::Certificate",
            "Properties": {
                "CertificateId": {
                    "Ref": "AWS::IoT::Certificate::Id"
                },
                "Status": "Active"
            }
        },
        "thing": {
            "Type": "AWS::IoT::Thing",
            "Properties": {
                "AttributePayload": {
                    "FirmwareVersion": {
                        "Ref": "FirmwareVersion"
                    },
                    "SensorType": {
                        "Ref": "SensorType"
                    },
                    "PlantId": {
                        "Ref": "PlantId"
                    },
                    "CertificateCreatedOn": {
                        "Ref": "CertificateCreatedOn"
                    }
                },
                "ThingTypeName": "thing_type_name",
                "ThingName": {
                    "Ref": "SerialNumber"
                },
                "ThingGroups": [
                    "group_name"
                ]
            }
        }
    }
}
```
</details>


---

<details>
  <summary>Fleet Hub Application</summary>

  ## Fleet Hub Application

Python CDK documentation link: https://docs.aws.amazon.com/cdk/api/v1/python/aws_cdk.aws_iotfleethub/CfnApplication.html

Sample from project:

```
fleet_hub_app = iotfleethub.CfnApplication(self, "FleetHubApp",
    application_name= env_params['fleet_hub']['application'],
    role_arn= fleet_hub_app_role.role_arn,
    application_description="FleetHub App created as part of IoT Enabled Sprinklers project stack"
)
```
</details>

---

<details>
  <summary>AWS IoT Jobs Template</summary>
  
## AWS IoT Jobs Template

Python CDK documentation link: https://docs.aws.amazon.com/cdk/api/v1/python/aws_cdk.aws_iot/CfnJobTemplate.html

Sample from project:

```
cacert_rotation_job_template = iot.CfnJobTemplate(self, "CaCertRotationTemplate",
    description="IoT Jobs tempalte that will rotate a device's RootCA upon given a URL",
    job_template_id= env_params['iot_jobs']['cacert_jobs_template_id'],
    document_source= "https://" + devices_bucket.bucket_name + ".s3.ap-southeast-2.amazonaws.com/" + env_params['iot_jobs']['cacert_job_document_path']
)
# Add dependency
cacert_rotation_job_template.node.add_dependency(devices_bucket)
cacert_rotation_job_template.node.add_dependency(devices_bucket_deploy)
```
  
</details>

---

<details>
  <summary>AWS IoT Rules Engine</summary>
  
  ## AWS IoT Rules Engine

  Python CDK documentation link: https://docs.aws.amazon.com/cdk/api/v1/python/aws_cdk.aws_iot/TopicRule.html

  Samples from project:

  <details>
    <summary>Create Topic Rule with AWS IoT Events Action</summary>

```
soil_moisture_events_sensordata_rule = iot.CfnTopicRule(self, "SoilMoistureEventsSensorData",
    rule_name= env_params['iot_rules_engine']['soil_moisture_events_sensordata_rule_name'],
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
```
  </details>


  <details>
    <summary>Create Topic Rule with AWS IoT Analytics Action</summary>

```
soil_moisture_analytics_sensordata_rule= iot.CfnTopicRule(self, "SoilMoistureAnalyticsSensorData",
    rule_name= env_params['iot_rules_engine']['soil_moisture_analytics_sensordata_rule_name'],
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
```
  </details>

  <details>
    <summary>Create Topic Rule with AWS Lambda Action</summary>

```
cert_rotation_complete_rule= iot.CfnTopicRule(self, "UpdateFirmwareAttribute",
    rule_name= env_params['iot_rules_engine']['update_firmware_attribute_rule_name'],
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
```
  </details>

</details>


---

<details>
  <summary>AWS IoT Events</summary>
  
  ## AWS IoT Events

  <details>
    <summary>Input</summary>

Python CDK documentation link: https://docs.aws.amazon.com/cdk/api/v1/python/aws_cdk.aws_iotevents/CfnInput.html

Sample from project:

```
iot_events_input = iotevents.CfnInput(self, "IotEventsInput",
    input_name=env_params['iotevents']['input']['input_name'],
    input_description="Input data coming from sprinkler's soil moisture sensor",
    input_definition={
        "attributes": [
            {
                "jsonPath": "sensorReportedState"
            },
            {
                "jsonPath": "sensorType"
            },
            {
                "jsonPath": "deviceID"
            },
            {
                "jsonPath":"sensorReportedMoisturePercentage"
            }
        ]
    }
)
```
  </details>
  <details>
    <summary>Detector Model</summary>

Python CDK documentation link: https://docs.aws.amazon.com/cdk/api/v1/python/aws_cdk.aws_iotevents/CfnDetectorModel.html

Sample from project:

```
iot_events_detector_model = iotevents.CfnDetectorModel(self, "IotEventsDetectorModel",
    detector_model_name= env_params['iotevents']['detector_model']['detector_model_name'],
    role_arn= iot_events_execution_role.role_arn,
    detector_model_description= "Detector model for IoT Enabled Sprinkler",
    evaluation_method= "BATCH",
    key= "deviceID",
    detector_model_definition= iotevents.CfnDetectorModel.DetectorModelDefinitionProperty(
        initial_state_name="SprinklerOff",
        states=[
            iotevents.CfnDetectorModel.StateProperty(
                state_name="SprinklerOff",
                on_enter=iotevents.CfnDetectorModel.OnEnterProperty(
                    events=[
                        iotevents.CfnDetectorModel.EventProperty(
                            event_name="InitializeInputValue",
                            condition="true",
                            actions=[
                                iotevents.CfnDetectorModel.ActionProperty(
                                    set_variable=iotevents.CfnDetectorModel.SetVariableProperty(
                                        variable_name="InputValue",
                                        value="0"
                                    )
                                )
                            ]
                        )
                    ]
                ),
                on_input=iotevents.CfnDetectorModel.OnInputProperty(
                    events=[
                        iotevents.CfnDetectorModel.EventProperty(
                            event_name="NormalToError",
                            condition='$input.{}.sensorReportedState == "dry"'.format(iot_events_input.input_name),
                            actions=[
                                iotevents.CfnDetectorModel.ActionProperty(
                                    set_variable=iotevents.CfnDetectorModel.SetVariableProperty(
                                        variable_name="InputValue",
                                        value="$variable.InputValue + 1"
                                    )
                                )
                            ]
                        ),
                        iotevents.CfnDetectorModel.EventProperty(
                            event_name="ErrorToNormal",
                            condition='$input.{}.sensorReportedState == "hydrated"'.format(iot_events_input.input_name),
                            actions=[
                                iotevents.CfnDetectorModel.ActionProperty(
                                    set_variable=iotevents.CfnDetectorModel.SetVariableProperty(
                                        variable_name="InputValue",
                                        value="0"
                                    )
                                )
                            ]
                        ),
                    ],
                    transition_events=[
                        iotevents.CfnDetectorModel.TransitionEventProperty(
                            event_name="OnTransition",
                            condition="$variable.InputValue > 4",
                            next_state="SprinklerOn",
                            actions=[
                                iotevents.CfnDetectorModel.ActionProperty(
                                    sns=iotevents.CfnDetectorModel.SnsProperty(
                                        target_arn=sprinkler_on_topic.topic_arn
                                    )
                                )
                            ]
                        )
                    ]
                ),
                on_exit=iotevents.CfnDetectorModel.OnExitProperty(
                    events=[]
                )
            ),
            iotevents.CfnDetectorModel.StateProperty(
                state_name="SprinklerOn",
                on_enter=iotevents.CfnDetectorModel.OnEnterProperty(
                    events=[
                        iotevents.CfnDetectorModel.EventProperty(
                            event_name="InitializeInputValue",
                            condition="true",
                            actions= [
                                iotevents.CfnDetectorModel.ActionProperty(
                                    set_variable=iotevents.CfnDetectorModel.SetVariableProperty(
                                        variable_name="InputValue",
                                        value="0"
                                    )
                                )
                            ]
                        )
                    ]
                ),
                on_input=iotevents.CfnDetectorModel.OnInputProperty(
                    events=[
                        iotevents.CfnDetectorModel.EventProperty(
                            event_name="ErrorToNormal",
                            condition='$input.{}.sensorReportedState == "hydrated"'.format(iot_events_input.input_name),
                            actions=[
                                iotevents.CfnDetectorModel.ActionProperty(
                                    set_variable=iotevents.CfnDetectorModel.SetVariableProperty(
                                        variable_name="InputValue",
                                        value="$variable.InputValue + 1"
                                    )
                                )
                            ]
                        ),
                        iotevents.CfnDetectorModel.EventProperty(
                            event_name="NormalToError",
                            condition='$input.{}.sensorReportedState == "dry"'.format(iot_events_input.input_name),
                            actions=[
                                iotevents.CfnDetectorModel.ActionProperty(
                                    set_variable=iotevents.CfnDetectorModel.SetVariableProperty(
                                        variable_name="InputValue",
                                        value="0"
                                    )
                                )
                            ]
                        ),
                    ],
                    transition_events=[
                        iotevents.CfnDetectorModel.TransitionEventProperty(
                            event_name="OffTransition",
                            condition="$variable.InputValue > 4",
                            next_state="SprinklerOff",
                            actions=[
                                iotevents.CfnDetectorModel.ActionProperty(
                                    sns=iotevents.CfnDetectorModel.SnsProperty(
                                        target_arn=sprinkler_off_topic.topic_arn
                                    )
                                )
                            ]
                        )
                    ],
                ),
                on_exit=iotevents.CfnDetectorModel.OnExitProperty(
                    events=[]
                )
            )
        ]
    )
)
# Add dependency
iot_events_detector_model.node.add_dependency(iot_events_input)
iot_events_detector_model.node.add_dependency(sprinkler_on_topic)
iot_events_detector_model.node.add_dependency(sprinkler_off_topic)
```
  </details>
</details>

---

<details>
  <summary>AWS IoT Analytics</summary>
  
  ## AWS IoT Analytics

  To create a full pipeline in AWS IoT Analytics, we need to create 4 resources: Channel, Datastore, Pipeline, and Data Set, in that order since to create a Pipeline, we need both a Channel and a Datastore.

  <details>
  	<summary>Creating a Channel</summary>

Python CDK documentation link: https://docs.aws.amazon.com/cdk/api/v1/python/aws_cdk.aws_iotanalytics/CfnChannel.html

Sample from project:

```
sprinkler_off_channel = iotanalytics.CfnChannel(self, "SprinklerOffChannel",
	channel_name= env_params['iotanalytics']['channel']['sprinkler_off_channel_name'],
	retention_period= iotanalytics.CfnChannel.RetentionPeriodProperty(
		number_of_days=5,
		unlimited=False
	)
)
```
  </details>

  <details>
  	<summary>Creating a Data Store</summary>

Python CDK documentation link: https://docs.aws.amazon.com/cdk/api/v1/python/aws_cdk.aws_iotanalytics/CfnPipeline.html

Sample from project:

```
sprinkler_off_datastore = iotanalytics.CfnDatastore(self, "SprinklerOffDatastore",
    datastore_name= env_params['iotanalytics']['datastore']['sprinkler_off_datastore'],
    retention_period=iotanalytics.CfnDatastore.RetentionPeriodProperty(
        number_of_days=5,
        unlimited=False
    )
)
```

  </details>

  <details>
  	<summary>Creating a Pipeline</summary>

Python CDK documentation link: https://docs.aws.amazon.com/cdk/api/v1/python/aws_cdk.aws_iotanalytics/CfnPipeline.html


Sample from project:

```
sprinkler_off_pipeline_name = iotanalytics.CfnPipeline(self, "SprinklerOffPipeline",
    pipeline_name= env_params['iotanalytics']['pipeline']['sprinkler_off_pipeline_name'],
    pipeline_activities= [
        iotanalytics.CfnPipeline.ActivityProperty(
            channel= iotanalytics.CfnPipeline.ChannelProperty(
                name= "PA_Sprinkler_Off_Channel_1",
                channel_name= sprinkler_off_channel.channel_name,
                next= "PA_Sprinkler_Off_MathActivity_1"
            ),
        ),
        iotanalytics.CfnPipeline.ActivityProperty(
            math= iotanalytics.CfnPipeline.MathProperty(
                name= "PA_Sprinkler_Off_MathActivity_1",
                attribute= "duration_s",
                math= "duration_ms/1000",
                next= "PA_Sprinkler_Off_MathActivity_2"
            )
        ),
        iotanalytics.CfnPipeline.ActivityProperty(
            math= iotanalytics.CfnPipeline.MathProperty(
                name= "PA_Sprinkler_Off_MathActivity_2",
                attribute= "waterFlowed_l",
                math= "trunc(((flow_rate*1000)*duration_s),2)",
                next= "PA_Sprinkler_Off_RemoveAttributesActivity_1"
            )
        ),
        iotanalytics.CfnPipeline.ActivityProperty(
            remove_attributes= iotanalytics.CfnPipeline.RemoveAttributesProperty(
                name= "PA_Sprinkler_Off_RemoveAttributesActivity_1",
                attributes= [
                    "duration_ms",
                    "flow_rate"
                ],
                next= "PA_Sprinkler_Off_LambdaCwActivity_1"
            )
        ),
        iotanalytics.CfnPipeline.ActivityProperty(
            lambda_= iotanalytics.CfnPipeline.LambdaProperty(
                name= "PA_Sprinkler_Off_LambdaCwActivity_1",
                lambda_name= cw_put_metric_lambda.function_name,
                batch_size=1,
                next= "PA_Sprinkler_Off_Datastore_1"
            )
        ),
        iotanalytics.CfnPipeline.ActivityProperty(
            datastore= iotanalytics.CfnPipeline.DatastoreProperty(
                name= "PA_Sprinkler_Off_Datastore_1",
                datastore_name= sprinkler_off_datastore.datastore_name
            )
        )
    ]
)
# Add dependency
sprinkler_off_pipeline_name.node.add_dependency(sprinkler_off_channel)
sprinkler_off_pipeline_name.node.add_dependency(sprinkler_off_datastore)
sprinkler_off_pipeline_name.node.add_dependency(cw_put_metric_lambda)
```

  </details>

  <details>
  	<summary>Creating a Data Set</summary>

Python CDK documentation link: https://docs.aws.amazon.com/cdk/api/v1/python/aws_cdk.aws_iotanalytics/CfnDataset.html

Sample from project:

```
sprinkler_off_dataset = iotanalytics.CfnDataset(self, "SprinklerOffDataset",
    dataset_name= env_params['iotanalytics']['dataset']['sprinkler_off_dataset_name'],
    actions= [
        iotanalytics.CfnDataset.ActionProperty(
            action_name= "DA_SprinklerOff_Query_1",
            query_action= iotanalytics.CfnDataset.QueryActionProperty(
                sql_query= "SELECT * FROM {}".format(sprinkler_off_datastore.datastore_name)
            )
        )
    ],
    triggers= [
        iotanalytics.CfnDataset.TriggerProperty(
            schedule= iotanalytics.CfnDataset.ScheduleProperty(
                schedule_expression= "cron(0/5 * * * ? *)"
            )
        )
    ],
    retention_period= iotanalytics.CfnDataset.RetentionPeriodProperty(
        number_of_days= 5,
        unlimited=False
    )
)
# Add dependency
sprinkler_off_dataset.node.add_dependency(sprinkler_off_datastore)
```
  </details>
</details>

---

<details>
  <summary>AWS IoT Device Defender</summary>
  
  ## AWS IoT Device Defender

  <details>
    <summary>Device Defender Audit Schedule</summary>

Python CDK documentation link: https://docs.aws.amazon.com/cdk/api/v1/python/aws_cdk.aws_iot/CfnScheduledAudit.html

Sample from project:
```
dd_scheduled_audit = iot.CfnScheduledAudit(self, "DDScheduledAudit",
    scheduled_audit_name=env_params['device_defender']['scheduled_audit_name'],
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
```
  </details>

  <details>
    <summary>Device Defender ML Security Profile</summary>

Python CDK documentation link: https://docs.aws.amazon.com/cdk/api/v1/python/aws_cdk.aws_iot/CfnSecurityProfile.html

Sample from project:
```
dd_ml_security_profile = iot.CfnSecurityProfile(self, "DDMlSecurityProfile",
    target_arns=[
        "arn:aws:iot:{}:{}:thinggroup/{}".format(env_params['region'], env_params['account_id'], env_params['static_thing_group']['group_name'])
    ],
    security_profile_name= env_params['device_defender']['ml_security_profile_name'],
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

```
  </details>

  <details>
    <summary>Device Defender Mitigation Action</summary>

Python CDK documentation link: https://docs.aws.amazon.com/cdk/api/v1/python/aws_cdk.aws_iot/CfnMitigationAction.html

Sample from project:
```
dd_mitigation_action = iot.CfnMitigationAction(self, "DDMitigationAction",
    action_name=env_params['device_defender']['mitigation_action'],
    action_params=iot.CfnMitigationAction.ActionParamsProperty(
        add_things_to_thing_group_params=iot.CfnMitigationAction.AddThingsToThingGroupParamsProperty(
            thing_group_names=[
                env_params['device_defender']['quarantine_group']
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
```
  </details>
</details>

---

<details>
  <summary>Custom Resource</summary>
  
  ## Custom Resource

Lots of AWS IoT resources can't be created, and lots of actions cannot be executed via CDK/Cloudformation such as creating thing groups, attaching policies, creating jobs, etc. For this you need to create a custom resource, and make API Calls.

Python CDK documentation link: https://docs.aws.amazon.com/cdk/api/v1/python/aws_cdk.core/CfnCustomResource.html#cfncustomresource

Sample from project:

```
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
                .
                .
                "iot:ListThings",
                "iot:UpdateThing",
            ],
            resources=["*"]
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
        )
    ]
)
custom_resource_lambda_policy = iam.Policy(self, "LambdaCustomResourcePolicy",
    document=custom_resource_lambda_policy_statement
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
        openssl_layer
    ],
    environment= {
        "ROOTCA_URL": env_params['rootCa']['url'] + env_params['name'],
        "CLAIM_POLICY_NAME": claim_policy.policy_name,
        "S3_BUCKET_NAME": devices_bucket.bucket_name,
        .
        .
        "CUSTOM_CERTIFICATE_ROTATION_JOB_ID": env_params['iot_jobs']['custom_certificate_rotation_job_id'] + env_params['name']
    }
)
onEvent.role.attach_inline_policy(custom_resource_lambda_policy)

# Add dependency for resources referred in the function
onEvent.node.add_dependency(claim_policy)
.
.
onEvent.node.add_dependency(ota_update_lambda)

# Create custom resource
provider = cr.Provider(self, "CustomResourceProvider",
    on_event_handler=onEvent,
    log_retention= logs.RetentionDays.ONE_DAY
)
custom_resource = cloudformation.CfnCustomResource(self, "CfnCustomResource",
    service_token=provider.service_token
)
```

  Custom Resource Lambda Function *lambda/custom_resource/lambda_function.py*:

```
import json
import requests
.
.
from uuid import uuid4

iot = boto3.client('iot')
s3 = boto3.resource('s3')
.
.
_lambda = boto3.client('lambda')

def lambda_handler(event, context):
    
    # Get variables from environment variable
    TEMPLATE_NAME= os.environ.get('TEMPLATE_NAME')
    .
    .
    DD_SNS_PUBLISH_ROLE= os.environ.get('DD_SNS_PUBLISH_ROLE')
    THING_TYPE_NAME= os.environ.get('THING_TYPE_NAME')
    # Define bucket 
    BUCKET = s3.Bucket(S3_BUCKET_NAME)
    
    if event['RequestType']=='Create':
        
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
        
        ..
        ..

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
        
    if event['RequestType']=='Delete':
        
        ###################################
        # Get claim certificate
        ###################################
        list_target_response = iot.list_targets_for_policy(
            policyName=CLAIM_POLICY_NAME,
        )
        CERTIFICATE_ARN= list_target_response['targets'][0]
        CERTIFICATE_ID= CERTIFICATE_ARN.split('/')[1]

        ..
        ..
        
        ###################################
        # Detach policy from certificate
        ###################################
        response = iot.detach_policy(
            policyName=CLAIM_POLICY_NAME,
            target=CERTIFICATE_ARN
        )
    
    return {
        'statusCode': 200,
        'body': json.dumps('Executing Custom Resource!')
    }
```


---
