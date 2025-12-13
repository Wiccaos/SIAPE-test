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
    # No establecer default_acl para cuentas de estudiante que pueden no tener permisos de ACL
    default_acl = None
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Asegurar que el bucket name esté configurado
        if not self.bucket_name:
            from django.conf import settings
            self.bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'siape-docs')


class StaticStorage(S3Boto3Storage):
    """
    Almacenamiento personalizado para archivos estáticos (opcional)
    Los archivos estáticos se guardarán en el bucket S3 en la carpeta 'static/'
    """
    location = 'static'
    default_acl = 'public-read'  # Archivos estáticos públicos

