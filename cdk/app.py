#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aws_cdk as cdk

from lib.stacks.book_app_stack import BookAppStack
from lib.stacks.user_stack import UserStack

app = cdk.App()
env_name = app.node.try_get_context("env") or "dev"

user_stack = UserStack(app, f"BookAppUser-{env_name}", env_name=env_name)
book_stack = BookAppStack(
    app, f"BookApp-{env_name}",
    env_name=env_name,
    user_pool=user_stack.user_pool,
)
book_stack.add_dependency(user_stack)

app.synth()
