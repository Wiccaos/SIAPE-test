"""
Configuración personalizada de almacenamiento para S3
"""
from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings


class MediaStorage(S3Boto3Storage):
    """
    Almacenamiento personalizado para archivos media (evidencias, documentos, etc.)
    Los archivos se guardarán en el bucket S3 'siape-docs' en la carpeta 'media/'
    """
    # El bucket name se toma de AWS_STORAGE_BUCKET_NAME en settings.py
    # Asegúrate de que en tu .env o variables de entorno tengas:
    # AWS_STORAGE_BUCKET_NAME=siape-docs
    location = 'media'
    file_overwrite = False
    default_acl = 'private'  # Archivos privados por defecto
    
    # Opcional: Si quieres forzar el nombre del bucket aquí, descomenta:
    # bucket_name = 'siape-docs'


class StaticStorage(S3Boto3Storage):
    """
    Almacenamiento personalizado para archivos estáticos (opcional)
    Los archivos estáticos se guardarán en el bucket S3 en la carpeta 'static/'
    """
    location = 'static'
    default_acl = 'public-read'  # Archivos estáticos públicos

