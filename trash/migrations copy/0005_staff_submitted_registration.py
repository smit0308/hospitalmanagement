# Generated by Django 5.0.6 on 2024-06-18 07:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app2', '0004_staff_awards_staff_birth_date_staff_city_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='staff',
            name='submitted_registration',
            field=models.BooleanField(default=False),
        ),
    ]
