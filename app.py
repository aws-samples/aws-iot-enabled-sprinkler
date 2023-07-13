#!/usr/bin/env python3
import os

import aws_cdk as cdk

from iot_enabled_sprinkler.iot_enabled_sprinkler_stack import IotEnabledSprinklerStack

app = cdk.App()
params = app.node.try_get_context("params")

dev_params = params['environments']['dev']
IotEnabledSprinklerStack(app, "IotEnabledSprinklerStack",
    env=cdk.Environment(
        account=dev_params["account_id"],
        region=dev_params["region"]), 
        env_params=dev_params
)

# prod_params = params['environments']['prod']
# IotEnabledSprinklerStack(app, "IotEnabledSprinklerStack-Prod",
#     env=cdk.Environment(
#         account=prod_params["account_id"],
#         region=prod_params["region"]), 
#         env_params=prod_params
# )


app.synth()