from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_iotanalytics as iotanalytics
)
import aws_cdk as cdk
from constructs import Construct

class IotAnalyticsStack(Construct):
    def __init__(self, scope: Construct, construct_id: str,
                env_params: dict, 
                cw_put_metric_lambda: _lambda.Function,
                **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create Channels
        sensor_data_channel = iotanalytics.CfnChannel(self, "SensorDataChannel",
            channel_name= env_params['name'] + env_params['iotanalytics']['channel']['sensor_data_channel_name'],
            retention_period= iotanalytics.CfnChannel.RetentionPeriodProperty(
                number_of_days=5,
                unlimited=False
            )
        )
        
        sprinkler_off_channel = iotanalytics.CfnChannel(self, "SprinklerOffChannel",
            channel_name= env_params['name'] + env_params['iotanalytics']['channel']['sprinkler_off_channel_name'],
            retention_period= iotanalytics.CfnChannel.RetentionPeriodProperty(
                number_of_days=5,
                unlimited=False
            )
        )
        
        sprinkler_on_channel = iotanalytics.CfnChannel(self, "SprinklerOnChannel",
            channel_name= env_params['name'] + env_params['iotanalytics']['channel']['sprinkler_on_channel_name'],
            retention_period= iotanalytics.CfnChannel.RetentionPeriodProperty(
                number_of_days=5,
                unlimited=False
            )
        )
        
        # Create Datastore
        sensor_data_datastore = iotanalytics.CfnDatastore(self, "SensorDataDatastore",
            datastore_name= env_params['name'] + env_params['iotanalytics']['datastore']['sensor_data_datastore_name'],
            retention_period=iotanalytics.CfnDatastore.RetentionPeriodProperty(
                number_of_days=5,
                unlimited=False
            )
        )
        
        sprinkler_off_datastore = iotanalytics.CfnDatastore(self, "SprinklerOffDatastore",
            datastore_name= env_params['name'] + env_params['iotanalytics']['datastore']['sprinkler_off_datastore'],
            retention_period=iotanalytics.CfnDatastore.RetentionPeriodProperty(
                number_of_days=5,
                unlimited=False
            )
        )
        
        sprinkler_on_datastore = iotanalytics.CfnDatastore(self, "SprinklerOnDatastore",
            datastore_name= env_params['name'] + env_params['iotanalytics']['datastore']['sprinkler_on_datastore'],
            retention_period=iotanalytics.CfnDatastore.RetentionPeriodProperty(
                number_of_days=5,
                unlimited=False
            )
        )
        
        # Create Pipeline
        sensor_data_pipeline_name= iotanalytics.CfnPipeline(self, "SensorDataPipeline",
            pipeline_name= env_params['name'] + env_params['iotanalytics']['pipeline']['sensor_data_pipeline_name'],
            pipeline_activities= [
                iotanalytics.CfnPipeline.ActivityProperty(
                    channel= iotanalytics.CfnPipeline.ChannelProperty(
                        name= "PA_SM_Data_Channel_1",
                        channel_name= sensor_data_channel.channel_name,
                        next= "PA_SM_Data_Datastore_1"
                    ),
                    datastore= iotanalytics.CfnPipeline.DatastoreProperty(
                        name= "PA_SM_Data_Datastore_1",
                        datastore_name= sensor_data_datastore.datastore_name
                    )
                )
            ]
        )
        # Add dependency
        sensor_data_pipeline_name.node.add_dependency(sensor_data_channel)
        sensor_data_pipeline_name.node.add_dependency(sensor_data_datastore)
        
        
        sprinkler_off_pipeline_name = iotanalytics.CfnPipeline(self, "SprinklerOffPipeline",
            pipeline_name= env_params['name'] + env_params['iotanalytics']['pipeline']['sprinkler_off_pipeline_name'],
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
        
        sprinkler_on_pipeline_name = iotanalytics.CfnPipeline(self, "SprinklerOnPipeline",
            pipeline_name= env_params['name'] + env_params['iotanalytics']['pipeline']['sprinkler_on_pipeline_name'],
            pipeline_activities= [
                iotanalytics.CfnPipeline.ActivityProperty(
                    channel= iotanalytics.CfnPipeline.ChannelProperty(
                        name= "PA_Sprinkler_On_Channel_1",
                        channel_name= sprinkler_on_channel.channel_name,
                        next= "PA_Sprinkler_On_Datastore_1"
                    ),
                    datastore= iotanalytics.CfnPipeline.DatastoreProperty(
                        name= "PA_Sprinkler_On_Datastore_1",
                        datastore_name= sprinkler_on_datastore.datastore_name
                    )
                )
            ]
        )
        # Add dependency
        sprinkler_on_pipeline_name.node.add_dependency(sprinkler_on_channel)
        sprinkler_on_pipeline_name.node.add_dependency(sprinkler_on_datastore)
        
        # Create Dataset
        sensor_data_dataset = iotanalytics.CfnDataset(self, "SensorDataDataset",
            dataset_name= env_params['name'] + env_params['iotanalytics']['dataset']['sensor_data_dataset_name'],
            actions= [
                iotanalytics.CfnDataset.ActionProperty(
                    action_name= "DA_SensorData_Query_1",
                    query_action= iotanalytics.CfnDataset.QueryActionProperty(
                        sql_query= "SELECT * FROM {}".format(sensor_data_datastore.datastore_name) # nosec
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
        sensor_data_dataset.node.add_dependency(sensor_data_datastore)
        
        sprinkler_off_dataset = iotanalytics.CfnDataset(self, "SprinklerOffDataset",
            dataset_name= env_params['name'] + env_params['iotanalytics']['dataset']['sprinkler_off_dataset_name'],
            actions= [
                iotanalytics.CfnDataset.ActionProperty(
                    action_name= "DA_SprinklerOff_Query_1",
                    query_action= iotanalytics.CfnDataset.QueryActionProperty(
                        sql_query= "SELECT * FROM {}".format(sprinkler_off_datastore.datastore_name) # nosec
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
        
        sprinkler_on_dataset = iotanalytics.CfnDataset(self, "SprinklerOnDataset",
            dataset_name= env_params['name'] + env_params['iotanalytics']['dataset']['sprinkler_on_dataset_name'],
            actions= [
                iotanalytics.CfnDataset.ActionProperty(
                    action_name= "DA_SprinklerOn_Query_1",
                    query_action= iotanalytics.CfnDataset.QueryActionProperty(
                        sql_query= "SELECT * FROM {}".format(sprinkler_on_datastore.datastore_name) # nosec
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
        sprinkler_on_dataset.node.add_dependency(sprinkler_on_datastore)
        
        self.sensor_data_channel = sensor_data_channel
        self.sprinkler_off_channel = sprinkler_off_channel
        self.sprinkler_on_channel = sprinkler_on_channel
        