import os
import joblib
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from auth import init_auth, login_required, roles_required

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("INVENTORY_SECRET_KEY", "dev-only-change-this-secret")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
CORS(app, supports_credentials=True, origins=["http://127.0.0.1:5500", "http://localhost:5500"])
init_auth(app)

# Maximum combined upload size: 50 MB.
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

# Load the trained model created by backend/train_model.py.
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "models",
    "random_forest_model.pkl",
)

demand_model = None
product_codes = {}
model_status = "not loaded"

try:
    saved_model = joblib.load(MODEL_PATH)
    demand_model = saved_model["model"]
    product_codes = {
        str(product_id): int(code)
        for product_id, code in saved_model["product_codes"].items()
    }
    model_status = "loaded"
except FileNotFoundError:
    model_status = "model file not found; run python backend/train_model.py"
except (EOFError, KeyError, ValueError, TypeError) as error:
    model_status = f"model could not be loaded: {error}"

INVENTORY_REQUIRED = [
    "Product_ID",
    "Current_Stock",
    "Reorder_Level",
]

SALES_REQUIRED = [
    "Date",
    "Product_ID",
    "Units_Sold",
]


def read_uploaded_csv(file):
    """Read an uploaded CSV and return a useful error if it is invalid."""
    if file is None or not file.filename:
        raise ValueError("Please upload a CSV file.")

    try:
        return pd.read_csv(file)
    except Exception as error:
        raise ValueError(f"Unable to read CSV: {error}") from error


def clean_inventory(inventory):
    """Validate and clean the inventory CSV."""
    missing = [column for column in INVENTORY_REQUIRED if column not in inventory.columns]
    if missing:
        raise ValueError("Inventory CSV is missing: " + ", ".join(missing))

    inventory = inventory.copy()
    inventory["Product_ID"] = inventory["Product_ID"].astype("string").str.strip()

    numeric_columns = [
        "Current_Stock",
        "Reorder_Level",
        "Reorder_Quantity",
        "Lead_Time_Days",
        "Unit_Price_INR",
        "Unit_Cost_INR",
    ]

    for column in numeric_columns:
        if column in inventory.columns:
            inventory[column] = pd.to_numeric(inventory[column], errors="coerce")

    inventory = inventory.dropna(
        subset=["Product_ID", "Current_Stock", "Reorder_Level"]
    )
    inventory = inventory[inventory["Product_ID"] != ""]
    inventory = inventory.drop_duplicates(subset=["Product_ID"], keep="last")

    if "Product_Name" not in inventory.columns:
        inventory["Product_Name"] = ""
    inventory["Product_Name"] = inventory["Product_Name"].fillna("").astype(str)

    return inventory


def clean_sales(sales):
    """Validate and clean the sales CSV."""
    missing = [column for column in SALES_REQUIRED if column not in sales.columns]
    if missing:
        raise ValueError("Sales CSV is missing: " + ", ".join(missing))

    sales = sales.copy()
    sales["Date"] = pd.to_datetime(sales["Date"], errors="coerce")
    sales["Product_ID"] = sales["Product_ID"].astype("string").str.strip()
    sales["Units_Sold"] = pd.to_numeric(sales["Units_Sold"], errors="coerce")

    sales = sales.dropna(subset=["Date", "Product_ID", "Units_Sold"])
    sales = sales[
        (sales["Product_ID"] != "")
        & (sales["Units_Sold"] >= 0)
    ]

    if "Product_Name" not in sales.columns:
        sales["Product_Name"] = ""
    sales["Product_Name"] = sales["Product_Name"].fillna("").astype(str)

    return sales


def make_json_safe(dataframe):
    """Replace non-finite or missing values so Flask can serialize the result."""
    dataframe = dataframe.copy()
    dataframe = dataframe.replace({np.inf: np.nan, -np.inf: np.nan})
    return dataframe.astype(object).where(pd.notna(dataframe), None)


def forecast_product_demand(product_id, forecast_date):
    """Predict one product's demand for a given date, if it was in training."""
    if demand_model is None:
        return None

    product_code = product_codes.get(str(product_id))
    if product_code is None:
        return None

    forecast_date = pd.Timestamp(forecast_date)
    features = pd.DataFrame([{
        "Product_Code": product_code,
        "Day_Of_Week": forecast_date.dayofweek,
        "Day_Of_Month": forecast_date.day,
        "Month": forecast_date.month,
    }])

    prediction = float(demand_model.predict(features)[0])
    if not np.isfinite(prediction):
        return None

    return max(0, int(round(prediction)))


def analyze_datasets(inventory, sales=None):
    inventory = clean_inventory(inventory)

    sales_summary = pd.DataFrame(
        columns=["Product_ID", "Product_Name", "Total_Units_Sold"]
    )
    daily_sales = []
    total_units_sold = None
    sales = clean_sales(sales) if sales is not None else None

    if sales is not None:
        if not sales.empty:
            names = (
                sales.loc[
                    sales["Product_Name"].str.strip() != "",
                    ["Product_ID", "Product_Name"],
                ]
                .drop_duplicates("Product_ID", keep="last")
            )

            sales_summary = (
                sales.groupby("Product_ID", as_index=False)
                .agg(Total_Units_Sold=("Units_Sold", "sum"))
            )
            sales_summary = sales_summary.merge(names, on="Product_ID", how="left")
            sales_summary["Product_Name"] = sales_summary["Product_Name"].fillna("")
            sales_summary = sales_summary.sort_values(
                "Total_Units_Sold", ascending=False
            )

            total_units_sold = float(sales["Units_Sold"].sum())

            daily = (
                sales.groupby(sales["Date"].dt.strftime("%Y-%m-%d"))["Units_Sold"]
                .sum()
                .sort_index()
            )
            daily_sales = [
                {"Date": str(date), "Units_Sold": float(units)}
                for date, units in daily.items()
            ]

            # Fill missing inventory names from sales data.
            sales_names = sales_summary[["Product_ID", "Product_Name"]]
            inventory = inventory.merge(
                sales_names,
                on="Product_ID",
                how="left",
                suffixes=("", "_sales"),
            )
            inventory["Product_Name"] = inventory["Product_Name"].where(
                inventory["Product_Name"].str.strip() != "",
                inventory["Product_Name_sales"].fillna(""),
            )
            inventory = inventory.drop(columns=["Product_Name_sales"], errors="ignore")

            day_count = max(
                (sales["Date"].max().normalize() - sales["Date"].min().normalize()).days + 1,
                1,
            )
            demand = sales_summary[["Product_ID", "Total_Units_Sold"]].copy()
            demand["Average_Daily_Demand"] = demand["Total_Units_Sold"] / day_count
            inventory = inventory.merge(demand, on="Product_ID", how="left")
        else:
            inventory["Total_Units_Sold"] = 0
            inventory["Average_Daily_Demand"] = np.nan
    else:
        inventory["Total_Units_Sold"] = 0
        inventory["Average_Daily_Demand"] = np.nan

    inventory["Total_Units_Sold"] = inventory["Total_Units_Sold"].fillna(0)

    # Forecast only when sales data has dates and the model loaded successfully.
    inventory["Forecast_Date"] = None
    inventory["Predicted_Next_Day_Demand"] = None
    inventory["Predicted_7_Day_Demand"] = None

    if (
        sales is not None
        and not sales.empty
        and demand_model is not None
    ):
        last_sales_date = sales["Date"].max().normalize()
        next_day = last_sales_date + pd.Timedelta(days=1)

        for index, row in inventory.iterrows():
            product_id = str(row["Product_ID"])
            if product_id not in product_codes:
                continue

            next_prediction = forecast_product_demand(product_id, next_day)
            predictions = [
                forecast_product_demand(
                    product_id, next_day + pd.Timedelta(days=offset)
                )
                for offset in range(7)
            ]

            if next_prediction is not None:
                inventory.at[index, "Forecast_Date"] = next_day.strftime("%Y-%m-%d")
                inventory.at[index, "Predicted_Next_Day_Demand"] = next_prediction

            if all(value is not None for value in predictions):
                inventory.at[index, "Predicted_7_Day_Demand"] = int(sum(predictions))

    # Reorder based on current stock thresholds.
    reorder = inventory[
        inventory["Current_Stock"] <= inventory["Reorder_Level"]
    ].copy()

    stock_gap = (
        reorder["Reorder_Level"] - reorder["Current_Stock"]
    ).clip(lower=0)

    if "Reorder_Quantity" in reorder.columns:
        configured_quantity = reorder["Reorder_Quantity"]
        reorder["Recommended_Order_Qty"] = configured_quantity.where(
            configured_quantity.notna() & (configured_quantity > 0),
            stock_gap,
        )
    else:
        reorder["Recommended_Order_Qty"] = stock_gap

    reorder["Recommended_Order_Qty"] = (
        reorder["Recommended_Order_Qty"].clip(lower=0).round().astype(int)
    )

    sort_columns = ["Current_Stock"]
    ascending = [True]
    if "Average_Daily_Demand" in reorder.columns:
        sort_columns = ["Average_Daily_Demand", "Current_Stock"]
        ascending = [False, True]

    reorder = reorder.sort_values(
        sort_columns, ascending=ascending, na_position="last"
    )
    reorder = make_json_safe(reorder)

    top_selling = []
    low_selling = []
    if not sales_summary.empty:
        ordered = sales_summary.sort_values("Total_Units_Sold", ascending=False)
        top_selling = make_json_safe(ordered.head(10)).to_dict(orient="records")
        low_selling = make_json_safe(
            ordered.tail(10).sort_values("Total_Units_Sold")
        ).to_dict(orient="records")

    summary = {
        "inventory_products": int(len(inventory)),
        "products_to_reorder": int(len(reorder)),
        "total_units_in_stock": float(inventory["Current_Stock"].sum()),
        "total_units_sold": total_units_sold,
    }

    if sales is None:
        message = "Inventory dataset analyzed."
    elif sales.empty:
        message = "Inventory analyzed; the sales file contains no valid records."
    else:
        message = "Inventory and sales datasets analyzed."

    forecast_columns = [
        "Product_ID", "Product_Name", "Current_Stock", "Forecast_Date",
        "Predicted_Next_Day_Demand", "Predicted_7_Day_Demand"
    ]
    available_forecast_columns = [column for column in forecast_columns if column in inventory.columns]
    forecast_rows = inventory[available_forecast_columns].copy() if available_forecast_columns else pd.DataFrame()
    if not forecast_rows.empty:
        forecast_rows = forecast_rows[forecast_rows["Predicted_Next_Day_Demand"].notna() | forecast_rows["Predicted_7_Day_Demand"].notna()]
        forecast_rows = make_json_safe(forecast_rows).to_dict(orient="records")
    else:
        forecast_rows = []

    return {
        "summary": summary,
        "replenishment": reorder.to_dict(orient="records"),
        "forecast": forecast_rows,
        "top_selling": top_selling,
        "low_selling": low_selling,
        "daily_sales": daily_sales,
        "model_status": model_status,
        "message": message,
    }


def calculate_profit_insights(inventory, sales):
    """Calculate historical gross profit from uploaded sales and inventory costs."""
    inventory = clean_inventory(inventory)
    sales = clean_sales(sales)
    if sales.empty or "Unit_Cost_INR" not in inventory.columns:
        return {"available": False, "message": "Sales records and Unit_Cost_INR are required for profit analysis.", "summary": {}, "top_products": []}

    costs = inventory[["Product_ID", "Unit_Cost_INR"]].drop_duplicates("Product_ID")
    names = inventory[["Product_ID", "Product_Name"]].drop_duplicates("Product_ID")
    merged = sales.merge(costs, on="Product_ID", how="left")
    merged = merged.dropna(subset=["Unit_Cost_INR"])
    if merged.empty:
        return {"available": False, "message": "No sales rows matched inventory unit costs.", "summary": {}, "top_products": []}

    if "Sales_Amount_INR" in merged.columns:
        merged["Revenue"] = pd.to_numeric(merged["Sales_Amount_INR"], errors="coerce")
    else:
        price = pd.to_numeric(merged.get("Unit_Price_INR", 0), errors="coerce").fillna(0)
        discount = pd.to_numeric(merged.get("Discount_Percent", 0), errors="coerce").fillna(0) if "Discount_Percent" in merged.columns else 0
        merged["Revenue"] = merged["Units_Sold"] * price * (1 - discount / 100)
    merged["Revenue"] = pd.to_numeric(merged["Revenue"], errors="coerce").fillna(0)
    merged["Cost"] = merged["Units_Sold"] * merged["Unit_Cost_INR"]
    merged["Gross_Profit"] = merged["Revenue"] - merged["Cost"]
    grouped = merged.groupby("Product_ID", as_index=False).agg(
        Revenue=("Revenue", "sum"), Cost=("Cost", "sum"), Gross_Profit=("Gross_Profit", "sum"), Units_Sold=("Units_Sold", "sum")
    ).merge(names, on="Product_ID", how="left")
    grouped["Product_Name"] = grouped["Product_Name"].fillna("")
    grouped["Profit_Margin_Percent"] = np.where(grouped["Revenue"] != 0, grouped["Gross_Profit"] / grouped["Revenue"] * 100, 0)
    grouped = grouped.sort_values("Gross_Profit", ascending=False).head(10)
    revenue_total = float(merged["Revenue"].sum())
    cost_total = float(merged["Cost"].sum())
    profit_total = revenue_total - cost_total
    margin_total = (profit_total / revenue_total * 100) if revenue_total else 0
    return {
        "available": True,
        "summary": {"total_revenue": round(revenue_total, 2), "cost_of_goods_sold": round(cost_total, 2), "gross_profit": round(profit_total, 2), "profit_margin_percent": round(margin_total, 2)},
        "top_products": make_json_safe(grouped).to_dict(orient="records")
    }


@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "message": "Inventory API is running.",
        "model_status": model_status,
    })


@app.post("/api/analyze")
@login_required
def analyze():
    try:
        inventory_file = request.files.get("inventory")
        sales_file = request.files.get("sales")

        if inventory_file is None or not inventory_file.filename:
            return jsonify({"error": "Please upload an inventory CSV file."}), 400

        inventory = read_uploaded_csv(inventory_file)
        sales = None

        if sales_file and sales_file.filename:
            sales = read_uploaded_csv(sales_file)

        result = analyze_datasets(inventory, sales)

        # Profit figures are calculated and returned only for Admin sessions.
        if getattr(g, "current_user", {}).get("role") == "admin" and sales is not None:
            result["profit_insights"] = calculate_profit_insights(inventory, sales)

        return jsonify(result)

    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception:
        app.logger.exception("Dataset analysis failed")
        return jsonify({
            "error": (
                "The server could not process these datasets. "
                "Check the CSV columns and backend terminal."
            )
        }), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
