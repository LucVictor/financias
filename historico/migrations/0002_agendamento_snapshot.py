from django.db import migrations


def criar_agendamento(apps, schema_editor):
    CrontabSchedule = apps.get_model('django_celery_beat', 'CrontabSchedule')
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    cron, _ = CrontabSchedule.objects.get_or_create(
        minute='0',
        hour='0,8,16',
        day_of_month='*',
        month_of_year='*',
        day_of_week='*',
        timezone='America/Sao_Paulo',
    )
    PeriodicTask.objects.get_or_create(
        name='Snapshot histórico a cada 8h',
        defaults={
            'task': 'historico.tasks.snapshot_historico_8h',
            'crontab': cron,
            'enabled': True,
        },
    )


def remover_agendamento(apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    PeriodicTask.objects.filter(task='historico.tasks.snapshot_historico_8h').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('historico', '0001_initial'),
        ('django_celery_beat', '0018_improve_crontab_helptext'),
    ]

    operations = [
        migrations.RunPython(criar_agendamento, remover_agendamento),
    ]