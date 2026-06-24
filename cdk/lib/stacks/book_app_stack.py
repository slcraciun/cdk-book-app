import aws_cdk as cdk
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as lambda_
from constructs import Construct

from lib.constructs.book_app_dynamodb_table import BookAppDynamodbTable


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
            partition_key=dynamodb.Attribute(
                name="isbn",
                type=dynamodb.AttributeType.STRING,
            ),
        )

        books_fn = self._create_books_handler(table)
        table.grant_read_write_data(books_fn)

        self._create_rest_api(books_fn, user_pool)

    def _create_books_handler(self, table: BookAppDynamodbTable) -> lambda_.Function:
        return lambda_.Function(
            self, "BooksApiHandler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset("api"),
            handler="books.handler.handler",
            environment={
                "TABLE_NAME": table.table_name,
                "ENV_NAME": self.env_name,
            },
            timeout=cdk.Duration.seconds(30),
            memory_size=256,
        )

    def _create_rest_api(
        self,
        books_fn: lambda_.Function,
        user_pool: cognito.UserPool,
    ) -> apigw.RestApi:
        api = apigw.RestApi(
            self, "BooksApi",
            rest_api_name=f"books-api-{self.env_name}",
            deploy_options=apigw.StageOptions(stage_name="v1"),
        )

        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self, "CognitoAuthorizer",
            cognito_user_pools=[user_pool],
        )

        integration = apigw.LambdaIntegration(books_fn)

        books = api.root.add_resource("books")
        books.add_method("POST", integration, authorizer=authorizer)
        books.add_method("GET", integration)

        book = books.add_resource("{isbn}")
        book.add_method("GET", integration)
        book.add_method("PUT", integration, authorizer=authorizer)
        book.add_method("DELETE", integration, authorizer=authorizer)

        return api
