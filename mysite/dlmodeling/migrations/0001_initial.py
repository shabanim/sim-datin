# Generated by Django 3.0.3 on 2020-06-11 05:02

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Summary',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('workload_graph', models.FileField(upload_to='')),
                ('archbench_config', models.FileField(upload_to='')),
                ('param_scaleup_config', models.FileField(upload_to='')),
                ('param_scaleout_config', models.FileField(upload_to='')),
                ('enable_scaleout', models.BooleanField(default=False)),
                ('param_report', models.FileField(upload_to='')),
                ('overlap_report', models.FileField(upload_to='')),
            ],
        ),
    ]
