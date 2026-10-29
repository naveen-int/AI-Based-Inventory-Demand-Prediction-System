Upload user-provided CSV files through the frontend.

Inventory CSV required columns:
- Product_ID
- Current_Stock
- Reorder_Level

Optional inventory columns:
- Product_Name
- Reorder_Quantity
- Lead_Time_Days
- Category

Sales CSV is optional. If provided, it must contain:
- Date
- Product_ID
- Units_Sold

Optional sales columns:
- Product_Name
- Category
- Unit_Price_INR
- Discount_Percent
- Promotion_Flag
- Sales_Amount_INR
- Stockout_Flag

The application does not require a fixed general dataset. Example files can be kept in this folder for development/testing only.
