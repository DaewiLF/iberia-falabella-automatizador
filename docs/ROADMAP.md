# Roadmap de producto y registro de decisiones pendientes

Estado al 2026-11-10: aplicación web local v2.2. Las acciones marcadas implementadas se comprobaron con pruebas automatizadas; no implican certificación Seller Center.

| Área del plan | Estado | Evidencia / siguiente paso |
|---|---|---|
| Detectar esquema, campos, SKU duplicados y ambigüedades | Implementado | `processor.py`, pruebas con XLSX reales y sintéticos |
| Modificar plantilla OOXML y verificar integridad | Implementado | `ooxml.py`, `verify_output`, prueba de estilos/partes externas |
| Vista previa y confirmación antes de descargar | Implementado | Interfaz web y endpoint `/api/approve` |
| Precio final explícito por SKU/pack | Implementado | Fuente adicional y override manual, sin derivación arbitraria |
| Fotos de packs con componentes inferidos o declarados | Implementado | `infer_components`, `choose_images` |
| Múltiples SKU padre y responsable | Implementado | Filtros y filas preformateadas |
| Mapeo de columnas/encabezados por JSON | Implementado | `parse_config` y detección con ambigüedades bloqueadas |
| Reporte de errores CSV | Implementado | `report_csv`, escape contra fórmulas |
| Auditoría detallada con hashes | Implementado en v2.2 | `GET /api/report-json/<token>.json` |
| Historial local mínimo y preferencias | Implementado | `data/history.jsonl` (no versionado), `localStorage` |
| Pruebas sin datos comerciales y GitHub Actions | Implementado en código | `tests/`, `.github/workflows/tests.yml`; ejecución remota pendiente de push |
| Ejecutable Windows | Script incluido | Requiere compilación y smoke test **en Windows** |
| Recalcular precios con Excel COM | Script incluido | Requiere equipo Windows con Excel instalado |
| Carga piloto a Falabella Seller Center | Pendiente externa | Requiere cuenta/categoría/productos reales, revisión de restricciones |
| Reglas obligatorias por categoría Falabella | Pendiente externa | Requiere esquema y reglas vigentes de las categorías utilizadas |
| Validación de titularidad de GTIN GS1 | Pendiente externa | Requiere datos/servicio autorizado; checksum no basta |
| Integración automática con Seller Center | Fuera de alcance actual | Requiere API/autorización, caso de negocio y límites de plataforma |
| Otros marketplaces | Pendiente | Aportar plantillas reales y reglas, nueva capa de adaptadores |
| Publicación GitHub remoto | Pendiente de creación del repositorio | Conector actual no tiene `create_repository`; guía en `GITHUB_PUBLICACION.md` |

## Siguiente hito propuesto

Crear repositorio **privado** y comprobar GitHub Actions (Windows/Linux). Probar en un PC Windows una exportación con tus 5 fuentes, revisar auditoría JSON y ejecutar una carga piloto pequeña en Seller Center. Registrar diferencias entre validación interna y mensajes reales de Seller Center como incidencias reproducibles **sin compartir archivos comerciales**.
