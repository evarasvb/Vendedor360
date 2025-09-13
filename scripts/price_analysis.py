"""
Price and margin analysis tool for Convenio Marco products.

This script reads an Excel price list with a column "PRECIO VENTA LICI 20%"
representing sale prices with a 20% markup over cost. It calculates the
underlying cost, current margin, and a recommended price reduction based on
a competitor price ratio derived from marketplace observations (0.17% below
current price). The recommended price maintains a margin greater than 19% over
cost. The script outputs a CSV with new columns: COST, MARGIN_RATIO,
RECOMMENDED_PRICE, and NEW_MARGIN_RATIO.

Usage:
    python price_analysis.py input.xlsx output.csv
"""

import pandas as pd


def calculate_margins(input_xls: str, output_csv: str) -> None:
    """Compute costs, margins, and recommended prices from an Excel file.

    Parameters
    ----------
    input_xls : str
        Path to the input Excel file with a sheet 'lista de precios'.
    output_csv : str
        Path to save the generated CSV with analysis columns.
    """
    df = pd.read_excel(input_xls, sheet_name='lista de precios')
    # Drop columns that are entirely NaN
    df = df.dropna(axis=1, how='all')
    # Rename price column
    price_col = 'PRECIO VENTA LICI 20%'
    if price_col not in df.columns:
        raise ValueError(f"El archivo no contiene la columna '{price_col}'")
    df = df.rename(columns={price_col: 'PRICE'})
    # Compute cost by dividing price by 1.2 (20% markup)
    df['COST'] = df['PRICE'] / 1.2
    # Current margin relative to cost
    df['MARGIN_RATIO'] = (df['PRICE'] - df['COST']) / df['COST']
    # Apply competitor price reduction ratio of 0.17%
    reduction_ratio = 0.0017
    df['RECOMMENDED_PRICE'] = df['PRICE'] * (1 - reduction_ratio)
    df['NEW_MARGIN_RATIO'] = (df['RECOMMENDED_PRICE'] / df['COST']) - 1
    # Round numeric columns for readability
    df['COST'] = df['COST'].round(2)
    df['PRICE'] = df['PRICE'].round(2)
    df['RECOMMENDED_PRICE'] = df['RECOMMENDED_PRICE'].round(2)
    df['MARGIN_RATIO'] = df['MARGIN_RATIO'].round(4)
    df['NEW_MARGIN_RATIO'] = df['NEW_MARGIN_RATIO'].round(4)
    df.to_csv(output_csv, index=False, encoding='utf-8')


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print('Uso: python price_analysis.py input.xlsx output.csv')
    else:
        calculate_margins(sys.argv[1], sys.argv[2])