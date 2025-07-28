import pandas as pd
from openpyxl import Workbook
import os
from datetime import datetime
import re
import yaml

# --- Configuration ---
CONFIG_DIR = 'config'
OUTPUT_DIR = 'output'
MAX_IMAGES_PER_PROPERTY = 4 # This will just create empty columns
OUTPUT_EXCEL_PATH = os.path.join(OUTPUT_DIR, f"canva_ready_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

def find_latest_source_file(directory=OUTPUT_DIR):
    """Finds the most recently created 'Combined' or other .xlsx file in the output directory."""
    if not os.path.exists(directory):
        return None
    
    all_xlsx_files = [f for f in os.listdir(directory) if f.endswith('.xlsx') and not f.startswith('canva_ready')]
    if not all_xlsx_files:
        return None
        
    combined_files = [f for f in all_xlsx_files if f.startswith('Combined')]
    
    if combined_files:
        latest_file = max(combined_files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    else:
        latest_file = max(all_xlsx_files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
        
    return os.path.join(directory, latest_file)

def load_features_config():
    """Loads the features configuration to map column names to Chinese names."""
    config_path = os.path.join(CONFIG_DIR, 'features_config.yaml')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return {feature['column_name']: feature['name'] for feature in config.get('features', [])}
    except FileNotFoundError:
        print(f"[Warning] {config_path} not found. Feature names will be derived from column names.")
        return {}
    except Exception as e:
        print(f"[Warning] Error loading features config: {e}. Feature names will be derived from column names.")
        return {}

def format_available_date(date_str):
    """Formats the available date string into Chinese."""
    if not date_str or pd.isna(date_str):
        return "暂无"
    date_str = str(date_str).strip()
    if 'now' in date_str.lower():
        return "可立即入住"
    try:
        date_str_cleaned = re.sub(r'(Available from|Available)', '', date_str, flags=re.IGNORECASE).strip()
        dt = pd.to_datetime(date_str_cleaned).to_pydatetime()
        return f"{dt.year}年{dt.month}月{dt.day}日"
    except (ValueError, TypeError):
        return date_str

def format_inspection_time(time_str):
    """Formats the inspection time string into Chinese."""
    if not time_str or pd.isna(time_str) or 'no ' in time_str.lower() or 'no inspection' in time_str.lower():
        return "暂无公布 - 需预约看房"
    try:
        cleaned_time = str(time_str).replace('Inspection', '').strip()
        return cleaned_time if cleaned_time else "暂无公布 - 需预约看房"
    except Exception:
        return "暂无公布 - 需预约看房"

def format_feature_to_emoji(value):
    """Formats boolean feature value into an emoji."""
    if value == True or str(value).lower() == 'true':
        return "✔️"
    return "❌"

def format_furnishing_status(value):
    """Formats furnishing status string into an emoji."""
    if isinstance(value, str) and value.lower() == 'furnished':
        return "✔️"
    return "❌"

def main():
    """Main function to generate the Canva-ready Excel sheet."""
    print("--- Canva Sheet Generator (Text-Only) ---")

    # --- 1. Find and Load Source Data ---
    source_file = find_latest_source_file()
    if not source_file:
        print(f"[Error] No source .xlsx file found in '{OUTPUT_DIR}' directory.")
        return
    print(f"Processing source file: {source_file}")
    df = pd.read_excel(source_file)
    
    feature_name_map = load_features_config()

    # --- 2. Setup Output Excel ---
    wb = Workbook()
    ws = wb.active
    if ws is None:
        print("[Error] Could not create a new worksheet.")
        return
    ws.title = "Canva Bulk Create Data"

    # --- 3. Define Headers ---
    source_columns = {
        'Price': 'rent_pw',
        'Address': 'address',
        'Suburb': 'suburb',
        'Bedrooms': 'bedrooms',
        'Bathrooms': 'bathrooms',
        'Parking': 'parking_spaces',
        'Available_Date': 'available_date',
        'Inspection_Time': 'inspection_times',
        'Property_URL': 'property_url'
    }
    
    headers = list(source_columns.keys())
    
    # Explicitly define and order feature columns
    feature_columns_source = sorted([col for col in df.columns if col.startswith('has_')])
    # Add furnishing_status if it exists and is not already included
    if 'furnishing_status' in df.columns and 'furnishing_status' not in feature_columns_source:
        feature_columns_source.append('furnishing_status')

    for feature_col in feature_columns_source:
        # Use original column name as header, per user request
        feature_name = feature_col
        headers.append(feature_name)

    for i in range(1, MAX_IMAGES_PER_PROPERTY + 1):
        headers.append(f'Image_{i}')
    
    ws.append(headers)

    # --- 4. Process Each Property ---
    print(f"Found {len(df)} properties to process.")
    for i, index in enumerate(df.index):
        row = df.loc[index]
        print(f"  - Processing property {i + 1}/{len(df)}: {row.get(source_columns['Address'], 'N/A')}")
        
        processed_row = {h: '' for h in headers}

        # Process and transform data
        for header, source_col in source_columns.items():
            if header == 'Available_Date':
                processed_row[header] = format_available_date(row.get(source_col))
            elif header == 'Inspection_Time':
                processed_row[header] = format_inspection_time(row.get(source_col))
            else:
                processed_row[header] = row.get(source_col, '')

        for feature_col in feature_columns_source:
            # Use original column name as the key
            feature_name = feature_col
            
            # Use the appropriate formatter
            if feature_col == 'furnishing_status':
                processed_row[feature_name] = format_furnishing_status(row.get(feature_col))
            else:
                processed_row[feature_name] = format_feature_to_emoji(row.get(feature_col))

        final_row_data = [processed_row.get(h, '') for h in headers]
        ws.append(final_row_data)

    # --- 5. Save Final Excel File ---
    try:
        wb.save(OUTPUT_EXCEL_PATH)
        print(f"\n--- Success! ---")
        print(f"Generated Canva-ready sheet: {OUTPUT_EXCEL_PATH}")
    except Exception as e:
        print(f"\n[Error] Failed to save the final Excel file: {e}")

if __name__ == "__main__":
    main()
