from invoke import task


@task
def format(context):
    context.run("black .")
    # context.run("isort .")


@task
def lint(context):
    context.run("black . --check")
    context.run("isort . --check")
    # context.run("flake8 meshdb tests unit_tests")
    # context.run("mypy meshdb")


@task
def unit_test(context):
    context.run("pytest unit_tests/")
