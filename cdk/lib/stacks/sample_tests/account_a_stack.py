import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ec2 as ec2,
)
from constructs import Construct

# ─────────────────────────────────────────
# ACCOUNT A — deține bucket-ul și rolul
# ─────────────────────────────────────────
class AccountAStack(Stack):
    def __init(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # 1. create bucket
        data_bucket = s3.Bucket(
            self, "DataBucket",
            bucket_name="my_data_bucket"
        )

        # 2. Add trust policy role - how can assume it
        cross_account_role = iam.Role(
            self, "CrossAccountS3Role",
            role_name="CrossAccountS3Role",
            assumed_by=iam.AccountPrincipal("222222222222")
            # assumed_by=iam.ArnPrincipal(
            #     "arn:awsLiam:22222:role/EC2AppRole"
            # )
        )
        cross_account_role.add_statement(
            iam.PolicyStatement(
                effect=iam.Effect.DENY,
                principals=[iam.AccountPrincipal("222222222222")],
                actions=["sts:AssumeRole"],
                conditions={
                    "StringNotEquals": {
                        "sts:ExternalId": "secret-unic-per-client-xyz789"
                    }
                }

            )
        )

        # 3. Add Permission Policy attached to this role
        data_bucket.grant_read(cross_account_role)

# ─────────────────────────────────────────
# ACCOUNT B — EC2 care asumă rolul
# ─────────────────────────────────────────
class AccountBStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

    def createEC2Instance(self):
        vpc = ec2.Vpc(
            self, "AppVpc",
            max_azs=2
        )

        # EC2 role from account B
        ec2_role = iam.Role(
            self, "EC2AppRole",
            role_name="EC2AppRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )

        ec2_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["sts:AssumeRole"],
            resources=["arn:aws:iam:111111111111:role/CrossAccountS3Role"]
        ))

        sg = ec2.SecurityGroup(
            self, "AppServerSG",
            vpc=vpc,
            description="Security groups for EC2",
            allow_all_outbound=True
        )
        sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(22),
            description="SSH access"
        )

        instance = ec2.Instance(
            self, "AppServer",
            instance_type=ec2.InstanceType("t3.micro"),
            machine_image=ec2.MachineImage.latest_amazon_linux2(),
            vpc=vpc,
            # vpc_subnet=ec2.SubnetSelection(
            #     subnet_type=ec2.SubnetType.PUBLIC,
            # ),
            security_group=sg,
            role=ec2_role
        )





app = cdk.App()

AccountAStack(app, "AccountAStack", env=cdk.Environment(
    account="111111111111",
    region="eu-west-1",
))

AccountBStack(app, "AccountBstack", env=cdk.Environment(
    account="222222222222",
    region="eu-west-1",
))

app.synth()