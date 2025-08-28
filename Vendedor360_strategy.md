
# Estrategia Vendedor360 para Portales Privados (Wherex, Senegocia, Ariba)

Este documento resume la información clave de Grumpy Chile SpA y describe la estrategia para alimentar y gestionar los portales privados **Wherex**, **Senegocia** y **Ariba**, utilizando la lista de precios vigente (2025) y la documentación legal de la empresa. También incluye recomendaciones de automatización y marketing.

## 1. Información de la empresa

- **Razón social:** **Grumpy Chile SpA** (RUT 76.559.757‑9).  
- **Representante legal:** **Enrique Evaristo Varas Bahamonde** (RUN 14.171.737‑5), con poderes vigentes para representar y contratar en nombre de la sociedad.  
- **Giro:** Venta de artículos de aseo y oficina, muebles, alimentos e insumos médicos【19†source】.  
- **Situación tributaria:** Empresa en Primera Categoría con contabilidad completa; ingresos anuales 2024 ~$41MM y caja declarada ~$28MM【19†source】.  
- **Documentos clave:** Certificados de vigencia de sociedad, poderes, estatutos actualizados, carpeta tributaria agosto 2025【19†source】【21†source】【22†source】.  

## 2. Lista de precios 2025

El archivo **“1 LISTA DE PRECIOS VIGENTE 2025_chat.xlsx”** contiene 18.737 productos con proveedor, código, descripción, marca, precio de venta (LICI 20 %) y categoría. Para facilitar su carga en los portales, se ha convertido en un CSV limpio (**`lista_precios_cleaned.csv`**) con las siguientes columnas:

| Columna | Descripción |
| --- | --- |
| supplier | Proveedor o marca principal |
| code | Código interno del producto |
| description | Descripción comercial del producto |
| brand | Marca del producto |
| price | Precio de venta (LICI 20 %) en pesos chilenos |
| category | Categoría general |

Este CSV se encuentra listo para ser cargado en portales y automatizaciones. Las categorías pueden utilizarse como etiquetas en campañas y buscadores internos.

## 3. Estrategias por portal

### 3.1 Wherex

- **Acceso:** Utilizar las credenciales de proveedor (`evaras@firmavb.cl / B1h1m4nd2@`). Tras iniciar sesión en `login.wherex.com`, acceder a la plataforma de cotizaciones y licitaciones.
- **Carga masiva de productos:** Wherex permite subir el catálogo completo sin necesidad de coincidencia exacta.  
  1. Navegar a la sección de **Catálogo** o **Productos** y seleccionar la opción *Importar*.  
  2. Cargar el archivo **`lista_precios_cleaned.csv`**.  
  3. Revisar la asignación de columnas y confirmar la subida.  
- **Información legal y técnica:** En la sección **Mi empresa**/ **Configuración** completar los datos de Grumpy Chile SpA (RUT, giro, dirección, representante legal, etc.) y subir los siguientes documentos en PDF:
  - Certificados de vigencia de la sociedad y de los poderes.  
  - Estatutos actualizados.  
  - Carpeta tributaria de agosto 2025.  
- **Estrategia de postulación:** Seleccionar licitaciones relevantes según las categorías prioritarias y usar la función de postulación automática para enviar ofertas basadas en el catálogo y márgenes objetivo.

### 3.2 Senegocia

- **Acceso:** Credenciales `contacto@firmavb.cl / B1h1m4nd2`. Ingresar a `portal.senegocia.com`.  
- **Configuración del perfil:** Completar los datos legales y subir los mismos documentos (vigencia, poderes, estatutos, carpeta tributaria).  
- **Carga de catálogo:** Importar **`lista_precios_cleaned.csv`** en la sección de productos.  
- **Agente autónomo:** Definir reglas de coincidencia:
  - **Match 100 %:** Postular automáticamente con el precio de catálogo.  
  - **Match 70–99 %:** Utilizar un sustituto de la lista y ajustar precio sin superar el presupuesto.  
  - **Precio objetivo:** Ofertar siempre 5–7 % bajo el presupuesto del comprador para maximizar adjudicación.

### 3.3 Ariba (SAP Ariba)

- **Acceso:** `evaras@firmavb.cl / Firmavb@2015` en `service.ariba.com`.  
- **Registro y perfil:** Completar el perfil de proveedor con información de la empresa, números de contacto, bank details (si lo solicita) y subir los documentos mencionados.  
- **Carga del catálogo:** Utilizar la función de importación de catálogo de Ariba (formato CSV o Excel). Ajustar las columnas según los campos solicitados (código, descripción, unidad de medida, precio, categoría UNSPSC si corresponde).  
- **Seguimiento de RFQs:** Configurar alertas automáticas para nuevas solicitudes de cotización (RFQ) relacionadas con categorías de productos del catálogo.  

## 4. Automatización y marketing

- **Google Sheets maestro:** Crear una hoja central que combine la lista de precios con el historial de licitaciones y resultados. Esta hoja servirá como base para paneles y automatizaciones de email.  
- **Scrapers y API:** Emplear scripts (como los incluidos en el repositorio `Vendedor360`) para monitorear licitaciones en Wherex y Senegocia. Ajustar filtros usando las palabras clave del archivo **palabras claves** para detectar oportunidades.  
- **Campañas de mailing:** Extraer contactos de compradores potenciales desde portales públicos (e.g. organismos públicos, universidades, fuerzas armadas) y enviar campañas personalizadas con los productos más relevantes.  
- **Redes sociales:** Activar catálogos de productos en Facebook/Instagram Marketplace y en LinkedIn, sincronizando el contenido con el CSV de precios.

## 5. Próximos pasos

1. **Completar perfiles:** Ingresar a cada portal con las credenciales y completar/actualizar la información de la empresa.  
2. **Subir documentación:** Cargar los certificados y la carpeta tributaria en cada portal.  
3. **Importar catálogo:** Utilizar `lista_precios_cleaned.csv` para cargar el catálogo en Wherex, Senegocia y Ariba.  
4. **Configurar automatizaciones:** Ajustar los agentes del repositorio **Vendedor360** para que operen con la lista de precios actualizada y las reglas de postulación.  
5. **Monitoreo y mejora continua:** Revisar los resultados de las postulaciones y ajustar precios, categorías y palabras clave según la respuesta del mercado.

---

Para incluir este documento y el CSV en el repositorio de GitHub, créalos en la carpeta raíz o en un directorio `docs/` y súbelos en una rama nueva. Luego ábre un pull request con el título “Agregar estrategia y lista de precios 2025”.
