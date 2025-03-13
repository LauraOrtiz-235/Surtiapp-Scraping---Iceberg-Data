import os
import pandas as pd
from datetime import datetime

# ============================================================================
# Functions to analyze the SurtiApp historical data and the new data extracted 
# from the web scraping process. Generate insights and save the results
# ============================================================================

def combine_recent_datasets(folder="data", output="data/surtiapp_dataset_recent.csv"):
    """
    Function to combine the recent datasets in the data folder. 
    """
    if os.path.exists(output):
        print(f"Eliminando archivo existente: {output}")
        os.remove(output)

    csv_files = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.startswith("surtiapp_dataset_") and f.endswith(".csv")
    ]

    if not csv_files:
        print("No se encontraron datasets para combinar.")
        return

    dataframes = []
    for file in csv_files:
        print(f"Cargando: {file}")
        df = pd.read_csv(file)
        dataframes.append(df)

    combined_df = pd.concat(dataframes, ignore_index=True)
    combined_df.to_csv(output, index=False)
    print(f"Total de registros: {len(combined_df)}")

# Combine datasets
combine_recent_datasets()

# Load datasets
old_df = pd.read_csv("surtiapp_dataset.csv")                # Historical data
new_df = pd.read_csv("data/surtiapp_dataset_recent.csv")    # New data

# Numeric columns
for df in [old_df, new_df]:
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['discount_price'] = pd.to_numeric(df['discount_price'], errors='coerce')
    df['available_quantity'] = pd.to_numeric(df['available_quantity'], errors='coerce')
    df['date_scrape'] = pd.to_datetime(df['date_scrape'], errors='coerce')

all_data = pd.concat([old_df, new_df], ignore_index=True)

# ============================================================================
# 1. Categorías con mayor variabilidad de precios
# ============================================================================
# Filter the data for the last month
recent_month = all_data[all_data["date_scrape"] > datetime.now() - pd.DateOffset(months=1)]
# Group by category and calculate the standard deviation of the price
price_variability = recent_month.groupby("subcategory")["price"].std().sort_values(ascending=False)
print("\n1. Categorías con mayor variabilidad de precios en el último mes:")
print(price_variability)


# ============================================================================
# 2. Relación entre stock y fluctuación de precio
# ============================================================================
# Merge datasets
merged_df = pd.merge(old_df, new_df, on="product_URL", suffixes=("_old", "_new"))
# Calculate the difference in price
merged_df["price_diff"] = merged_df["price_new"] - merged_df["price_old"]

price_stock = merged_df.dropna(subset=["price_diff", "available_quantity_new"])

print("\n2. Correlación entre cambio de precio y cantidad disponible:")
# Calculate the correlation
correlation = price_stock['available_quantity_new'].corr(price_stock['price_diff'])
print(f"Correlación: {correlation:.2f}")


# ============================================================================
# 3. Productos nuevos luego del 6 de marzo 2025
# ============================================================================
new_date = datetime(2025, 3, 6)
# Filter new products
new_products = new_df[~new_df["product_URL"].isin(old_df["product_URL"]) & (new_df["date_scrape"] > new_date)]
# Drop duplicates
new_products = new_products.drop_duplicates(subset="product_URL")

print("\n3. Productos nuevos desde el 6 de marzo:")
print(new_products[["product_name", "product_URL", "date_scrape"]])


# ============================================================================
# 4. Tendencias de precios por categoría
# ============================================================================
# Group by category and week
all_data["week"] = all_data["date_scrape"].dt.to_period("W")
# Calculate the mean price per week and category
weekly_prices = all_data.groupby(["subcategory", "week"])["price"].mean().reset_index()
print("\nTendencias de precios por categoría semanal:")
print(weekly_prices)

# Same but for daily data
all_data["day"] = all_data["date_scrape"].dt.to_period("D")
daily_prices = all_data.groupby(["subcategory", "day"])["price"].mean().reset_index()
print("\nTendencias de precios por categoría diaria:")
print(daily_prices)


# ============================================================================
# 5. Productos sin inventario (o muy bajo stock)
# ============================================================================
print("\n5. Productos con posible desabastecimiento:")
# Filter products with low stock
out_of_stock = new_df[new_df["available_quantity"] <= 7]
lastest_stock = out_of_stock.sort_values("date_scrape", ascending=False).drop_duplicates("product_name")
print(out_of_stock[["product_name", "available_quantity", "category"]])


# Save results in the out folder
os.makedirs("out", exist_ok=True)

# 1.
price_variability.to_csv("out/1_price_variability.csv")
# 2.
price_stock[["product_URL", "product_name_new", "price_diff", "available_quantity_new"]].to_csv("out/2_stock_vs_price.csv", index=False)
# 3. 
new_products[["product_name", "product_URL", "date_scrape", "subcategory"]].to_csv("out/3_new_products.csv", index=False)
# 4.
weekly_prices.to_csv("out/4a_weekly_trends.csv", index=False)
daily_prices.to_csv("out/4b_daily_trends.csv", index=False)
# 5.
lastest_stock[["product_name", "available_quantity", "subcategory"]].to_csv("out/5_low_stock_products.csv", index=False)