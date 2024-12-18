# Generated by Django 5.1.1 on 2024-10-06 09:59

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('userincome', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='userincome',
            options={'ordering': ['-date']},
        ),
        migrations.AlterField(
            model_name='userincome',
            name='amount',
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
        migrations.AlterField(
            model_name='userincome',
            name='source',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='userincome.source'),
        ),
    ]
