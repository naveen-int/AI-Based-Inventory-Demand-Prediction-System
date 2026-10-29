# AI-Based Inventory Demand Prediction System

## Features
- Login and Staff signup
- Admin and Staff roles
- Both roles can upload inventory/sales CSVs, view dashboard, sales analysis, demand forecasts (when the trained model supports the product), and reorder reports
- Admin-only Profit Insights: historical gross profit, margin, and Top 10 products by gross profit
- Larger readable text; navy/teal design; no chart animations

## Setup (Windows / VS Code)
1. Open a terminal in `backend`.
2. Create/activate your virtual environment if you use one.
3. Install packages: `pip install -r requirements.txt`.
4. Create the first Admin account: `python init_admin.py`.
5. Start Flask: `python app.py`.
6. Open `frontend/login.html` using VS Code Live Server (port 5500).
7. Create Staff accounts using the Signup page. Public signup cannot create Admin accounts.

## CSV columns
Inventory requires `Product_ID`, `Current_Stock`, `Reorder_Level`. Profit Insights additionally requires `Unit_Cost_INR`; sales data should include `Date`, `Product_ID`, and `Units_Sold`. If `Sales_Amount_INR` is supplied, it is used as revenue. Otherwise revenue is estimated from unit price and discount when available.

## Notes
- Profit figures are historical gross profit, not net profit or future profit predictions.
- The backend enforces login before analysis and only includes profit data in Admin responses.
- For production, set a long random `INVENTORY_SECRET_KEY`, set `FLASK_DEBUG=false`, use HTTPS, and set `COOKIE_SECURE=true`.
- Keep your existing trained model file at `backend/models/random_forest_model.pkl`; this update does not include or replace the model/data files.
