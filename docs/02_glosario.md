# Glosario rápido — Microsoft Purview

Términos que debes reconocer al instante. Si te preguntan algo y no recuerdas, aquí lo buscas.

---

| Término | Definición corta |
|---|---|
| **Asset** | Cualquier objeto registrado en Purview: tabla, archivo, dashboard, pipeline |
| **Capacity Unit (vCU)** | Unidad de cómputo del Data Map. Mínimo 1, escala elástica |
| **Classification** | Etiqueta de tipo de dato (Credit Card, Email, DNI). System o custom |
| **Collection** | Carpeta jerárquica que agrupa sources y assets. Hereda RBAC |
| **Data Catalog** | UI para descubrir y explorar assets |
| **Data Estate Insights (DEI)** | Dashboards de salud y cumplimiento del catálogo |
| **Data Map** | Grafo de metadatos. Núcleo de Purview, basado en Apache Atlas |
| **Data Policy** | Permisos de acceso a datos gestionados desde Purview |
| **Data Sharing** | Compartir datasets entre tenants/cuentas sin moverlos |
| **Data Source Admin** | Rol que registra sources y configura scans |
| **Data Curator** | Rol que edita metadatos, classifications, glossary |
| **Data Reader** | Rol de solo lectura |
| **Domain** *(preview)* | Agrupación de nivel superior a collection (data mesh) |
| **Glossary** | Diccionario de términos de negocio asociados a assets técnicos |
| **Lineage** | Trazabilidad del flujo de datos entre assets |
| **Managed Identity (MSI)** | Identidad gestionada por Azure, sin secretos. Recomendada para scans |
| **MIP (Microsoft Information Protection)** | Plataforma de sensitivity labels que Purview consume |
| **Resource Set** | Agrupación lógica de archivos en lake (ej: particiones de una tabla) |
| **Scan** | Proceso de extracción de metadatos desde una source |
| **Scan rule set** | Configuración: qué extensiones escanear y qué classifications correr |
| **Self-hosted Integration Runtime (SHIR)** | Agent para escanear sources on-premise o en VNets privadas |
| **Sensitivity Label** | Etiqueta de criticidad (Public, Confidential, Highly Confidential) |
| **Source** | Sistema de datos registrado en Purview |
| **Steward** | Responsable de calidad y documentación de un asset |
| **Unity Catalog** | Catálogo nativo de Databricks. Sincroniza con Purview |

---

## Atajos visuales en la UI

- **Mapa con flechas** → Lineage
- **Casita azul (collections)** → Data Map → Collections
- **Lupa** → Data Catalog (búsqueda)
- **Barras de progreso** → Data Estate Insights
- **Engranaje** → Management
