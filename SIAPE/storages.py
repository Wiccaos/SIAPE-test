"""
Configuración personalizada de almacenamiento para S3
"""
from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings


class MediaStorage(S3Boto3Storage):
    """
    Almacenamiento personalizado para archivos media (evidencias, documentos, etc.)
    Los archivos se guardarán en el bucket S3 'siape-docs' en la carpeta 'media/'
    
    Configurado para funcionar con llaves de acceso directas (cuentas de estudiante/Academy)
    """
    # El bucket name se toma de AWS_STORAGE_BUCKET_NAME en settings.py
    # Asegúrate de que en tu .env o variables de entorno tengas:
    # AWS_STORAGE_BUCKET_NAME=siape-docs
    location = 'media'
    file_overwrite = False
    # Archivos públicos para acceso permanente sin tokens que expiren
    default_acl = 'public-read'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Asegurar que el bucket name esté configurado
        if not self.bucket_name:
            from django.conf import settings
            self.bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'siape-docs')
    
    def exists(self, name):
        """
        Sobrescribir exists() para evitar errores 403 en HeadObject.
        Para cuentas de estudiante, simplemente asumimos que el archivo no existe
        si no podemos verificarlo, permitiendo que se suba.
        """
        try:
            return super().exists(name)
        except Exception as e:
            # Si hay un error de permisos (403), asumimos que no existe
            # Esto permite que el archivo se suba sin verificar primero
            if '403' in str(e) or 'Forbidden' in str(e):
                return False
            # Para otros errores, relanzar la excepción
            raise


class StaticStorage(S3Boto3Storage):
    """
    Almacenamiento personalizado para archivos estáticos (opcional)
    Los archivos estáticos se guardarán en el bucket S3 en la carpeta 'static/'
    """
    location = 'static'
    default_acl = 'public-read'  # Archivos estáticos públicos

