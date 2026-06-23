import aws_cdk as core
import aws_cdk.assertions as assertions

from lib.stacks.book_app_stack import BookAppStack


def test_stack_synthesizes():
    app = core.App()
    stack = BookAppStack(app, "book-app-test")
    assertions.Template.from_stack(stack)
