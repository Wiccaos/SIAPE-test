# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SIAPE', '0021_add_is_active_semestre_to_asignaturas'),
    ]

    operations = [
        migrations.CreateModel(
            name='DecisionDocenteAjuste',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('decision', models.CharField(choices=[('aprobado', 'Aprobado'), ('rechazado', 'Rechazado')], max_length=20, verbose_name='Decisión')),
                ('comentario', models.TextField(blank=True, default='', verbose_name='Comentario')),
                ('fecha_decision', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Decisión')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ajuste_asignado', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='decisiones_docente', to='SIAPE.ajusteasignado', verbose_name='Ajuste Asignado')),
                ('docente', models.ForeignKey(limit_choices_to={'rol__nombre_rol': 'Docente'}, on_delete=django.db.models.deletion.CASCADE, related_name='decisiones_ajustes', to='SIAPE.perfilusuario', verbose_name='Docente')),
            ],
            options={
                'verbose_name': 'Decisión de Docente sobre Ajuste',
                'verbose_name_plural': 'Decisiones de Docentes sobre Ajustes',
                'db_table': 'decision_docente_ajuste',
            },
        ),
        migrations.AddConstraint(
            model_name='decisiondocenteajuste',
            constraint=models.UniqueConstraint(fields=('ajuste_asignado', 'docente'), name='unique_decision_docente_ajuste'),
        ),
    ]

