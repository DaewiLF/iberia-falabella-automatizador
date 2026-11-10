# Seguridad y protección de datos

## Modelo de confianza

Este programa fue diseñado para funcionar únicamente desde el PC del operador; escucha en `127.0.0.1`. No incorpora credenciales de Falabella, no realiza llamados al Seller Center y no envía los Excel a un servidor externo.

## Controles implementados

- Tamaño total de solicitud 85 MB, archivo individual 40 MB.
- Validación OOXML ZIP: duplicados de partes, rutas internas, cifrado, límites de archivos, límites de expansión y rechazo de VBA en archivos `.xlsx`.
- Comprobación de origen y cabeceras `Sec-Fetch-Site` para mutaciones HTTP.
- CSP, `X-Frame-Options`, `Cache-Control: no-store` y `nosniff`.
- Token aleatorio temporal (1 hora) y confirmación antes de descargar el Excel.
- Protección de fórmulas al exportar CSV (se prefija apóstrofo cuando un texto podría interpretarse como fórmula).
- Historial solo con timestamp, hash parcial del Excel base y contadores; no se guardan Excel ni SKU.
- Comparación de integridad de las partes protegidas de OOXML y de las celdas autorizadas.

## Riesgos que permanecen

- Un usuario local con acceso al equipo o al navegador puede leer datos de la sesión.
- El reporte de auditoría JSON y el CSV contienen SKU, cambios, precios y otras referencias: deben tratarse como datos internos.
- La validación de URL es estructural; no verifica disponibilidad ni contenido remoto de imágenes.
- No existe proceso de certificación GS1 de GTIN ni API oficial de validación Falabella.
- No se ha auditado toda la superficie ZIP/XML contra entradas adversarias especializadas ni se han realizado pruebas de penetración.

## Recomendaciones de publicación GitHub

Crear un repositorio **privado**, activar autenticación multifactor, conceder acceso solo a personal autorizado y revisar `git status` antes de cada push. Mantener los archivos Excel de trabajo en almacenamiento empresarial, nunca en commits, issues ni PR. Revisar periódicamente las versiones de GitHub Actions y de PyInstaller si se utiliza.
