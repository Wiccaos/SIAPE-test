"""
Management command para desactivar automáticamente las asignaturas 
cuyo semestre ha terminado.

Semestres:
- Otoño (otono): Marzo - Julio (termina el 31 de julio)
- Primavera (primavera): Agosto - Diciembre (termina el 31 de diciembre)

Uso:
    python manage.py desactivar_asignaturas_semestre
    
Para ejecutar automáticamente, configurar una tarea programada (cron/Task Scheduler)
que ejecute este comando el 1 de agosto y el 1 de enero de cada año.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from SIAPE.models import Asignaturas


class Command(BaseCommand):
    help = 'Desactiva automáticamente las asignaturas cuyo semestre ha terminado'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué asignaturas se desactivarían sin hacer cambios',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar desactivación sin importar la fecha actual',
        )

    def handle(self, *args, **options):
        hoy = timezone.localtime().date()
        mes_actual = hoy.month
        anio_actual = hoy.year
        
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write(f"Fecha actual: {hoy}")
        self.stdout.write(f"Modo dry-run: {'Sí' if dry_run else 'No'}")
        self.stdout.write("-" * 50)
        
        asignaturas_a_desactivar = []
        
        # Determinar qué semestres deben desactivarse
        if force:
            # Forzar: desactivar todas las que tengan semestre/año anterior al actual
            # Otoño del año actual o anterior
            asignaturas_a_desactivar = Asignaturas.objects.filter(
                is_active=True
            ).exclude(
                semestre__isnull=True
            ).exclude(
                anio__isnull=True
            )
            
            # Filtrar las que ya deberían estar desactivadas
            ids_a_desactivar = []
            for asig in asignaturas_a_desactivar:
                if self._semestre_terminado(asig.semestre, asig.anio, hoy):
                    ids_a_desactivar.append(asig.id)
            
            asignaturas_a_desactivar = Asignaturas.objects.filter(id__in=ids_a_desactivar)
        else:
            # Modo normal: verificar según la fecha actual
            if mes_actual >= 8:  # Agosto o después
                # Desactivar asignaturas de Otoño del año actual
                asignaturas_otono = Asignaturas.objects.filter(
                    is_active=True,
                    semestre='otono',
                    anio=anio_actual
                )
                asignaturas_a_desactivar = list(asignaturas_otono)
                
            if mes_actual >= 1 and mes_actual <= 2:  # Enero o Febrero
                # Desactivar asignaturas de Primavera del año anterior
                asignaturas_primavera = Asignaturas.objects.filter(
                    is_active=True,
                    semestre='primavera',
                    anio=anio_actual - 1
                )
                asignaturas_a_desactivar = list(asignaturas_primavera)
        
        if not asignaturas_a_desactivar:
            self.stdout.write(
                self.style.SUCCESS("No hay asignaturas que necesiten ser desactivadas.")
            )
            return
        
        self.stdout.write(f"Asignaturas a desactivar: {len(asignaturas_a_desactivar)}")
        self.stdout.write("-" * 50)
        
        for asig in asignaturas_a_desactivar:
            semestre_display = asig.get_semestre_display() if asig.semestre else 'Sin semestre'
            self.stdout.write(
                f"  - {asig.nombre} ({asig.seccion}) | {semestre_display} {asig.anio or ''} | Carrera: {asig.carreras.nombre}"
            )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\n[DRY-RUN] Se habrían desactivado {len(asignaturas_a_desactivar)} asignaturas."
                )
            )
        else:
            # Desactivar asignaturas
            if isinstance(asignaturas_a_desactivar, list):
                count = 0
                for asig in asignaturas_a_desactivar:
                    asig.is_active = False
                    asig.save()
                    count += 1
            else:
                count = asignaturas_a_desactivar.update(is_active=False)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✓ Se desactivaron {count} asignaturas exitosamente."
                )
            )
    
    def _semestre_terminado(self, semestre, anio, fecha_actual):
        """
        Determina si un semestre ya terminó basándose en la fecha actual.
        
        - Otoño (marzo-julio): Termina el 31 de julio
        - Primavera (agosto-diciembre): Termina el 31 de diciembre
        """
        if not semestre or not anio:
            return False
        
        mes_actual = fecha_actual.month
        anio_actual = fecha_actual.year
        
        if semestre == 'otono':
            # Otoño termina en julio
            if anio < anio_actual:
                return True
            elif anio == anio_actual and mes_actual >= 8:
                return True
        elif semestre == 'primavera':
            # Primavera termina en diciembre
            if anio < anio_actual:
                return True
        
        return False

