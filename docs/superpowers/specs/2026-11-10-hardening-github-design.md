# Diseño: endurecimiento y publicación controlada de Iberia Falabella

Fecha: 2026-11-10

## Objetivo

Mantener la aplicación local y sin servicios externos para transformar Excel de trabajo en un libro Falabella sin reconstruirlo ni alterar los contenidos protegidos. Añadir protección ante archivos hostiles, informes auditables y pruebas ejecutables sin datos comerciales, además de documentación lista para un repositorio privado.

## Alcance y decisiones

- Conservar arquitectura HTML/JS + HTTP Python estándar + motor OOXML, sin base de datos ni API de Seller Center.
- Validar archivos XLSX antes de leerlos: entradas ZIP únicas, rutas canónicas, sin cifrado, tamaños y ratio de expansión acotados.
- Resolver encabezados alternativos únicamente si existe una coincidencia inequívoca.
- Evitar que campos de usuario se ejecuten como fórmulas al abrir reportes CSV en Excel.
- Añadir reporte de auditoría JSON descargable (sin guardar contenido de archivos en el historial persistente).
- Incorporar pruebas sintéticas sin plantillas privadas; mantener pruebas reales opcionales fuera de GitHub.
- Añadir CI GitHub Actions para Windows/Linux, prácticas de contribución y seguridad.

## Enfoques considerados

1. Migración a un frontend/backend moderno: más dependencias, no necesaria para el trabajo local de 48 horas.
2. Complemento de Excel: modifica el modelo operativo y no elimina riesgos de SKU/pricing.
3. **Evolución de la aplicación local (elegida por continuidad del plan aprobado):** mejora confiabilidad sin migrar archivos ni exponer datos a servicios externos.

## Restricciones

- No subir ni versionar los Excel de la empresa, precios, fotos ni históricos locales.
- No generar GTIN aleatorios para una carga comercial.
- Ninguna afirmación de aceptación Seller Center sin prueba real.
- Repo privado recomendado; la conexión GitHub actual no dispone de una acción de creación de repositorios.

## Fuera de alcance

- Publicación automática, credenciales Seller Center, consulta de reglas privadas por categoría.
- Compilación Windows certificada desde Linux, prueba final con Seller Center.
