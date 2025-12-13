# Configuración de Permisos S3 para SIAPE

## Error 403: Forbidden

El error 403 puede ocurrir por varias razones:
1. Las llaves de acceso no tienen los permisos necesarios
2. El bucket tiene restricciones de acceso
3. La configuración de ACL está causando conflictos

## Configuración para Cuentas de Estudiante/Academy

Esta aplicación está configurada para usar **llaves de acceso directas** (no IAM), que es común en cuentas de estudiante de AWS Academy.

### Permisos Requeridos en las Llaves de Acceso

Las llaves de acceso deben tener permisos para:

- `s3:PutObject` - Para subir archivos
- `s3:GetObject` - Para leer archivos
- `s3:DeleteObject` - Para eliminar archivos
- `s3:ListBucket` - Para listar objetos en el bucket
- `s3:HeadObject` - Para verificar si un archivo existe

### Configuración del Bucket

El bucket `siape-docs` debe tener:
1. **Permisos del bucket**: Asegúrate de que tu cuenta tenga permisos de lectura/escritura
2. **Block Public Access**: Puede estar activado (los archivos son privados)
3. **CORS** (si es necesario): Configurado para permitir acceso desde tu dominio

### Nota sobre ACLs

La aplicación está configurada con `AWS_DEFAULT_ACL = None` y `default_acl = None` porque:
- Las cuentas de estudiante pueden no tener permisos para gestionar ACLs
- Esto evita errores 403 relacionados con permisos de ACL
- Los archivos usarán los permisos por defecto del bucket

## Verificación

1. **Verificar que el bucket existe:**
   ```bash
   aws s3 ls s3://siape-docs
   ```

2. **Verificar permisos de escritura:**
   ```bash
   aws s3 cp test.txt s3://siape-docs/media/test.txt
   ```

3. **Verificar variables de entorno en el servidor:**
   ```bash
   echo $AWS_STORAGE_BUCKET_NAME
   echo $AWS_ACCESS_KEY_ID
   echo $AWS_SECRET_ACCESS_KEY
   echo $AWS_S3_REGION_NAME
   ```

## Configuración del Bucket

El bucket debe tener:
- Nombre: `siape-docs`
- Región: La misma que `AWS_S3_REGION_NAME` (por defecto `us-east-1`)
- Block Public Access: Puede estar activado (los archivos son privados)
- Versioning: Opcional

## Solución del Error KeyError: 'staticfiles'

Asegúrate de que el servidor tenga el código actualizado con la configuración de `STORAGES` que incluye `staticfiles`.

Después de actualizar el código, reinicia el servidor:
```bash
sudo systemctl restart gunicorn
# o
sudo supervisorctl restart gunicorn
```

