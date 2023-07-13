from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_iam as iam,
    aws_s3_deployment as s3deploy,
    CfnOutput
)
import aws_cdk as cdk
from constructs import Construct
import json

class S3Stack(Construct):
    def __init__(self, scope: Construct, construct_id: str, env_params: dict, 
                    **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create Bucket
        devices_bucket = s3.Bucket(self, "DevicesBucket",
            # bucket_name= env_params['name'] + env_params['s3']['bucket_name'],
            versioned=True,
            block_public_access= s3.BlockPublicAccess.BLOCK_ALL,
            intelligent_tiering_configurations=[s3.IntelligentTieringConfiguration(
                name="DevicesBucketTiering",
                archive_access_tier_time=cdk.Duration.days(90),
                deep_archive_access_tier_time=cdk.Duration.days(180)
            )],
            server_access_logs_prefix= "access_logs/"
        )
        
        # Add Template names to the device parameters file
        with open('device_files/devices/sample_device/parameters.json', 'r+') as f:
            data = json.load(f)
            data['provisioningTemplateName'] =  env_params['name'] + env_params['template']['provisioning_template_name']
            data['rotationTemplateName'] =  env_params['name'] + env_params['template']['rotation_template_name']
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()
        
        
        # Alter JITP Tempalte Body with values of ThingTypeName, and GroupName
        with open('jitp_template/template_body.json', 'r+') as f:
            template_body = json.load(f)
            template_body['Resources']['thing']['Properties']['ThingTypeName'] =  env_params['name'] + env_params['thing_type']['thing_type_name']
            template_body['Resources']['thing']['Properties']['ThingGroups'][0] = env_params['name'] + env_params['static_thing_group']['group_name']
            f.seek(0)
            json.dump(template_body, f, indent=4)
            f.truncate()
        
        # Alter the JITP Template to include the altered template body, and JITP Role
        with open('device_files/jitp_template/template.json', 'r+') as f:
            template = json.load(f)
            template['templateBody'] = json.dumps(template_body)
            template['roleArn'] = "arn:aws:iam::{}:role/{}".format(env_params['account_id'], env_params['name'] + env_params['jitp']['role_name'])
            f.seek(0)
            json.dump(template, f, indent=4)
            f.truncate()
        
        # Upload device files to bucket
        devices_bucket_deploy = s3deploy.BucketDeployment(self, "DeployDeviceFiles",
            sources= [
                s3deploy.Source.asset('device_files')
            ],
            destination_bucket=devices_bucket
        )
        
        # Self declarations
        self.devices_bucket= devices_bucket
        self.devices_bucket_deploy= devices_bucket_deploy
        
        # Outputs
        CfnOutput(self, "S3BucketName", 
            value=devices_bucket.bucket_name,
            description= "S3 Bucket Name where device files are stored",
            export_name="DeviceFilesBucket"
        )