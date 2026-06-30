import aws_cdk as cdk
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as lambda_
from constructs import Construct

from lib.constructs.book_app_dynamodb_table import BookAppDynamodbTable

_BUNDLING = cdk.BundlingOptions(
    image=lambda_.Runtime.PYTHON_3_12.bundling_image,
    platform="linux/amd64",
    command=[
        "bash", "-c",
        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output",
    ],
)

_REPLICA_REGION = "eu-west-2"


class BookAppStack(cdk.Stack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_name: str,
        user_pool: cognito.UserPool,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = env_name
        is_prod = env_name == "prod"

        table = BookAppDynamodbTable(
            self, f"BooksTable-{env_name}",
            env_name=env_name,
            table_name=f"books-{env_name}",
            partition_key=dynamodb.Attribute(
                name="isbn",
                type=dynamodb.AttributeType.STRING,
            ),
            billing=dynamodb.Billing.on_demand(),
            # Cross-region Global Table replica so reads/writes survive a regional
            # outage. Requires the stack to be deployed to a concrete env (see app.py).
            replicas=[
                dynamodb.ReplicaTableProps(region=_REPLICA_REGION, point_in_time_recovery=True),
            ] if is_prod else None,
        )

        handlers = self._create_handlers(table)
        api = self._create_rest_api(handlers, user_pool)

        if is_prod:
            self._create_replication_alarm(table)
            self._create_table_throttle_alarm(table)
            self._create_lambda_alarms(handlers)
            self._create_api_alarm(api)

    def _create_replication_alarm(self, table: BookAppDynamodbTable) -> None:
        replication_latency = cloudwatch.Metric(
            namespace="AWS/DynamoDB",
            metric_name="ReplicationLatency",
            dimensions_map={"TableName": table.table_name, "ReceivingRegion": _REPLICA_REGION},
            statistic="Maximum",
            period=cdk.Duration.minutes(1),
        )
        cloudwatch.Alarm(
            self, "ReplicationLatencyAlarm",
            metric=replication_latency,
            threshold=60_000,
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            alarm_description=(
                f"DynamoDB replication from {self.region} to {_REPLICA_REGION} "
                "has been lagging more than 60s for 3 consecutive minutes"
            ),
        )

    def _create_table_throttle_alarm(self, table: BookAppDynamodbTable) -> None:
        cloudwatch.Alarm(
            self, "TableThrottlingAlarm",
            # Matches the operations the repository actually issues (see
            # api/books/adapters/dynamodb_repository.py) — list/create_batch
            # both go through get_item/put_item/scan, not Query or BatchWriteItem.
            metric=table.metric_throttled_requests_for_operations(
                operations=[
                    dynamodb.Operation.GET_ITEM,
                    dynamodb.Operation.PUT_ITEM,
                    dynamodb.Operation.UPDATE_ITEM,
                    dynamodb.Operation.DELETE_ITEM,
                    dynamodb.Operation.SCAN,
                ],
                period=cdk.Duration.minutes(5),
            ),
            threshold=1,
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description="DynamoDB requests are being throttled",
        )

    def _create_lambda_alarms(self, handlers: dict) -> None:
        for key, fn in handlers.items():
            label = key.replace("_", " ").title().replace(" ", "")
            cloudwatch.Alarm(
                self, f"{label}ErrorsAlarm",
                metric=fn.metric_errors(period=cdk.Duration.minutes(5)),
                threshold=1,
                evaluation_periods=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
                alarm_description=f"{label} Lambda is erroring",
            )
            cloudwatch.Alarm(
                self, f"{label}ThrottlesAlarm",
                metric=fn.metric_throttles(period=cdk.Duration.minutes(5)),
                threshold=1,
                evaluation_periods=2,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
                alarm_description=f"{label} Lambda is being throttled",
            )

    def _create_api_alarm(self, api: apigw.RestApi) -> None:
        cloudwatch.Alarm(
            self, "ApiServerErrorAlarm",
            metric=api.metric_server_error(period=cdk.Duration.minutes(5)),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description="API Gateway is returning 5XX errors",
        )

    def _make_fn(self, name: str, handler: str, table: BookAppDynamodbTable) -> lambda_.Function:
        return lambda_.Function(
            self, f"{name}Handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset("api", bundling=_BUNDLING),
            handler=handler,
            environment={
                "TABLE_NAME": table.table_name,
                "ENV_NAME": self.env_name,
            },
            timeout=cdk.Duration.seconds(30),
            memory_size=256,
        )

    def _create_handlers(self, table: BookAppDynamodbTable) -> dict:
        create_fn       = self._make_fn("Create",      "books.handlers.create.handler",       table)
        create_batch_fn = self._make_fn("CreateBatch", "books.handlers.create_batch.handler", table)
        list_fn         = self._make_fn("List",        "books.handlers.list.handler",         table)
        get_fn          = self._make_fn("Get",         "books.handlers.get.handler",          table)
        update_fn       = self._make_fn("Update",      "books.handlers.update.handler",       table)
        delete_fn       = self._make_fn("Delete",      "books.handlers.delete.handler",       table)

        # Minimal IAM per function
        table.grant_read_data(list_fn)
        table.grant_read_data(get_fn)
        table.grant_read_write_data(create_fn)
        table.grant_read_write_data(create_batch_fn)
        table.grant_read_write_data(update_fn)
        table.grant_read_write_data(delete_fn)

        return {
            "create":       create_fn,
            "create_batch": create_batch_fn,
            "list":         list_fn,
            "get":          get_fn,
            "update":       update_fn,
            "delete":       delete_fn,
        }

    def _create_rest_api(self, handlers: dict, user_pool: cognito.UserPool) -> apigw.RestApi:
        api = apigw.RestApi(
            self, "BooksApi",
            rest_api_name=f"books-api-{self.env_name}",
            deploy_options=apigw.StageOptions(stage_name="v1"),
        )

        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self, "CognitoAuthorizer",
            cognito_user_pools=[user_pool],
        )

        books = api.root.add_resource("books")
        books.add_method("POST", apigw.LambdaIntegration(handlers["create"]), authorizer=authorizer)
        books.add_method("GET",  apigw.LambdaIntegration(handlers["list"]))

        batch = books.add_resource("batch")
        batch.add_method("POST", apigw.LambdaIntegration(handlers["create_batch"]), authorizer=authorizer)

        book = books.add_resource("{isbn}")
        book.add_method("GET",    apigw.LambdaIntegration(handlers["get"]))
        book.add_method("PUT",    apigw.LambdaIntegration(handlers["update"]), authorizer=authorizer)
        book.add_method("DELETE", apigw.LambdaIntegration(handlers["delete"]), authorizer=authorizer)

        return api
