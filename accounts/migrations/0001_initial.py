from django.db import migrations


def create_statuses(apps, schema_editor):
    Status = apps.get_model("accounts", "Status")
    Status.objects.bulk_create(
        [
            Status(name="Pending"),
            Status(name="Accepted"),
            Status(name="Rejected"),
        ]
    )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(create_statuses),
    ]
