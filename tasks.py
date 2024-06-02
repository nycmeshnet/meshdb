from invoke import task


@task
def format(context):
    context.run("black .")
    context.run("isort .")


@task
def lint(context):
    context.run("black . --check")
    context.run("isort . --check")
    context.run("flake8 src")
    context.run("mypy")


@task
def test(context):
    context.run("python src/manage.py test meshapi meshapi_hooks")
