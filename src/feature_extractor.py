from typing import Dict, Any
from .data_models import PropertyFeatures

class FeatureExtractor:
    """从房源文本中提取各种Features。"""

    def __init__(self, features_config: Dict[str, Any]):
        self.features_config = features_config
        self.legacy_keywords = {
            'furnished': ['furnished', 'fully furnished', 'incl. furniture'],
            'partly furnished': ['partly furnished', 'semi-furnished'],
            'unfurnished': ['unfurnished'],
            'split system': ['split system', 'split-system'],
            'ducted': ['ducted', 'central'],
            'air conditioning': ['air conditioning', 'air-conditioning', 'air con', 'air-con']
        }

    def extract(self, text_blob: str) -> PropertyFeatures:
        """根据配置和关键字提取所有features。"""
        features = PropertyFeatures(self.features_config)
        text_blob = text_blob.lower()

        # 1. Dynamic feature extraction from config
        if self.features_config and 'features' in self.features_config:
            for feature_config in self.features_config['features']:
                column_name = feature_config.get('column_name', '')
                keywords = feature_config.get('keywords', [])
                
                if column_name and keywords and hasattr(features, column_name):
                    for keyword in keywords:
                        if keyword.lower() in text_blob:
                            setattr(features, column_name, True)
                            break # Move to the next feature once one keyword is found

        # 2. Legacy air conditioning and furnishing status extraction
        self._extract_legacy_features(features, text_blob)

        return features

    def _extract_legacy_features(self, features: PropertyFeatures, text_blob: str):
        """提取旧版的空调和家具信息以保证后向兼容。"""
        # Air Conditioning
        ac_found = False
        if any(keyword in text_blob for keyword in self.legacy_keywords['split system']):
            features.air_conditioning_type = 'split_system'
            ac_found = True
        elif any(keyword in text_blob for keyword in self.legacy_keywords['ducted']):
            features.air_conditioning_type = 'ducted'
            ac_found = True
        elif any(keyword in text_blob for keyword in self.legacy_keywords['air conditioning']):
            features.air_conditioning_type = 'yes'
            ac_found = True
        
        if ac_found:
            features.has_air_conditioning = True

        # Furnishing Status
        if any(keyword in text_blob for keyword in self.legacy_keywords['furnished']):
            features.furnishing_status = 'furnished'
        elif any(keyword in text_blob for keyword in self.legacy_keywords['partly furnished']):
            features.furnishing_status = 'partly_furnished'
        # 'unfurnished' is the default, so no explicit check is needed unless specified
