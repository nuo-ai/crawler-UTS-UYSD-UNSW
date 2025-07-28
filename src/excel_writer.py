import pandas as pd
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from .data_models import PropertyListing

class BatchWriter:
    """用于批量将房源数据写入Excel文件的类。"""
    def __init__(self, output_dir: str = 'output', buffer_size: int = 100):
        self.output_dir = output_dir
        self.buffer_size = buffer_size
        self.buffer: List[Dict[str, Any]] = []
        os.makedirs(self.output_dir, exist_ok=True)

    def add(self, listing: PropertyListing):
        """将单个房源信息添加到缓冲区。"""
        flat_data = self._flatten_listing(listing)
        self.buffer.append(flat_data)
        if len(self.buffer) >= self.buffer_size:
            self.flush()

    def _flatten_listing(self, listing: PropertyListing) -> Dict[str, Any]:
        """将嵌套的PropertyListing对象扁平化为字典。"""
        listing_dict = {
            "Listing ID": listing.listing_id,
            "Suburb": listing.suburb,
            "Address": listing.address,
            "Price": listing.price,
            "Property Type": listing.property_type,
            "Bedrooms": listing.bedrooms,
            "Bathrooms": listing.bathrooms,
            "Parking": listing.parking,
            "Title": listing.title,
            "URL": listing.url,
            "Description": listing.description,
            "Cover Image URL": listing.cover_image_url,
            "Images": ", ".join(listing.images),
            "Agent Name": listing.agent_name,
            "Agent Phone": listing.agent_phone,
            "Agency Name": listing.agency_name,
            "Raw Features Text": listing.raw_features_text,
            "Date Scraped": listing.date_scraped,
        }
        # Add feature fields dynamically
        if listing.features:
            for key, value in listing.features.__dict__.items():
                listing_dict[key] = value
        return listing_dict

    def flush(self, filename: str = "temp_listings.xlsx", expected_columns: Optional[List[str]] = None):
        """将缓冲区的数据写入Excel文件。"""
        if not self.buffer:
            return

        df = pd.DataFrame(self.buffer)
        
        # Reorder columns to match the expected order
        if expected_columns:
            # Ensure all expected columns are in the DataFrame, adding missing ones with default values
            current_columns = df.columns.tolist()
            final_columns = []
            for col in expected_columns:
                if col in current_columns:
                    final_columns.append(col)
                else:
                    df[col] = None
                    final_columns.append(col)
            
            # Add any columns from the dataframe that were not in expected_columns (preserves extra data)
            for col in current_columns:
                if col not in final_columns:
                    final_columns.append(col)

            df = df[final_columns]

        file_path = os.path.join(self.output_dir, filename)
        
        if os.path.exists(file_path):
            try:
                with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                    # This part is tricky with 'overlay'. A more robust way is reading, concatenating, and writing.
                    # For simplicity, we'll use a less efficient but safer method.
                    existing_df = pd.read_excel(file_path)
                    combined_df = pd.concat([existing_df, df], ignore_index=True)
                    combined_df.to_excel(writer, index=False, sheet_name='Sheet1')
            except Exception: # Fallback for corrupted files or other issues
                 df.to_excel(file_path, index=False)
        else:
            df.to_excel(file_path, index=False)
            
        print(f"已成功保存 {len(self.buffer)} 条记录到: {file_path}")
        self.buffer.clear()

    def save_to_file(self, listings: List[PropertyListing], filename: str, expected_columns: List[str]):
        """将所有房源数据保存到指定的Excel文件。"""
        for listing in listings:
            self.add(listing)
        if self.buffer:
            self.flush(filename, expected_columns)

def get_expected_columns(features_config: Dict[str, Any]) -> List[str]:
    """根据配置动态生成期望的Excel列顺序。"""
    base_columns = [
        "Listing ID", "Suburb", "Address", "Price", "Property Type", 
        "Bedrooms", "Bathrooms", "Parking", "Title", "URL", 
        "Description", "Cover Image URL", "Images", "Agent Name", 
        "Agent Phone", "Agency Name", "Raw Features Text", "Date Scraped"
    ]
    
    # Legacy feature columns
    feature_columns = ["furnishing_status", "air_conditioning_type", "has_air_conditioning"]
    
    # Dynamic feature columns from config
    if features_config and 'features' in features_config:
        for feature in features_config['features']:
            col_name = feature.get('column_name')
            if col_name and col_name not in feature_columns:
                feature_columns.append(col_name)
                
    return base_columns + feature_columns
