"""
Utility functions to extract metadata from filenames and file content
"""
from pathlib import Path
from typing import Dict, Optional, Any


def extract_state_district_from_filename(filename: str) -> Dict[str, Optional[str]]:
    """
    Extract state and district from filename.
    
    Common patterns:
    - Bengaluru_Rural.geojson -> district: "Bengaluru Rural"
    - Karnataka_Bengaluru_Rural.geojson -> state: "Karnataka", district: "Bengaluru Rural"
    - state_district.geojson -> state, district
    """
    stem = Path(filename).stem
    
    # Try to split by common separators
    parts = stem.replace('_', ' ').replace('-', ' ').split()
    
    # Common state names in India
    indian_states = [
        'karnataka', 'kerala', 'tamil nadu', 'andhra pradesh', 'telangana',
        'maharashtra', 'gujarat', 'rajasthan', 'punjab', 'haryana',
        'uttar pradesh', 'bihar', 'west bengal', 'odisha', 'assam',
        'madhya pradesh', 'chhattisgarh', 'jharkhand', 'uttarakhand',
        'himachal pradesh', 'goa', 'delhi', 'jammu kashmir'
    ]
    
    state = None
    district = None
    
    # Check if first part matches a state
    first_part_lower = parts[0].lower() if parts else ''
    for indian_state in indian_states:
        if indian_state in first_part_lower or first_part_lower in indian_state:
            state = parts[0].title()
            if len(parts) > 1:
                district = ' '.join(parts[1:]).title()
            break
    
    # If no state found, assume all parts are district name
    if not state:
        district = ' '.join(parts).title()
    
    # Special case: If filename suggests Karnataka (common case)
    stem_lower = stem.lower()
    if 'karnataka' in stem_lower or 'bangalore' in stem_lower or 'bengaluru' in stem_lower:
        state = 'Karnataka'
    
    return {
        'state': state,
        'district': district or stem.title()
    }


def extract_state_district_from_properties(features: list) -> Dict[str, Optional[str]]:
    """
    Extract state and district from feature properties.
    Looks at first few features to determine state/district.
    """
    if not features:
        return {'state': None, 'district': None}
    
    # Check first few features for state/district info
    state = None
    district = None
    
    for feature in features[:10]:  # Check first 10 features
        props = feature.get('properties', {})
        
        # Try different field name variations
        if not state:
            state = (
                props.get('State_Name') or
                props.get('state') or
                props.get('STATE') or
                props.get('State') or
                props.get('state_name')
            )
        
        if not district:
            district = (
                props.get('District_Name') or
                props.get('district') or
                props.get('DISTRICT') or
                props.get('District') or
                props.get('district_name')
            )
        
        if state and district:
            break
    
    return {
        'state': state,
        'district': district
    }

