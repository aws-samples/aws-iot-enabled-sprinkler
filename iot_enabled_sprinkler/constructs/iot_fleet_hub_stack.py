from aws_cdk import (
    Stack,
    aws_iot as iot,
    aws_iam as iam,
    aws_iotfleethub as iotfleethub,
    aws_cloudformation as cloudformation,
    CfnOutput, CfnDeletionPolicy, CfnTag
)
from constructs import Construct
import json

class IotFleetHubStack(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
                    env_params: dict,
                    fleet_hub_app_role: iam.Role,
                    custom_resource: cloudformation.CfnCustomResource,
                    **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
    
        
        # Create Fleet Hub Application
        fleet_hub_app = iotfleethub.CfnApplication(self, "FleetHubApp",
            application_name= env_params['name'] + env_params['fleet_hub']['application'],
            role_arn= fleet_hub_app_role.role_arn,
            application_description="FleetHub App created as part of IoT Enabled Sprinklers project stack",
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
        fleet_hub_app.node.add_dependency(custom_resource)