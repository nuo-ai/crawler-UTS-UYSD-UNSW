import pandas as pd
import yaml
import ast
from collections import OrderedDict

# Helper to represent OrderedDict in YAML
class OrderedDumper(yaml.Dumper):
    def represent_dict(self, data):
        return self.represent_mapping('tag:yaml.org,2002:map', data.items())

OrderedDumper.add_representer(OrderedDict, OrderedDumper.represent_dict)

def load_existing_features(yaml_path):
    """Loads existing features and their keywords from the YAML file."""
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        config = {'features': []}

    existing_keywords = set()
    if 'features' in config and config['features']:
        for feature in config['features']:
            if 'keywords' in feature and feature['keywords']:
                for keyword in feature['keywords']:
                    existing_keywords.add(keyword.lower())
    return config, existing_keywords

def extract_and_update_features(csv_path, yaml_path, feature_column_name='features'):
    """Extracts features from CSV, finds new ones, and updates the YAML config."""
    print(f"Loading data from: {csv_path}")
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: The file was not found at {csv_path}")
        return
    except Exception as e:
        print(f"An error occurred while reading the CSV file: {e}")
        return

    if feature_column_name not in df.columns:
        print(f"Error: Column '{feature_column_name}' not found in the CSV file.")
        print(f"Available columns are: {list(df.columns)}")
        return

    print(f"Extracting features from column '{feature_column_name}'...")
    all_features = set()
    for item in df[feature_column_name].dropna():
        try:
            # Safely evaluate the string representation of the list
            feature_list = ast.literal_eval(item)
            if isinstance(feature_list, list):
                for feature in feature_list:
                    all_features.add(feature.strip().lower())
        except (ValueError, SyntaxError):
            # Handle cases where the column is not a list string
            # Assuming it might be a comma-separated string
            for feature in str(item).split(','):
                if feature.strip():
                    all_features.add(feature.strip().lower())

    print(f"Found {len(all_features)} unique features in the dataset.")

    print(f"Loading existing configuration from: {yaml_path}")
    config, existing_keywords = load_existing_features(yaml_path)
    print(f"Found {len(existing_keywords)} existing keywords in the config.")

    new_keywords = all_features - existing_keywords

    if not new_keywords:
        print("No new features to add. The configuration file is already up-to-date.")
        return

    print(f"Found {len(new_keywords)} new features to add: {sorted(list(new_keywords))}")

    if 'features' not in config or config['features'] is None:
        config['features'] = []

    # Add a comment section for newly discovered features
    # This is a simple append, for more complex structures, manual editing might be better
    # config['features'].append("\n# --- Automatically Discovered Features ---")

    for keyword in sorted(list(new_keywords)):
        # Create a user-friendly name and a valid column name
        display_name = keyword.replace('_', ' ').title()
        column_name = f"has_{keyword.replace(' ', '_').lower()}"
        
        new_feature = OrderedDict([
            ('name', display_name),
            ('column_name', column_name),
            ('keywords', [keyword])
        ])
        config['features'].append(new_feature)

    print(f"Updating {yaml_path} with new features...")
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, Dumper=OrderedDumper, default_flow_style=False, allow_unicode=True, indent=2)

    print("Update complete.")

if __name__ == '__main__':
    # --- CONFIGURATION ---
    # 1. Path to your CSV data file
    CSV_FILE_PATH = r'C:\Users\nuoai\Downloads\20250729_234048_Combined_2274properties - 工作表1.csv'
    
    # 2. Path to your features configuration file
    YAML_CONFIG_PATH = r'c:\Users\nuoai\Desktop\crawler-UTS-UYSD-UNSW\dist\crawler\config\features_config.yaml'
    
    # 3. The exact name of the column in your CSV that contains the feature list
    FEATURE_COLUMN = 'property_features'
    # --- END CONFIGURATION ---

    extract_and_update_features(CSV_FILE_PATH, YAML_CONFIG_PATH, FEATURE_COLUMN)