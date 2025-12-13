"""
Configuración personalizada de almacenamiento para S3
"""
from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorage(S3Boto3Storage):
    """
    Almacenamiento personalizado para archivos media (evidencias, documentos, etc.)
    Los archivos se guardarán en el bucket S3 en la carpeta 'media/'
    """
    location = 'media'
    file_overwrite = False
    default_acl = 'private'  # Archivos privados por defecto


class StaticStorage(S3Boto3Storage):
    """
    Almacenamiento personalizado para archivos estáticos (opcional)
    Los archivos estáticos se guardarán en el bucket S3 en la carpeta 'static/'
    """
    location = 'static'
    default_acl = 'public-read'  # Archivos estáticos públicos

