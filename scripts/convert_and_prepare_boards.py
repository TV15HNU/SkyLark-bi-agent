import os
import pandas as pd
import numpy as np

def prepare_boards():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend_data_dir = os.path.join(base_dir, "backend", "data")
    os.makedirs(backend_data_dir, exist_ok=True)
    
    deals_path = os.path.join(base_dir, "Deal funnel Data.xlsx")
    wo_path = os.path.join(base_dir, "Work_Order_Tracker Data.xlsx")
    
    print(f"Reading Deals from: {deals_path}")
    deals_df = pd.read_excel(deals_path)
    
    # 1. Deals: drop rows where Deal Name or Deal Status is the header itself (duplicate embedded header rows)
    deals_cleaned = deals_df[deals_df["Deal Status"] != "Deal Status"].copy()
    deals_cleaned = deals_cleaned.dropna(subset=["Deal Name"])
    
    # Format date columns cleanly
    for date_col in ["Close Date (A)", "Tentative Close Date", "Created Date"]:
        if date_col in deals_cleaned.columns:
            deals_cleaned[date_col] = pd.to_datetime(deals_cleaned[date_col], errors='coerce').dt.strftime('%Y-%m-%d')
            
    deals_out = os.path.join(backend_data_dir, "deals_for_monday_import.csv")
    deals_cleaned.to_csv(deals_out, index=False)
    print(f"Saved cleaned Deals CSV to {deals_out} ({len(deals_cleaned)} rows)")
    
    print(f"Reading Work Orders from: {wo_path}")
    # Work Orders sheet has row 0 as empty, row 1 as header
    wo_df = pd.read_excel(wo_path, header=1)
    wo_cleaned = wo_df.dropna(subset=["Deal name masked"]).copy()
    
    # Format date columns in Work Orders
    for date_col in [
        "Data Delivery Date", "Date of PO/LOI", "Probable Start Date", 
        "Probable End Date", "Last invoice date", "Collection Date"
    ]:
        if date_col in wo_cleaned.columns:
            wo_cleaned[date_col] = pd.to_datetime(wo_cleaned[date_col], errors='coerce').dt.strftime('%Y-%m-%d')
            
    wo_out = os.path.join(backend_data_dir, "work_orders_for_monday_import.csv")
    wo_cleaned.to_csv(wo_out, index=False)
    print(f"Saved cleaned Work Orders CSV to {wo_out} ({len(wo_cleaned)} rows)")

if __name__ == "__main__":
    prepare_boards()
