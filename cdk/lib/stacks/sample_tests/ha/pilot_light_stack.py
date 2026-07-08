from aws_cdk import (
    Stack,
    Construct,
    aws_rds as rds,
    aws_ec2 as ec2,
    aws_autoscaling as autoscaling,
    Duration,
)

class PilotLightStack(Stack):
    def __init(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        vpc = ec2.Vpc(self, "Vpc", max_azs=2)

        primary_db = rds.DatabaseInstance(
            self, "PrimaryDB",
            engine = rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_18
            ),
            vpc=vpc,
            instance_type=ec2.InstanceType("t3.micro"),

            backup_retention=Duration.days(7),
        )
        asg = autoscaling.AutoScalingGroup(
            self, "PilotLightASG",
            vpc=vpc,
            instance_type=ec2.InstanceType("t3.micro"),
            machine_image=ec2.MachineImage.latest_amazon_linux2(),

            min_capacity=0,
            max_capacity=4,
            desired_capacity=0,
        )

# La disaster:
# 1. Promovezi Read Replica din Region B la Primary
# 2. Setezi desired_capacity=2 pe ASG
# 3. Actualizezi DNS (Route 53) spre Region B
# → RTO: ~15-30 minute
