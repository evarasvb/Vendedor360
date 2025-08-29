## Catálogo Convenio Marco - Scraper y Cotizador

### Instalación

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Archivos de ejemplo

Generar archivos de ejemplo (catálogo y listas de compra):

```bash
python /workspace/scripts/generar_ejemplos.py
```

Esto crea:
- `/workspace/productos_catalogo.csv`
- `/workspace/lista_compra_ejemplo.csv`
- `/workspace/lista_compra_ejemplo.txt`
- `/workspace/lista_compra_ejemplo.xlsx`

### Enriquecimiento de datos (Scraper)

Lee `productos_catalogo.csv` (debe tener columna `ID_Convenio_Marco`) y produce `productos_catalogo_con_imagenes.csv` agregando `URL_Imagen` obtenida desde Prisa.

```bash
# Requiere: requests, beautifulsoup4 (instalar si no están disponibles)
python -m catalogo.scraper --in /workspace/productos_catalogo.csv --out /workspace/productos_catalogo_con_imagenes.csv --espera 1.0
```

Notas:
- Usa `requests` + `BeautifulSoup`.
- Maneja errores y estructura cambiante devolviendo `URL_Imagen` vacía cuando falle.

### Cotizador automático

Procesa archivos de lista de compra (`.csv`, `.txt`, `.xlsx`) para generar una cotización con columnas requeridas. Base de datos simulada en `catalogo/data.py`.

```bash
python -m catalogo.cotizador /workspace/lista_compra_ejemplo.csv --salida /workspace/cotizacion_salida.csv
```

La salida `cotizacion_salida.csv` contiene columnas: `ID_Convenio_Marco`, `Nombre_Producto`, `Precio_Unitario`, `Cantidad`, `URL_Imagen`, `Subtotal`.

Si hay productos no encontrados, se listan por consola y están en `df.attrs['no_encontrados']` si se usa como módulo.

