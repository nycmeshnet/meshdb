import os

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("meshapi", "0001_initial"),
    ]

    @staticmethod
    def create_meshdb_ro(apps, schema_editor):
        with schema_editor.connection.cursor() as cursor:
            db_user_ro = os.environ.get("DB_USER_RO")
            if not db_user_ro:
                raise ValueError(
                    f"Could not create {db_user_ro} postgres role! Please set the DB_USER_RO environment variable."
                )
            db_password_ro = os.environ.get("DB_PASSWORD_RO")
            if not db_password_ro:
                raise ValueError(
                    f"Could not create {db_user_ro} postgres role! Please set the DB_PASSWORD_RO environment variable."
                )

            # Role for meshdb_ro
            # Super extra solution to create if doesn't exist on SO.
            # https://stackoverflow.com/a/8099557/6095682
            cursor.execute(
                f"""
            DO
            $do$
            BEGIN
               IF EXISTS (
                  SELECT FROM pg_catalog.pg_roles
                  WHERE  rolname = '{db_user_ro}') THEN

                  RAISE NOTICE 'Role "{db_user_ro}" already exists. Skipping.';
               ELSE
                  BEGIN   -- nested block
                     CREATE USER {db_user_ro} WITH PASSWORD '{db_password_ro}';
                  EXCEPTION
                     WHEN duplicate_object THEN
                        RAISE NOTICE 'Role "{db_user_ro}" was just created by a concurrent transaction. Skipping.';
                  END;
               END IF;
            END
            $do$;
            """
            )

            # Grant SELECT on meshdb tables and other relevant tables
            cursor.execute(
                f"""
            DO
            $$
            BEGIN
            EXECUTE (
               SELECT 'GRANT SELECT ON TABLE '
                   || string_agg (format('%I.%I', table_schema, table_name), ',')
                   || ' TO {db_user_ro}'
               FROM   information_schema.tables
               WHERE  table_schema = 'public'
               AND (table_name LIKE 'meshapi%' OR table_name LIKE 'explorer%')
               );
            END
            $$;
            """
            )

            # Ensure he gets SELECT permission on future tables
            cursor.execute(
                f"""
            ALTER DEFAULT PRIVILEGES IN SCHEMA public
            GRANT SELECT ON TABLES TO {db_user_ro};
            """
            )

    @staticmethod
    def drop_meshdb_ro(apps, schema_editor):
        db_user_ro = os.environ.get("DB_USER_RO")
        if not db_user_ro:
            raise ValueError(
                f"Could not create {db_user_ro} postgres role! Please set the DB_USER_RO environment variable."
            )
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(f"DROP OWNED BY {db_user_ro};")
            cursor.execute(f"DROP USER IF EXISTS {db_user_ro};")

    operations = [
        migrations.RunPython(create_meshdb_ro, reverse_code=drop_meshdb_ro),
    ]
