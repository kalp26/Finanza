# Generated by Django 5.1.1 on 2024-10-06 10:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0006_alter_expense_category'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='expense',
            options={},
        ),
        migrations.AlterField(
            model_name='expense',
            name='amount',
            field=models.FloatField(),
        ),
    ]