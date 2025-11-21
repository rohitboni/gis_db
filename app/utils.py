from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
import json


def geometry_to_geojson(geometry):
    """Convert PostGIS geometry to GeoJSON format"""
    if geometry is None:
        return None
    
    try:
        shapely_geom = to_shape(geometry)
        return mapping(shapely_geom)
    except Exception:
        return None

