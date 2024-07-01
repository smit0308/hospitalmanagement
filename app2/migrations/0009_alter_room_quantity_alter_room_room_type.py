# Generated by Django 5.0.6 on 2024-06-27 06:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app2', '0008_remove_room_available_quantity_room_is_available_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='room',
            name='quantity',
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name='room',
            name='room_type',
            field=models.CharField(choices=[('AC', 'AC Room'), ('Non-AC', 'Non-AC Room'), ('General', 'General Room')], max_length=20),
        ),
    ]
