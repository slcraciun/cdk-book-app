import aws_cdk as cdk
from aws_cdk import aws_dynamodb as dynamodb
from constructs import Construct


class BookAppDynamodbTable(dynamodb.Table):
    """DynamoDB table with opinionated environment-aware defaults.

    Dev:  PAY_PER_REQUEST billing, DESTROY removal policy, no point-in-time recovery.
    Prod: PROVISIONED billing with auto-scaling, RETAIN removal policy, point-in-time recovery.

    All defaults can be overridden by the caller via kwargs.
    """

    # Read capacity is set higher than the 10 simultaneous request requirement to account
    # for read-heavy catalog usage patterns and leave headroom for traffic spikes.
    # Write capacity is lower since book creation/updates are infrequent admin operations.
    READ_MIN_CAPACITY = 5
    READ_MAX_CAPACITY = 20
    WRITE_MIN_CAPACITY = 3
    WRITE_MAX_CAPACITY = 12
    TARGET_UTILIZATION_PERCENT = 70

    def __init__(self, scope: Construct, construct_id: str, env_name: str, **kwargs):
        is_prod = env_name == "prod"

        kwargs.setdefault(
            "billing_mode",
            dynamodb.BillingMode.PROVISIONED if is_prod else dynamodb.BillingMode.PAY_PER_REQUEST,
        )
        kwargs.setdefault(
            "removal_policy",
            cdk.RemovalPolicy.RETAIN if is_prod else cdk.RemovalPolicy.DESTROY,
        )
        kwargs.setdefault(
            "point_in_time_recovery_specification",
            dynamodb.PointInTimeRecoverySpecification(point_in_time_recovery_enabled=is_prod),
        )

        super().__init__(scope, construct_id, **kwargs)

        if kwargs["billing_mode"] == dynamodb.BillingMode.PROVISIONED:
            read_scaling = self.auto_scale_read_capacity(
                min_capacity=self.READ_MIN_CAPACITY,
                max_capacity=self.READ_MAX_CAPACITY,
            )
            read_scaling.scale_on_utilization(
                target_utilization_percent=self.TARGET_UTILIZATION_PERCENT,
            )

            write_scaling = self.auto_scale_write_capacity(
                min_capacity=self.WRITE_MIN_CAPACITY,
                max_capacity=self.WRITE_MAX_CAPACITY,
            )
            write_scaling.scale_on_utilization(
                target_utilization_percent=self.TARGET_UTILIZATION_PERCENT,
            )
