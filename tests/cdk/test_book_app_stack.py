import aws_cdk as core
import aws_cdk.assertions as assertions
import pytest

from lib.constructs.book_app_dynamodb_table import BookAppDynamodbTable
from lib.stacks.book_app_stack import BookAppStack
from lib.stacks.user_stack import UserStack

HANDLERS = [
    "books.handlers.create.handler",
    "books.handlers.list.handler",
    "books.handlers.get.handler",
    "books.handlers.update.handler",
    "books.handlers.delete.handler",
]


def _make_template(env_name: str) -> assertions.Template:
    app = core.App()
    user_stack = UserStack(app, f"BookAppUser-{env_name}", env_name=env_name)
    stack = BookAppStack(
        app, f"BookApp-{env_name}",
        env_name=env_name,
        user_pool=user_stack.user_pool,
    )
    return assertions.Template.from_stack(stack)


@pytest.fixture(scope="module")
def dev_template():
    return _make_template("dev")


@pytest.fixture(scope="module")
def prod_template():
    return _make_template("prod")


# --- DynamoDB dev ---

def test_dynamodb_table_created_with_isbn_pk(dev_template):
    dev_template.has_resource_properties("AWS::DynamoDB::Table", {
        "KeySchema": [{"AttributeName": "isbn", "KeyType": "HASH"}],
        "BillingMode": "PAY_PER_REQUEST",
    })


def test_dynamodb_dev_removal_policy_is_destroy(dev_template):
    dev_template.has_resource("AWS::DynamoDB::Table", {
        "DeletionPolicy": "Delete",
        "UpdateReplacePolicy": "Delete",
    })


def test_dynamodb_dev_no_point_in_time_recovery(dev_template):
    dev_template.has_resource_properties("AWS::DynamoDB::Table", {
        "PointInTimeRecoverySpecification": {
            "PointInTimeRecoveryEnabled": False,
        }
    })


# --- DynamoDB prod ---

def test_dynamodb_prod_billing_is_provisioned(prod_template):
    # PROVISIONED mode omits BillingMode key — ProvisionedThroughput is the indicator.
    prod_template.has_resource_properties("AWS::DynamoDB::Table", {
        "ProvisionedThroughput": assertions.Match.any_value(),
    })


def test_dynamodb_prod_removal_policy_is_retain(prod_template):
    prod_template.has_resource("AWS::DynamoDB::Table", {
        "DeletionPolicy": "Retain",
        "UpdateReplacePolicy": "Retain",
    })


def test_dynamodb_prod_point_in_time_recovery_enabled(prod_template):
    prod_template.has_resource_properties("AWS::DynamoDB::Table", {
        "PointInTimeRecoverySpecification": {
            "PointInTimeRecoveryEnabled": True,
        }
    })


def test_dynamodb_prod_read_autoscaling(prod_template):
    prod_template.has_resource_properties("AWS::ApplicationAutoScaling::ScalableTarget", {
        "MinCapacity": BookAppDynamodbTable.READ_MIN_CAPACITY,
        "MaxCapacity": BookAppDynamodbTable.READ_MAX_CAPACITY,
        "ScalableDimension": "dynamodb:table:ReadCapacityUnits",
    })


def test_dynamodb_prod_write_autoscaling(prod_template):
    prod_template.has_resource_properties("AWS::ApplicationAutoScaling::ScalableTarget", {
        "MinCapacity": BookAppDynamodbTable.WRITE_MIN_CAPACITY,
        "MaxCapacity": BookAppDynamodbTable.WRITE_MAX_CAPACITY,
        "ScalableDimension": "dynamodb:table:WriteCapacityUnits",
    })


def test_dynamodb_prod_autoscaling_target_utilization(prod_template):
    prod_template.has_resource_properties("AWS::ApplicationAutoScaling::ScalingPolicy", {
        "TargetTrackingScalingPolicyConfiguration": {
            "TargetValue": BookAppDynamodbTable.TARGET_UTILIZATION_PERCENT,
        }
    })


# --- Lambda ---

def test_five_lambda_functions_created(dev_template):
    dev_template.resource_count_is("AWS::Lambda::Function", 5)


@pytest.mark.parametrize("handler", HANDLERS)
def test_each_handler_exists(dev_template, handler):
    dev_template.has_resource_properties("AWS::Lambda::Function", {
        "Handler": handler,
        "Runtime": "python3.12",
        "MemorySize": 256,
    })


def test_lambda_has_env_vars(dev_template):
    dev_template.has_resource_properties("AWS::Lambda::Function", {
        "Environment": {
            "Variables": {
                "ENV_NAME": "dev",
            }
        }
    })


# --- API Gateway ---

def test_api_gateway_created(dev_template):
    dev_template.has_resource_properties("AWS::ApiGateway::RestApi", {
        "Name": "books-api-dev",
    })


def test_cognito_authorizer_created(dev_template):
    dev_template.resource_count_is("AWS::ApiGateway::Authorizer", 1)


def test_five_api_gateway_methods_created(dev_template):
    dev_template.resource_count_is("AWS::ApiGateway::Method", 5)
