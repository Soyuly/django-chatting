# Generated by Django 4.0 on 2023-06-25 16:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_rename_meesage_messaage_meessage'),
    ]

    operations = [
        migrations.RenameField(
            model_name='messaage',
            old_name='meessage',
            new_name='message',
        ),
    ]
