# AI-Based Inventory Demand Prediction and Intelligent Replenishment System

An AI-powered inventory management system that helps Indian shops and supermarkets predict demand, analyse sales, monitor stock, and make intelligent replenishment decisions.

## Project Overview

The system combines machine learning, inventory monitoring, and sales analytics through a web-based application. It uses a trained Random Forest Regression model to predict demand and identify products requiring replenishment.

## Objectives

- Predict product demand using machine learning.
- Identify low-stock products.
- Analyse sales trends and product performance.
- Generate replenishment reports.
- Provide role-based access to financial insights.

## Key Features

- **Inventory Analysis:** Monitor stock levels and reorder thresholds.
- **Demand Prediction:** Estimate product demand using Random Forest Regression.
- **Sales Analytics:** Display daily sales, revenue, and product performance.
- **Smart Replenishment:** Identify products requiring restocking.
- **Interactive Dashboard:** Present inventory metrics, tables, and charts.
- **Top and Low-Selling Products:** Analyse product sales performance.
- **CSV Export:** Download replenishment reports.
- **Admin Profit Insights:** Calculate historical revenue, cost of goods sold, gross profit, and gross margin.
- **User Authentication:** Support login and Staff registration with role-based access.
- **Supplier and Purchase Order Analysis:** Use supplier details, lead times, and order information.

## Technologies Used

| Component | Technologies |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, Flask |
| Machine Learning | Scikit-learn, Random Forest Regression |
| Data Processing | Pandas, NumPy |
| Model Persistence | Joblib |
| Database | SQLite |
| Visualisation | Chart.js |
| Tools | VS Code, Git, GitHub |

## Dataset Description

- **Inventory Dataset:** Product details, prices, stock levels, reorder levels, and supplier information.
- **Daily Sales Dataset:** Sales dates, quantities, discounts, promotions, and revenue.
- **Supplier Dataset:** Supplier details, cities, lead times, and minimum order quantities.
- **Purchase Order Dataset:** Order quantities, delivery dates, and costs.

## Machine Learning Approach

Random Forest Regression predicts numerical demand using features such as product code, day of the week, day of the month, and month. The trained model is saved and loaded using Joblib. Prediction performance should be evaluated on unseen data.

## System Workflow

1. User logs in.
2. Inventory and sales data are uploaded and processed.
3. The dashboard displays stock summaries and sales analytics.
4. The model generates demand predictions.
5. The system identifies products requiring replenishment.
6. Users export replenishment reports, while Admin users access Profit Insights.

## Security

- Role-based access for Admin and Staff.
- Backend authentication and authorization checks.
- Secure password hashing.
- Avoid committing credentials and secrets to GitHub.

## Future Enhancements

- Automated low-stock notifications.
- Supplier-aware replenishment.
- Multi-store inventory management.
- Advanced forecasting models.
- Cloud deployment.

## Project Information

**Title:** AI-Based Inventory Demand Prediction System.

**Domain:** Artificial Intelligence, Machine Learning, and Web Development

