#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aws_cdk as cdk

from lib.stacks.book_app_stack import BookAppStack

app = cdk.App()
BookAppStack(app, "BookAppStack")
app.synth()
