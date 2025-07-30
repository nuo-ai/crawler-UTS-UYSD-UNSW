import os
import json
import pandas as pd
from openpyxl import Workbook
import yaml
import re
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename

# --- Dynamic Path Configuration ---
# Get the directory of the currently running script (canva_converter)
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_ROOT)

# --- Flask App Configuration ---
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'uploads')
PROCESSED_FOLDER = os.path.join(APP_ROOT, 'processed')
ALLOWED_EXTENSIONS = {'xlsx'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['SECRET_KEY'] = 'supersecretkey' # Required for flashing messages

# --- Ensure directories exist ---
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# --- Core Processing Logic (Adapted from generate_canva_sheet.py) ---

def load_features_config():
    """Loads the features configuration from the crawler's config directory."""
    config_path = os.path.join(PROJECT_ROOT, 'crawler', 'config', 'features_config.yaml')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            # Return a mapping of column_name to its Chinese name
            return {feature['column_name']: feature['name'] for feature in config.get('features', [])}
    except FileNotFoundError:
        print(f"[Error] Features config not found at: {config_path}")
        return {}
    except Exception as e:
        print(f"[Error] Error loading features config: {e}")
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

def process_excel_file(source_path, output_dir, features_map):
    """
    Processes a single source Excel file and generates a Canva-ready CSV file.
    Returns the path to the generated file or None if an error occurs.
    """
    try:
        df = pd.read_excel(source_path)
        
        # --- Prepare the output DataFrame ---
        output_data = []
        
        # Define the columns for the output file
        source_columns = {
            'Price': 'rent_pw', 'Address': 'address', 'Suburb': 'suburb',
            'Bedrooms': 'bedrooms', 'Bathrooms': 'bathrooms', 'Parking': 'parking_spaces',
            'Available_Date': 'available_date', 'Inspection_Time': 'inspection_times',
            'Property_URL': 'property_url',
            'images': 'images'
        }
        
        feature_columns_source = sorted([col for col in df.columns if col.startswith('has_')])
        if 'furnishing_status' in df.columns and 'furnishing_status' not in feature_columns_source:
            feature_columns_source.append('furnishing_status')

        # Process each row from the source DataFrame
        for index, row in df.iterrows():
            processed_row = {}

            # Process standard columns
            for header, source_col in source_columns.items():
                if header == 'Available_Date':
                    processed_row[header] = format_available_date(row.get(source_col))
                elif header == 'Inspection_Time':
                    processed_row[header] = format_inspection_time(row.get(source_col))
                else:
                    processed_row[header] = row.get(source_col, '')

            # Process feature columns
            for feature_col in feature_columns_source:
                header_name = features_map.get(feature_col, feature_col)
                if feature_col == 'furnishing_status':
                    processed_row[header_name] = format_furnishing_status(row.get(feature_col))
                elif feature_col == 'has_gas_cooking':
                    processed_row[header_name] = "✔️" if row.get(feature_col) == True or str(row.get(feature_col)).lower() == 'true' else "❔"
                else:
                    processed_row[header_name] = format_feature_to_emoji(row.get(feature_col))
            
            output_data.append(processed_row)

        # Create the final DataFrame
        output_df = pd.DataFrame(output_data)

        # --- Save to CSV ---
        source_basename = os.path.basename(source_path)
        # Remove original extension and add .csv
        source_filename_no_ext = os.path.splitext(source_basename)[0]
        output_filename = f"canva_{source_filename_no_ext}.csv"
        
        output_path = os.path.join(output_dir, output_filename)
        
        # Save to CSV with UTF-8-BOM encoding for better compatibility
        output_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        return output_filename

    except Exception as e:
        print(f"[Error] Failed to process file {os.path.basename(source_path)}: {e}")
        return None

# --- Flask Routes ---

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
def index():
    """Renders the main upload page."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handles file uploads and processing."""
    if 'files[]' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    files = request.files.getlist('files[]')
    
    processed_filenames = []
    has_errors = False
    
    # Load the features config once per request
    features_map = load_features_config()
    if not features_map:
        flash('错误：无法加载特征配置文件。请检查服务器日志。')
        has_errors = True

    if not has_errors:
        for file in files:
            if not file or not file.filename:
                continue # Skip empty or invalid file submissions
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(upload_path)
                
                # Process the uploaded file
                processed_name = process_excel_file(upload_path, app.config['PROCESSED_FOLDER'], features_map)
                if processed_name:
                    processed_filenames.append(processed_name)
                else:
                    has_errors = True
            else:
                flash(f"不允许的文件类型: {file.filename}")
                has_errors = True

    if not processed_filenames and not has_errors:
        flash('没有选择文件或处理失败。')
        return redirect(url_for('index'))

    if has_errors:
         flash('部分文件处理失败。')

    return render_template('results.html', filenames=processed_filenames)

@app.route('/download/<filename>')
def download_file(filename):
    """Serves a processed file for download."""
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
