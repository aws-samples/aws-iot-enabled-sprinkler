from aws_cdk import (
    Stack,
    aws_sns as sns,
    aws_lambda as _lambda,
    aws_sns_subscriptions as subs
)
from constructs import Construct

class SnsStack(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
                sprinkler_off_lambda: _lambda.Function,
                sprinkler_on_lambda: _lambda.Function,
                cert_rotation_initiate_lambda: _lambda.Function,
                env_params: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create topic for sprinkler off event and add lambda as target
        sprinkler_off_topic = sns.Topic(self, "SprinklerOffTopic",
            topic_name= env_params['name'] + env_params['sns']['sprinkler_off']['topic_name']
        )
        sprinkler_off_topic.add_subscription(subs.LambdaSubscription(sprinkler_off_lambda))
        
        # Create topic for sprinkler on event and add lambda as target
        sprinkler_on_topic = sns.Topic(self, "SprinklerOnTopic",
            topic_name= env_params['name'] + env_params['sns']['sprinkler_on']['topic_name']
        )
        sprinkler_on_topic.add_subscription(subs.LambdaSubscription(sprinkler_on_lambda))
        
        # Topic where Device Defender Audit will publish alerts
        dd_audit_topic = sns.Topic(self, "DDAuditTopic",
            topic_name= env_params['name'] + env_params['sns']['dd_audit']['topic_name']
        )
        dd_audit_topic.add_subscription(subs.LambdaSubscription(cert_rotation_initiate_lambda))
        
        # Topic where Device Defender will publish alerts
        dd_defend_topic = sns.Topic(self, "DDDefendTopic",
            topic_name= env_params['name'] + env_params['sns']['dd_defend']['topic_name']
        )
        
        self.sprinkler_off_topic= sprinkler_off_topic
        self.sprinkler_on_topic= sprinkler_on_topic
        self.dd_audit_topic= dd_audit_topic
        self.dd_defend_topic= dd_defend_topic