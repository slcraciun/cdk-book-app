import aws_cdk as cdk
from aws_cdk import aws_cognito as cognito
from constructs import Construct


class UserStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, env_name: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        is_prod = env_name == "prod"
        removal_policy = cdk.RemovalPolicy.RETAIN if is_prod else cdk.RemovalPolicy.DESTROY

        self.user_pool = cognito.UserPool(
            self, "BookAppUserPool",
            user_pool_name=f"book-app-user-pool-{env_name}",
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=12,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=removal_policy,
        )

        # Groups — role is read from cognito:groups claim by the Lambda authorizer
        cognito.CfnUserPoolGroup(
            self, "AdminGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="admin",
            description="Full CRUD access",
            precedence=1,
        )
        cognito.CfnUserPoolGroup(
            self, "ReaderGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="reader",
            description="Read-only access",
            precedence=2,
        )

        # App client — no secret so tokens can be exchanged directly from CLI/API
        self.user_pool_client = self.user_pool.add_client(
            "BookAppClient",
            user_pool_client_name=f"book-app-client-{env_name}",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
            ),
            access_token_validity=cdk.Duration.hours(1),
            refresh_token_validity=cdk.Duration.days(7),
            generate_secret=False,
        )

        # CloudFormation outputs — visible after cdk deploy, used by make create-user
        cdk.CfnOutput(self, "UserPoolId", value=self.user_pool.user_pool_id)
        cdk.CfnOutput(self, "UserPoolClientId", value=self.user_pool_client.user_pool_client_id)
