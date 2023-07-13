from aws_cdk import (
    Stack,
    aws_sns as sns,
    aws_iotevents as iotevents,
    aws_iam as iam,
    aws_lambda as _lambda
)
import aws_cdk as cdk
from constructs import Construct

class IotEventsStack(Construct):
    
    def __init__(self, scope: Construct, id: str, env_params: dict, 
                    iot_events_execution_role: iam.Role,
                    sprinkler_off_topic: sns.Topic,
                    sprinkler_on_topic: sns.Topic,
                    sprinkler_off_lambda: _lambda.Function,
                    sprinkler_on_lambda: _lambda.Function,
                    **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        

        iot_events_input = iotevents.CfnInput(self, "IotEventsInput",
            input_name= env_params['name'] + env_params['iotevents']['input']['input_name'],
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
        
        
        # Create detector model
        iot_events_detector_model = iotevents.CfnDetectorModel(self, "IotEventsDetectorModel",
            detector_model_name= env_params['name'] + env_params['iotevents']['detector_model']['detector_model_name'],
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
                                        # iotevents.CfnDetectorModel.ActionProperty(
                                        #     lambda_=iotevents.CfnDetectorModel.LambdaProperty(
                                        #         function_arn=sprinkler_on_lambda.function_arn,
                                        #     )
                                        # ),
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
                                        # iotevents.CfnDetectorModel.ActionProperty(
                                        #     lambda_=iotevents.CfnDetectorModel.LambdaProperty(
                                        #         function_arn=sprinkler_off_lambda.function_arn,
                                        #     )
                                        # ),
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
        
        
        self.iot_events_input = iot_events_input