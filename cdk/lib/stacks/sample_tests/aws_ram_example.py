from aws_cdk import (
    Stack,
    Tags
)
from constructs import Construct
import aws_cdk.aws_ram as ram

class RamSharingStack(Stack):
    def __init__(self, scope: Cosntruct, construct_id: id, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        subnet_arn = f"arn:aws:ec2:{self.region}:{self.account}:subnet/subnet-0123456789abcdef0"

        resource_share=ram.CfnResourceShare(
            self, "MyResourceShare",
            name="Shared-Subnet-To-Target-Accounts",
            resource_arns=[subnet_arn],
            principals=[
                "11111111",
                "22222222"
            ],

            allow_external_principals=False
        )

        Tags.of(resource_share).add("Environment", "Production")
