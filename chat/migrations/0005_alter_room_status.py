# Generated by Django 4.0 on 2023-06-25 17:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0004_rename_message_messaage_content'),
    ]

    operations = [
        migrations.AlterField(
            model_name='room',
            name='status',
            field=models.IntegerField(default=0),
        ),
    ]