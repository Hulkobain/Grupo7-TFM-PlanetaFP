# Acuerdo de trabajo del equipo

## Flujo de Git

- Nadie hará *push* directamente a `main`.
- Todo el trabajo se subirá a `develop` desde su rama de tarea.
- Las *pull requests* se crearán y revisarán desde la interfaz de GitHub; no se integrará ningún cambio sin una PR revisada.
- Cada tarea se desarrollará en una rama específica y tendrá su *issue* o referencia asignada.
- Se seguirá **GitFlow**: `develop` será la rama de integración y las ramas `feature/<tarea>` se integrarán mediante PR en `develop`.
- `main` contendrá exclusivamente versiones preparadas para entrega. Cada entrega se marcará con un *tag* de *release*.
