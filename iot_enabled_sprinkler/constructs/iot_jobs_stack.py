from aws_cdk import (
    Stack,
    aws_iot as iot,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    CfnOutput
)
import aws_cdk as cdk
import json
from constructs import Construct

class IotJobsStack(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
        devices_bucket: s3.Bucket,
        devices_bucket_deploy: s3deploy.BucketDeployment,
        env_params: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create Job Template for CA Rotation
        cacert_rotation_job_template = iot.CfnJobTemplate(self, "CaCertRotationTemplate",
            description= "IoT Jobs tempalte that will rotate a device's RootCA upon given a URL",
            job_template_id= env_params['name'] + env_params['iot_jobs']['cacert_jobs_template_id'],
            document_source= "https://" + devices_bucket.bucket_name + ".s3.ap-southeast-2.amazonaws.com/" + env_params['iot_jobs']['cacert_job_document_path']
        )
        # Add dependency
        cacert_rotation_job_template.node.add_dependency(devices_bucket)
        cacert_rotation_job_template.node.add_dependency(devices_bucket_deploy)
        
        # Create Job Template for IoT Certificate Rotation
        iot_cert_rotation_job_template = iot.CfnJobTemplate(self, "IoTCertRotationTemplate",
            description= "IoT Jobs tempalte that will initiate iot certificate roation",
            job_template_id= env_params['name'] + env_params['iot_jobs']['iot_cert_jobs_template_id'],
            document_source= "https://" + devices_bucket.bucket_name + ".s3.ap-southeast-2.amazonaws.com/" + env_params['iot_jobs']['iot_cert_job_document_path']
        )
        # Add dependency
        iot_cert_rotation_job_template.node.add_dependency(devices_bucket)
        iot_cert_rotation_job_template.node.add_dependency(devices_bucket_deploy)
        
        # Create Job Template for Custom Certificate Rotation
        custom_cert_rotation_job_template = iot.CfnJobTemplate(self, "CustomCertRotationTemplate",
            description= "IoT Jobs tempalte that will initiate custom certificate roation",
            job_template_id= env_params['name'] + env_params['iot_jobs']['custom_cert_jobs_template_id'],
            document_source= "https://" + devices_bucket.bucket_name + ".s3.ap-southeast-2.amazonaws.com/" + env_params['iot_jobs']['custom_cert_job_document_path']
        )
        # Add dependency
        custom_cert_rotation_job_template.node.add_dependency(devices_bucket)
        custom_cert_rotation_job_template.node.add_dependency(devices_bucket_deploy)
        
        self.cacert_rotation_job_template= cacert_rotation_job_template
        self.iot_cert_rotation_job_template= iot_cert_rotation_job_template
        self.custom_cert_rotation_job_template= custom_cert_rotation_job_template