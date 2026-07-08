from aws_cdk import (
    Stack,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_elasticloadbalancingv2 as elbv2,
    aws_autoscaling as autoscaling,
    aws_rds as rds,
    aws_ec2 as ec2,
    Duration
)
from constructs import Construct

class PrimaryStack(Stack):
    def __init(self, scope: Construct, id: str, is_primary: bool, **kwargs):

        vpc=ec2.Vpc(self,  "Vpc", max_azs=2)

        primary_alb = elbv2.ApplicationLoadBalancer(
            self, "PrimaryALB",
            vpc=vpc,
            internet_facing=True,
        )

        asg = autoscaling.AutoScalingGroup(
            self, "ASG",
            vpc=vpc,
            instance_type=ec2.InstanceType("t3.micro"),
            machine_image=ec2.MachineImage.latest_amazon_linux2(),

            min_capacity=2 if is_primary else 1,
            max_capacity=10 if is_primary else 4,
            desired_capacity=2 if is_primary else 1
        )

        # Audora Global database - cross-region auto replicate
        cluster = rds.DatabaseCluster(
            self, "AuroraCluster",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_17_9
            ),
            vpc=vpc,
            writer=rds.ClusterInstance.provisioned(
                "writer",
                instance_type=ec2.InstanceType("t3.medium")
            )
        )

        # Route 53 Failover 
        # Health check
        health_check = route53.CfnHealthCheck(
            self, "PrimaryHealthCheck",
            health_check_config=route53.CfnHealthCheck.HealthCheckConfigProperty(
                type="HTTPS",
                fully_qualified_domain_name=alb.load_balancer_dns_name,
                port=443,
                request_interval=10,
                failure_threshold=2,
            )
        )

        hosted_zone = route53.HostedZone.from_lookup(
            self, "HostedZone",
            domain_name="example.com",
        )

        # Record PRIMARY
        route53.ARecord(
            self, "PrimaryRecord",
            zone=hosted_zone,
            record_name="app.example.com",
            target=route53.RecordTarget.from_alias(
                targets.LoadBalancerTarget(alb)
            )
        )

        # record failover
        route53.CfnRecordSet(
            self, "PrimaryRecord",
            name="app.example.com",
            hosted_zone_id=hosted_zone.hosted_zone_id,
            type="A",
            failover="PRIMARY",
            set_identifier="primary",
            health_check_id=health_check.attr_health_check_id,
            alias_target=route53.CfnRecordSet.AliasTargetProperty(
                dns_name=primary_alb.load_balancer_dns_name,
                hosted_zone_id=primary_alb.load_balancer_canonical_hosted_zone_id,
                evaluate_target_health=True
            )
        )

        route53.CfnRecordSet(
            self, "FailoverRecord",
            name="app.example.com",
            hosted_zone_id=hosted_zone.hosted_zone_id,
            type="A",
            failover="SECONDARY",
            set_identifier="secondary",
            alias_target=route53.CfnRecordSet.AliasTargetProperty(
                dns_name="standby-alb-123456.us-east-1.elb.amazonaws.com",
                hosted_zone_id="Z35SXDOTRQ7X7K",
                evaluate_target_health=True
            )
        )

class WarmStandbyStack(Stack):
    def __ini__(self, scope: Construct, id: str, **kwargs)
        super().__init__(scope, id, **kwargs)
    
        vpc = ec2.Vpc(self, "Vpc", max_azs=2)

        self.standby_alb = elbv2.ApplicationLoadBalancer(
            self, "StandbyALB",
            vpc=vpc,
            internet_facing=True
        )

        cdk.CfnOutput(
            self, "StandbyALBDns",
            value=self.standby_alb.load_balancer_dns_name,
            descripttion="Use this DNS in the primary stack"
        )
