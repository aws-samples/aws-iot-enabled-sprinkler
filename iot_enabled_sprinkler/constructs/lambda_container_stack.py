from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_s3 as s3,
    CfnOutput
)
from constructs import Construct

class LambdaContainerStack(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
                env_params: dict, 
                devices_bucket: s3.Bucket,
                rotation_lambda_container_policy: iam.Policy,
                cert_creation_lambda_container_policy: iam.Policy,
                verification_cert_creation_lambda_container_policy: iam.Policy,
                **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Lambda container to generate verification certificate
        verification_lambda_container = _lambda.DockerImageFunction(
            self, "CreateVerificationCert",
            code=_lambda.DockerImageCode.from_image_asset(directory="./lambda_containers/generate_verification_cert"),
            timeout= Duration.seconds(10)
        )
        verification_lambda_container.role.attach_inline_policy(verification_cert_creation_lambda_container_policy)
        
        # Lambda container to generate fresh device certificates
        device_cert_creation_container = _lambda.DockerImageFunction(
            self, "DeviceCertCreation",
            code=_lambda.DockerImageCode.from_image_asset(directory="./lambda_containers/device_cert_creation"),
            timeout= Duration.seconds(15),
            environment= {
                "S3_BUCKET_NAME":  devices_bucket.bucket_name,
                "ROOT_CERT_FILE_KEY": "custom_cert_files/customRootCA.pem",
                "ROOT_KEY_FILE_KEY": "custom_cert_files/customRootCA.key"
            }
        )
        device_cert_creation_container.role.attach_inline_policy(cert_creation_lambda_container_policy)
        

        # Lambda container to device certificate rotation
        device_cert_rotation_container = _lambda.DockerImageFunction(
            self, "DeviceCertRotation",
            code=_lambda.DockerImageCode.from_image_asset(directory="./lambda_containers/device_cert_rotation"),
            timeout= Duration.seconds(15),
            environment= {
                "S3_BUCKET_NAME":  devices_bucket.bucket_name,
                "ROOT_CERT_FILE_KEY": "custom_cert_files/customRootCA.pem",
                "ROOT_KEY_FILE_KEY": "custom_cert_files/customRootCA.key"
            }
        )
        device_cert_rotation_container.role.attach_inline_policy(rotation_lambda_container_policy)
        device_cert_rotation_container.grant_invoke(iam.ServicePrincipal('iot.amazonaws.com'))
        
        
        self.verification_lambda_container = verification_lambda_container
        self.device_cert_rotation_container = device_cert_rotation_container
        self.device_cert_creation_container = device_cert_creation_container
        
        # Outputs
        CfnOutput(self, "DeviceCertCreationLambdaContainer", 
            value=device_cert_creation_container.function_name,
            description= "Device Certificate Creation Lambda Container Name",
            export_name="DeviceCertCreationLambdaContainer"
        )