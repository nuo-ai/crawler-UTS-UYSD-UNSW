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

def find_all_source_files(directory=OUTPUT_DIR):
    """Finds all source .xlsx files that have not been processed yet."""
    if not os.path.exists(directory):
        print(f"[Error] Output directory not found: {directory}")
        return []
    
    all_files = os.listdir(directory)
    source_files = [f for f in all_files if f.endswith('.xlsx') and not f.startswith('canva_')]
    
    processed_files = {f.replace('canva_', '') for f in all_files if f.startswith('canva_')}
    
    # Find files that are in source_files but not in processed_files
    unprocessed_files = [f for f in source_files if f not in processed_files]
    
    return [os.path.join(directory, f) for f in unprocessed_files]

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
    print("--- Canva Batch Processor ---")

    # --- 1. Find all source files ---
    source_files = find_all_source_files()
    if not source_files:
        print(f"No new source .xlsx files found in '{OUTPUT_DIR}' to process.")
        return

    print(f"Found {len(source_files)} new file(s) to process.")
    
    for source_file in source_files:
        print(f"\n--- Processing: {os.path.basename(source_file)} ---")
        try:
            df = pd.read_excel(source_file)
            
            # --- 2. Setup Output Excel ---
            wb = Workbook()
            ws = wb.active
            if ws is None:
                print("[Error] Could not create a new worksheet.")
                continue # Skip to next file
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
            
            # Dynamically find feature columns from the current dataframe
            feature_columns_source = sorted([col for col in df.columns if col.startswith('has_')])
            if 'furnishing_status' in df.columns and 'furnishing_status' not in feature_columns_source:
                feature_columns_source.append('furnishing_status')

            for feature_col in feature_columns_source:
                feature_name = feature_col
                headers.append(feature_name)

            for i in range(1, MAX_IMAGES_PER_PROPERTY + 1):
                headers.append(f'Image_{i}')
            
            ws.append(headers)

            # --- 4. Process Each Property ---
            print(f"Found {len(df)} properties in this file.")
            for i, index in enumerate(df.index):
                row = df.loc[index]
                
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
                    feature_name = feature_col
                    if feature_col == 'furnishing_status':
                        processed_row[feature_name] = format_furnishing_status(row.get(feature_col))
                    elif feature_col == 'has_gas_cooking':
                        processed_row[feature_name] = "✔️" if row.get(feature_col) == True or str(row.get(feature_col)).lower() == 'true' else "❔"
                    else:
                        processed_row[feature_name] = format_feature_to_emoji(row.get(feature_col))

                final_row_data = [processed_row.get(h, '') for h in headers]
                ws.append(final_row_data)

            # --- 5. Save Final Excel File ---
            source_filename = os.path.basename(source_file)
            output_excel_path = os.path.join(OUTPUT_DIR, f"canva_{source_filename}")
            wb.save(output_excel_path)
            print(f"Successfully generated: {output_excel_path}")

        except Exception as e:
            print(f"[Error] Failed to process file {os.path.basename(source_file)}: {e}")

    print("\n--- Batch processing complete. ---")

if __name__ == "__main__":
    main()
