from aws_cdk import (
    Stack,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_elasticloadbalancingv2 as elbv2,
    aws_autoscaling as autoscaling,
    aws_rds as rds,
    aws_ec2 as ec2,
    aws_dynamodb as dynamodb,
    Duration
)
from constructs import Construct

class ActiveActiveStack(Stack):
    def __init(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        vpc = ec2.Vpc(self, "Vpc", max_azs=3)

        asg = autoscaling.AutoScalingGroup(
            self, "Asg",
            vpc=vpc,
            instance_type=ec2.InstanceType("t3.micro"),
            machine_image=ec2.MachineImage.latest_amazon_linux2(),
            min_capacity=2,
            max_capacity=10,
            desired_capacity=4,
        )

        # dynamodb global tables - sync automat intre regiuni
        table = dynamodb.TableV2(
            self, "MyGlobalTable",
            table_name="MyGlobalTable",
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            ),
            replicas=[
                dynamodb.ReplicaTableProps(region="eu-west-1"),
                dynamodb.ReplicaTableProps(region="us-east-1")
            ]
            billing=dynamodb.Billing.on_demand(),
        )

        # Route 53 Latency routing
        route53.CfnRecordSet(
            self, "LatencyRecord",
            name="app.example.com",
            type="A",
            region="eu-west-1",
            set_identifier="eu-west-1",
            alias_target=route53.CfnRecordSet.AliasTargetProperty(
                dns_name=albload_balancer_dns_name,
                hosted_zone_id=alb.load_balancer_canonical_hosted_zone_id,
                evaluate_target_health=True,
            )
        )

