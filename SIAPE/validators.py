"""
Validador de RUT chileno
"""
import re


def validar_rut_chileno(rut):
    """
    Valida un RUT chileno.
    
    Args:
        rut (str): RUT en formato "12345678-9" o "123456789"
    
    Returns:
        tuple: (bool, str) - (es_valido, mensaje_error)
        Si es válido, retorna (True, None)
        Si es inválido, retorna (False, mensaje_de_error)
    """
    if not rut:
        return False, "RUT inválido"
    
    # Limpiar el RUT: eliminar espacios y puntos, convertir a mayúsculas
    rut_limpio = rut.strip().replace('.', '').replace('-', '').upper()
    
    # Verificar que tenga al menos 7 caracteres (mínimo para un RUT válido)
    if len(rut_limpio) < 7:
        return False, "RUT inválido"
    
    # Verificar que tenga máximo 9 caracteres (máximo para un RUT válido)
    if len(rut_limpio) > 9:
        return False, "RUT inválido"
    
    # Separar número y dígito verificador
    if len(rut_limpio) < 2:
        return False, "RUT inválido"
    
    numero_rut = rut_limpio[:-1]
    digito_verificador = rut_limpio[-1]
    
    # Verificar que el número sea solo dígitos
    if not numero_rut.isdigit():
        return False, "RUT inválido"
    
    # Verificar que el dígito verificador sea un dígito o 'K'
    if not (digito_verificador.isdigit() or digito_verificador == 'K'):
        return False, "RUT inválido"
    
    # Calcular el dígito verificador correcto
    suma = 0
    multiplicador = 2
    
    # Recorrer el número de derecha a izquierda
    for digito in reversed(numero_rut):
        suma += int(digito) * multiplicador
        multiplicador += 1
        if multiplicador > 7:
            multiplicador = 2
    
    # Calcular el resto
    resto = suma % 11
    digito_calculado = 11 - resto
    
    # Ajustar según el algoritmo chileno
    if digito_calculado == 11:
        digito_calculado = '0'
    elif digito_calculado == 10:
        digito_calculado = 'K'
    else:
        digito_calculado = str(digito_calculado)
    
    # Comparar con el dígito verificador ingresado
    if digito_calculado != digito_verificador:
        return False, "RUT inválido"
    
    return True, None


def formatear_rut(rut):
    """
    Formatea un RUT agregando puntos y guion.
    
    Args:
        rut (str): RUT sin formato o con formato
    
    Returns:
        str: RUT formateado como "12.345.678-9"
    """
    if not rut:
        return ""
    
    # Limpiar el RUT
    rut_limpio = rut.strip().replace('.', '').replace('-', '').upper()
    
    if len(rut_limpio) < 2:
        return rut
    
    # Separar número y dígito verificador
    numero_rut = rut_limpio[:-1]
    digito_verificador = rut_limpio[-1]
    
    # Agregar puntos cada 3 dígitos desde la derecha
    numero_formateado = ""
    for i, digito in enumerate(reversed(numero_rut)):
        if i > 0 and i % 3 == 0:
            numero_formateado = '.' + numero_formateado
        numero_formateado = digito + numero_formateado
    
    # Retornar con guion y dígito verificador
    return f"{numero_formateado}-{digito_verificador}"


def validar_contraseña(password):
    """
    Valida una contraseña según los requisitos del sistema.
    
    Requisitos:
    - Mínimo 8 caracteres
    - Al menos una letra (a-z, A-Z)
    - Al menos un número (0-9)
    
    Args:
        password (str): Contraseña a validar
    
    Returns:
        tuple: (bool, str) - (es_valida, mensaje_error)
        Si es válida, retorna (True, None)
        Si es inválida, retorna (False, mensaje_de_error)
    """
    if not password:
        return False, "La contraseña no puede estar vacía"
    
    # Verificar longitud mínima
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    
    # Verificar que tenga al menos una letra
    tiene_letra = re.search(r'[a-zA-Z]', password)
    if not tiene_letra:
        return False, "La contraseña debe contener al menos una letra"
    
    # Verificar que tenga al menos un número
    tiene_numero = re.search(r'[0-9]', password)
    if not tiene_numero:
        return False, "La contraseña debe contener al menos un número"
    
    return True, None

