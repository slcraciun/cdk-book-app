import aws_cdk as core
import aws_cdk.assertions as assertions
import pytest
from lib.stacks.book_app_stack import BookAppStack
from lib.stacks.user_stack import UserStack

HANDLERS = [
    "books.handlers.create.handler",
    "books.handlers.create_batch.handler",
    "books.handlers.list.handler",
    "books.handlers.get.handler",
    "books.handlers.update.handler",
    "books.handlers.delete.handler",
]


def _make_template(env_name: str) -> assertions.Template:
    app = core.App()
    # A concrete env is required: prod's DynamoDB table uses Global Table
    # replicas, which CDK refuses to synthesize in a region-agnostic stack.
    env = core.Environment(account="123456789012", region="eu-west-1")
    user_stack = UserStack(app, f"BookAppUser-{env_name}", env_name=env_name, env=env)
    stack = BookAppStack(
        app,
        f"BookApp-{env_name}",
        env_name=env_name,
        user_pool=user_stack.user_pool,
        env=env,
    )
    return assertions.Template.from_stack(stack)


@pytest.fixture(scope="module")
def dev_template():
    return _make_template("dev")


@pytest.fixture(scope="module")
def prod_template():
    return _make_template("prod")


# --- DynamoDB ---


def test_dynamodb_table_created_with_isbn_pk(dev_template):
    dev_template.has_resource_properties(
        "AWS::DynamoDB::GlobalTable",
        {
            "KeySchema": [{"AttributeName": "isbn", "KeyType": "HASH"}],
            "BillingMode": "PAY_PER_REQUEST",
        },
    )


def test_dynamodb_dev_removal_policy_is_destroy(dev_template):
    dev_template.has_resource(
        "AWS::DynamoDB::GlobalTable",
        {
            "DeletionPolicy": "Delete",
            "UpdateReplacePolicy": "Delete",
        },
    )


def test_dynamodb_dev_no_point_in_time_recovery(dev_template):
    dev_template.has_resource_properties(
        "AWS::DynamoDB::GlobalTable",
        {
            "Replicas": assertions.Match.array_with([
                assertions.Match.object_like({
                    "PointInTimeRecoverySpecification": {"PointInTimeRecoveryEnabled": False},
                })
            ]),
        },
    )


def test_dynamodb_dev_has_no_cross_region_replica(dev_template):
    table = dev_template.find_resources("AWS::DynamoDB::GlobalTable")
    replicas = next(iter(table.values()))["Properties"]["Replicas"]
    assert len(replicas) == 1


def test_dynamodb_prod_removal_policy_is_retain(prod_template):
    prod_template.has_resource(
        "AWS::DynamoDB::GlobalTable",
        {
            "DeletionPolicy": "Retain",
            "UpdateReplacePolicy": "Retain",
        },
    )


def test_dynamodb_prod_point_in_time_recovery_enabled(prod_template):
    prod_template.has_resource_properties(
        "AWS::DynamoDB::GlobalTable",
        {
            "Replicas": assertions.Match.array_with([
                assertions.Match.object_like({
                    "PointInTimeRecoverySpecification": {"PointInTimeRecoveryEnabled": True},
                })
            ]),
        },
    )


def test_dynamodb_prod_has_cross_region_replica(prod_template):
    prod_template.has_resource_properties(
        "AWS::DynamoDB::GlobalTable",
        {
            "Replicas": assertions.Match.array_with([
                assertions.Match.object_like({"Region": "eu-west-2"})
            ]),
        },
    )


def test_dynamodb_prod_deletion_protection_enabled(prod_template):
    prod_template.has_resource_properties(
        "AWS::DynamoDB::GlobalTable",
        {
            "Replicas": assertions.Match.array_with([
                assertions.Match.object_like({"DeletionProtectionEnabled": True})
            ]),
        },
    )


def test_dynamodb_dev_deletion_protection_disabled(dev_template):
    dev_template.has_resource_properties(
        "AWS::DynamoDB::GlobalTable",
        {
            "Replicas": assertions.Match.array_with([
                assertions.Match.object_like({"DeletionProtectionEnabled": False})
            ]),
        },
    )


def test_dynamodb_prod_has_replication_latency_alarm(prod_template):
    prod_template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {
            "MetricName": "ReplicationLatency",
            "Namespace": "AWS/DynamoDB",
            "ComparisonOperator": "GreaterThanThreshold",
            "Dimensions": assertions.Match.array_with([
                assertions.Match.object_like({"Name": "ReceivingRegion", "Value": "eu-west-2"})
            ]),
        },
    )


def test_dynamodb_dev_has_no_replication_latency_alarm(dev_template):
    dev_template.resource_count_is("AWS::CloudWatch::Alarm", 0)


# --- Observability ---


def test_prod_has_table_throttling_alarm(prod_template):
    prod_template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {"AlarmDescription": "DynamoDB requests are being throttled"},
    )


def test_prod_has_api_server_error_alarm(prod_template):
    prod_template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {"AlarmDescription": "API Gateway is returning 5XX errors"},
    )


@pytest.mark.parametrize("handler", HANDLERS)
def test_prod_has_lambda_errors_alarm(prod_template, handler):
    label = handler.split(".")[2].replace("_", " ").title().replace(" ", "")
    prod_template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {"AlarmDescription": f"{label} Lambda is erroring"},
    )


@pytest.mark.parametrize("handler", HANDLERS)
def test_prod_has_lambda_throttles_alarm(prod_template, handler):
    label = handler.split(".")[2].replace("_", " ").title().replace(" ", "")
    prod_template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {"AlarmDescription": f"{label} Lambda is being throttled"},
    )


def test_prod_total_alarm_count(prod_template):
    prod_template.resource_count_is("AWS::CloudWatch::Alarm", 15)


def test_dynamodb_encryption_enabled(dev_template):
    dev_template.has_resource_properties(
        "AWS::DynamoDB::GlobalTable",
        {
            "SSESpecification": {"SSEEnabled": True},
        },
    )


# --- Lambda ---


def test_six_lambda_functions_created(dev_template):
    dev_template.resource_count_is("AWS::Lambda::Function", 6)


@pytest.mark.parametrize("handler", HANDLERS)
def test_each_handler_exists(dev_template, handler):
    dev_template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Handler": handler,
            "Runtime": "python3.12",
            "MemorySize": 256,
        },
    )


def test_lambda_has_env_vars(dev_template):
    dev_template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Environment": {
                "Variables": {
                    "ENV_NAME": "dev",
                }
            }
        },
    )


# --- API Gateway ---


def test_api_gateway_created(dev_template):
    dev_template.has_resource_properties(
        "AWS::ApiGateway::RestApi",
        {
            "Name": "books-api-dev",
        },
    )


def test_cognito_authorizer_created(dev_template):
    dev_template.resource_count_is("AWS::ApiGateway::Authorizer", 1)


def test_six_api_gateway_methods_created(dev_template):
    dev_template.resource_count_is("AWS::ApiGateway::Method", 6)
