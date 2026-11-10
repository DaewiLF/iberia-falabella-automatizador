# Repositorio GitHub — publicación y mantenimiento

**Repositorio:** `https://github.com/DaewiLF/iberia-falabella-automatizador` (propietario DaewiLF). Este documento conserva instrucciones manuales como alternativa a la publicación mediante el conector.

**Aviso de privacidad:** al preparar la publicación el repositorio estaba configurado como **Public**. Para limitar el acceso al código empresarial, el propietario debe cambiarlo a **Private** en GitHub → Settings → General → Danger Zone → Change repository visibility. Ningún archivo de Excel comercial, SKU real, precio empresarial ni reporte de auditoría forma parte del código versionado.

## Crear un repositorio nuevo (solo si este deja de existir)

1. Abre <https://github.com/new> e inicia sesión con la cuenta donde quieres mantener el código.
2. Nombre sugerido: `iberia-falabella-automatizador`.
3. Visibilidad: **Private**.
4. No inicialices el repositorio con README, licencia o `.gitignore` (el paquete ya los prepara cuando corresponda).
5. Crea el repositorio y copia su URL HTTPS.

## Subir código

Desde la carpeta extraída de la distribución de código:

```bash
git init -b main
git add .
git status
git commit -m "feat: automatizador Falabella 2.2 con seguridad y CI"
git remote add origin https://github.com/DaewiLF/iberia-falabella-automatizador.git
git push -u origin main
```

Si clonaste el `git bundle` que acompaña a la entrega, los commits ya están creados y solo necesitas añadir el remoto y hacer `git push -u origin main`.

### Alternativa: conservar el commit entregado con el bundle Git

Si prefieres mantener el historial original, coloca el archivo `.bundle` en una carpeta y ejecuta:

```bash
git clone -b main Iberia_Falabella_v2.2_repositorio_Git.bundle iberia-falabella-automatizador
cd iberia-falabella-automatizador
git remote remove origin
git remote add origin https://github.com/DaewiLF/iberia-falabella-automatizador.git
git push -u origin main
```

El parámetro `-b main` es importante porque el bundle lleva la rama `main` pero no una referencia `HEAD` independiente.

## Después de publicar

- Comprueba que **Actions → Validación Python / OOXML** haya terminado sin fallos en Windows y Linux.
- Verifica que no hay datos empresariales en la lista de archivos del repositorio.
- Configura revisión por PR antes de integrar cambios a `main` si trabajará más gente.
- Si la integración ChatGPT GitHub no ve el repositorio nuevo, revisa en la instalación de GitHub App que la cuenta le haya concedido acceso a ese repositorio.

## Alternativa temporal

El ZIP incluye todos los archivos `README`, `docs`, `tests`, `.github` y código. También se entrega un **bundle Git** con un commit local, que permite clonar el historial sin que exista todavía el remoto.
