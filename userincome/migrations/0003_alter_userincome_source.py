# Generated by Django 5.1.1 on 2024-10-06 10:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('userincome', '0002_alter_userincome_options_alter_userincome_amount_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userincome',
            name='source',
            field=models.CharField(max_length=266),
        ),
    ]
