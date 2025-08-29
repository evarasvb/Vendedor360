import os
import pandas as pd


def asegurar_directorio(path: str):
	os.makedirs(os.path.dirname(path), exist_ok=True)


def generar_productos_catalogo_csv(path: str = "/workspace/productos_catalogo.csv"):
	asegurar_directorio(path)
	df = pd.DataFrame({
		"ID_Convenio_Marco": ["CM-0001", "CM-0002", "CM-0003"],
		"Nombre_Producto": [
			"Lápiz Pasta Azul BIC",
			"Cuaderno Universitario 100 Hojas",
			"Block de Notas 75x75mm",
		],
	})
	df.to_csv(path, index=False)
	print(f"Escrito {path}")


def generar_lista_compra_csv(path: str = "/workspace/lista_compra_ejemplo.csv"):
	asegurar_directorio(path)
	df = pd.DataFrame({
		"Entrada": ["CM-0001", "Cuaderno Universitario", "CM-0003"],
		"Cantidad": [2, 1, 5],
	})
	df.to_csv(path, index=False)
	print(f"Escrito {path}")


def generar_lista_compra_txt(path: str = "/workspace/lista_compra_ejemplo.txt"):
	asegurar_directorio(path)
	contenido = "\n".join([
		"CM-0001,2",
		"Cuaderno Universitario,1",
		"CM-0003,5",
	])
	with open(path, "w", encoding="utf-8") as f:
		f.write(contenido)
	print(f"Escrito {path}")


def generar_lista_compra_xlsx(path: str = "/workspace/lista_compra_ejemplo.xlsx"):
	asegurar_directorio(path)
	df = pd.DataFrame({
		"Entrada": ["CM-0001", "Cuaderno Universitario", "CM-0003"],
		"Cantidad": [2, 1, 5],
	})
	df.to_excel(path, index=False)
	print(f"Escrito {path}")


if __name__ == "__main__":
	generar_productos_catalogo_csv()
	generar_lista_compra_csv()
	generar_lista_compra_txt()
	generar_lista_compra_xlsx()

