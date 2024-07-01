# Generated by Django 5.0.6 on 2024-06-27 06:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app2', '0009_alter_room_quantity_alter_room_room_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='medical',
            name='admit_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='medical',
            name='release_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='medical',
            name='patient',
            field=models.CharField(default='Patient', max_length=100),
        ),
    ]
