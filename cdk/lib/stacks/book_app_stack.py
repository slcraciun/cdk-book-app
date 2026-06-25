import aws_cdk as cdk
from aws_cdk import aws_apigateway as apigw
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

        table = BookAppDynamodbTable(
            self, f"BooksTable-{env_name}",
            env_name=env_name,
            table_name=f"books-{env_name}",
            partition_key=dynamodb.Attribute(
                name="isbn",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

        handlers = self._create_handlers(table)
        self._create_rest_api(handlers, user_pool)

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
