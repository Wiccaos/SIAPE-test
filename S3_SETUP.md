# Configuración de Almacenamiento en S3

Este documento explica cómo configurar el almacenamiento de archivos en AWS S3 para la aplicación SIAPE.

## Requisitos Previos

1. Tener un bucket S3 creado en AWS
2. Tener credenciales de AWS (Access Key ID y Secret Access Key) con permisos para:
   - `s3:PutObject`
   - `s3:GetObject`
   - `s3:DeleteObject`
   - `s3:ListBucket`

## Instalación de Dependencias

Las dependencias necesarias ya están en `requirements.txt`:
- `django-storages==1.14.2`
- `boto3==1.35.0`

Para instalarlas, ejecuta:
```bash
pip install -r requirements.txt
```

## Configuración de Variables de Entorno

Agrega las siguientes variables a tu archivo `.env` o a las variables de entorno de tu servidor:

```env
# Activar almacenamiento en S3 (True para producción, False para desarrollo local)
USE_S3=True

# Credenciales de AWS
AWS_ACCESS_KEY_ID=tu_access_key_id
AWS_SECRET_ACCESS_KEY=tu_secret_access_key

# Configuración del bucket S3
AWS_STORAGE_BUCKET_NAME=nombre-de-tu-bucket
AWS_S3_REGION_NAME=us-east-1  # Cambia según tu región
```

## Configuración del Bucket S3

### 1. Crear el bucket (si no existe)
- Ve a la consola de AWS S3
- Crea un nuevo bucket con un nombre único
- Selecciona la región donde está tu aplicación

### 2. Configurar permisos del bucket

**Bucket Policy** (permite acceso desde tu aplicación):
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowAppAccess",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::TU_ACCOUNT_ID:user/TU_IAM_USER"
            },
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::nombre-de-tu-bucket/*",
                "arn:aws:s3:::nombre-de-tu-bucket"
            ]
        }
    ]
}
```

**CORS Configuration** (si necesitas acceso desde el navegador):
```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
        "AllowedOrigins": ["https://tu-dominio.com"],
        "ExposeHeaders": ["ETag"]
    }
]
```

### 3. Configurar IAM User (recomendado)

1. Crea un usuario IAM específico para la aplicación
2. Asigna una política que permita acceso al bucket:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::nombre-de-tu-bucket/*",
                "arn:aws:s3:::nombre-de-tu-bucket"
            ]
        }
    ]
}
```
3. Genera Access Keys para este usuario
4. Usa estas credenciales en las variables de entorno

## Estructura de Archivos en S3

Los archivos se organizarán de la siguiente manera en el bucket:

```
tu-bucket/
└── media/
    └── evidencias/
        └── archivo1.pdf
        └── archivo2.pdf
        └── ...
```

## Migración de Archivos Existentes

Si ya tienes archivos en el servidor local, necesitarás migrarlos a S3:

1. **Opción 1: Usar AWS CLI**
```bash
aws s3 sync /ruta/local/media/ s3://tu-bucket/media/ --region us-east-1
```

2. **Opción 2: Script de migración Django**
Puedes crear un script de migración que lea los archivos del servidor y los suba a S3.

## Verificación

Después de configurar:

1. Reinicia tu aplicación Django
2. Sube un archivo de prueba desde la aplicación
3. Verifica en la consola de S3 que el archivo se haya guardado correctamente
4. Verifica que puedas descargar el archivo desde la aplicación

## Desarrollo Local

Para desarrollo local, puedes mantener `USE_S3=False` y los archivos se guardarán localmente en la carpeta `media/`.

## Notas Importantes

- Los archivos se guardan como **privados** por defecto (requieren autenticación)
- Las URLs de los archivos son firmadas y tienen expiración
- No se sobrescriben archivos existentes (`AWS_S3_FILE_OVERWRITE = False`)
- Los archivos se organizan automáticamente en la carpeta `media/` dentro del bucket

## Solución de Problemas

### Error: "Access Denied"
- Verifica que las credenciales sean correctas
- Verifica que el IAM user tenga los permisos necesarios
- Verifica que el bucket policy permita el acceso

### Error: "Bucket does not exist"
- Verifica que el nombre del bucket sea correcto
- Verifica que el bucket esté en la región correcta

### Los archivos no se suben
- Verifica que `USE_S3=True` en las variables de entorno
- Verifica los logs de Django para ver errores específicos
- Verifica que `django-storages` y `boto3` estén instalados correctamente

