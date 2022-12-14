# Generated by Django 4.1 on 2022-08-31 19:51

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DataLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now=True)),
                ('_raw', models.TextField()),
                ('voltage', models.FloatField()),
                ('current', models.FloatField()),
                ('frequency', models.FloatField()),
                ('phase_shift', models.FloatField()),
                ('apparent_power', models.IntegerField()),
                ('reactive_power', models.IntegerField()),
                ('active_power', models.IntegerField()),
                ('current_electricity_meter_reading', models.FloatField()),
            ],
        ),
    ]
