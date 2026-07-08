from aws_cdk import (
    Stack,
    aws_rds as rds,
    aws_ec2 as ec2,
    Duration
)
from constructs import Construct

class BackupRestoreStack(Stack):
    def __init(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        vpc =ec2.Vpc(self, "Vpc", max_azs=2)

        db = rds.DatabaseInstance(
            self, "Database",
            engine = rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_17_9
            ),
            vpc=vpc,
            instance_type=ec2.InstanceType("t3.micro"),

            backup_retention=Duration.days(7),
            preferred_backup_window="03:00-04:00",

            deletion_protection=True
        )

        # Example about how to restore a db
        # restore_bd = rds.DatabaseInstanceFromSnapshot(
        #     self, "RestoreDB",
        #     snapshot_identifier="rds:my-db-2024-01-15",
        #     engine=rds.DatabaseInstanceEngine.postgres(
        #         version=rds.PostgresEngineVersion.VER_18
        #     ),
        #     vpc=vpc,
        #     instance_type=ec2.InstanceType("t3.micro"),
        # )
