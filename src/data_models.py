from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

# 全局变量，用于存储从配置文件加载的Feature定义
FEATURES_CONFIG: Dict[str, Any] = {}

@dataclass
class PropertyFeatures:
    """存储房源的各种Feature，动态初始化。"""

    def __init__(self, features_config: Dict[str, Any]):
        # Legacy fields for backward compatibility
        self.furnishing_status: str = 'unfurnished'
        self.air_conditioning_type: str = 'none'
        self.has_air_conditioning: bool = False

        # Dynamically add feature fields from the loaded configuration
        if features_config and 'features' in features_config:
            for feature in features_config['features']:
                column_name = feature.get('column_name', '')
                if column_name:
                    # Initialize all feature flags to False
                    setattr(self, column_name, False)

@dataclass
class PropertyListing:
    """存储单个房源的所有信息。"""
    listing_id: Optional[str] = None
    suburb: Optional[str] = None
    address: Optional[str] = None
    price: Optional[str] = None
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    parking: Optional[int] = None
    title: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    features: PropertyFeatures = field(default_factory=lambda: PropertyFeatures(FEATURES_CONFIG))
    cover_image_url: Optional[str] = None
    images: List[str] = field(default_factory=list)
    agent_name: Optional[str] = None
    agent_phone: Optional[str] = None
    agency_name: Optional[str] = None
    raw_features_text: Optional[str] = None
    date_scraped: Optional[str] = None

def set_features_config(config: Dict[str, Any]):
    """设置全局的FEATURES_CONFIG变量。"""
    global FEATURES_CONFIG
    FEATURES_CONFIG = config
