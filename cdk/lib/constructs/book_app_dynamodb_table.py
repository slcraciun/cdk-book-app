import aws_cdk as cdk
from aws_cdk import aws_dynamodb as dynamodb
from constructs import Construct


class BookAppDynamodbTable(dynamodb.TableV2):
    """DynamoDB Global Table (V2) with opinionated environment-aware defaults.

    Dev:  on-demand billing, DESTROY removal policy, no point-in-time recovery.
    Prod: auto-scaled provisioned billing, RETAIN removal policy, point-in-time recovery.
    Both: AWS managed encryption at rest.

    All defaults can be overridden by the caller via kwargs, including `replicas`
    for cross-region replication (PITR on a replica is set per-entry via
    `ReplicaTableProps`, since CloudFormation manages it independently per region).
    """

    READ_MIN_CAPACITY = 5
    READ_MAX_CAPACITY = 20
    WRITE_MIN_CAPACITY = 3
    WRITE_MAX_CAPACITY = 12
    TARGET_UTILIZATION_PERCENT = 70

    def __init__(self, scope: Construct, construct_id: str, env_name: str, **kwargs):
        is_prod = env_name == "prod"

        kwargs.setdefault(
            "billing",
            dynamodb.Billing.provisioned(
                read_capacity=dynamodb.Capacity.autoscaled(
                    min_capacity=self.READ_MIN_CAPACITY,
                    max_capacity=self.READ_MAX_CAPACITY,
                    target_utilization_percent=self.TARGET_UTILIZATION_PERCENT,
                ),
                write_capacity=dynamodb.Capacity.autoscaled(
                    min_capacity=self.WRITE_MIN_CAPACITY,
                    max_capacity=self.WRITE_MAX_CAPACITY,
                    target_utilization_percent=self.TARGET_UTILIZATION_PERCENT,
                ),
            ) if is_prod else dynamodb.Billing.on_demand(),
        )
        kwargs.setdefault(
            "removal_policy",
            cdk.RemovalPolicy.RETAIN if is_prod else cdk.RemovalPolicy.DESTROY,
        )
        # Blocks manual/console DeleteTable calls, independent of the CloudFormation
        # removal policy above (which only governs stack-driven deletes).
        kwargs.setdefault("deletion_protection", is_prod)
        kwargs.setdefault(
            "point_in_time_recovery_specification",
            dynamodb.PointInTimeRecoverySpecification(point_in_time_recovery_enabled=is_prod),
        )
        kwargs.setdefault("encryption", dynamodb.TableEncryptionV2.aws_managed_key())

        super().__init__(scope, construct_id, **kwargs)
