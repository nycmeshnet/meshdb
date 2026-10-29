from invoke import task


@task
def format(context):
    context.run("uv run black .")
    context.run("uv run isort .")


@task
def lint(context):
    context.run("uv run black . --check")
    context.run("uv run isort . --check")
    context.run("uv run flake8 src")
    context.run("uv run mypy")


@task
def test(context):
    context.run("uv run python src/manage.py test meshapi meshapi_hooks")
