from shapely.geometry import shape, mapping
from shapely import wkt, wkb
from shapely.ops import transform as shapely_transform
from geoalchemy2.shape import from_shape
from geoalchemy2 import Geometry
from sqlalchemy import func
try:
    from pyproj import Transformer, CRS
    PYPROJ_AVAILABLE = True
except ImportError:
    PYPROJ_AVAILABLE = False


def validate_wgs84_bounds(geojson_geom):
    """
    Check if all coordinates in a GeoJSON geometry are within WGS84 bounds.
    
    Args:
        geojson_geom: GeoJSON geometry dict
    
    Returns:
        tuple: (is_valid, min_lon, min_lat, max_lon, max_lat)
    """
    if geojson_geom is None or 'coordinates' not in geojson_geom:
        return True, None, None, None, None
    
    coords = geojson_geom['coordinates']
    min_lon = float('inf')
    min_lat = float('inf')
    max_lon = float('-inf')
    max_lat = float('-inf')
    
    def extract_coords(coords_array):
        """Recursively extract coordinates"""
        if not coords_array:
            return
        
        if isinstance(coords_array[0], (int, float)):
            # This is a coordinate pair [lon, lat]
            if len(coords_array) >= 2:
                lon = float(coords_array[0])
                lat = float(coords_array[1])
                nonlocal min_lon, min_lat, max_lon, max_lat
                min_lon = min(min_lon, lon)
                min_lat = min(min_lat, lat)
                max_lon = max(max_lon, lon)
                max_lat = max(max_lat, lat)
        else:
            # Nested array - recurse
            for item in coords_array:
                extract_coords(item)
    
    extract_coords(coords)
    
    # Check if all coordinates are in WGS84 range
    is_valid = (-180 <= min_lon <= 180 and -180 <= max_lon <= 180 and
                -90 <= min_lat <= 90 and -90 <= max_lat <= 90)
    
    return is_valid, min_lon, min_lat, max_lon, max_lat


def detect_source_crs(min_lon, min_lat, max_lon, max_lat):
    """
    Detect the source coordinate reference system based on coordinate ranges.
    
    Args:
        min_lon, min_lat, max_lon, max_lat: Bounding box coordinates
    
    Returns:
        str: EPSG code as string, or None if cannot be determined
    """
    if not PYPROJ_AVAILABLE:
        return None
    
    # Calculate center coordinates
    center_x = (min_lon + max_lon) / 2
    center_y = (min_lat + max_lat) / 2
    
    # Check for UTM zones in India
    # UTM Zone 43N (EPSG:32643): Covers Western India including Karnataka, Goa, parts of Maharashtra
    # Easting range: ~200000-900000, Northing range: ~0-10000000
    # For Karnataka, typically Easting: ~700000-850000, Northing: ~1400000-1600000
    
    if (200000 <= center_x <= 900000 and 0 <= center_y <= 10000000):
        # This looks like UTM - determine zone based on center X coordinate
        # UTM Zone 43N: ~166000-833000 (theoretical), actual India coverage ~200000-900000
        # UTM Zone 44N: ~833000-833000 (theoretical)
        
        # For Karnataka/Bengaluru area, UTM Zone 43N is most likely
        # Bengaluru coordinates in UTM 43N: Easting ~700000-850000, Northing ~1200000-1600000
        if (700000 <= center_x <= 850000 and 1200000 <= center_y <= 1600000):
            return "EPSG:32643"  # UTM Zone 43N (WGS84 / UTM zone 43N)
        elif center_x < 833000:
            return "EPSG:32643"  # UTM Zone 43N
        else:
            return "EPSG:32644"  # UTM Zone 44N
    
    return None


def transform_geojson_coordinates(geojson_geom, source_crs, target_crs="EPSG:4326"):
    """
    Transform GeoJSON coordinates from source CRS to target CRS.
    
    Args:
        geojson_geom: GeoJSON geometry dict
        source_crs: Source CRS (e.g., "EPSG:32643")
        target_crs: Target CRS (default "EPSG:4326" for WGS84)
    
    Returns:
        GeoJSON geometry dict with transformed coordinates
    """
    if not PYPROJ_AVAILABLE:
        raise ValueError("pyproj is required for coordinate transformation. Install it with: pip install pyproj")
    
    if geojson_geom is None or 'coordinates' not in geojson_geom:
        return geojson_geom
    
    # Convert GeoJSON to Shapely geometry
    shapely_geom = shape(geojson_geom)
    
    # Create transformer
    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    
    # Transform geometry
    transformed_geom = shapely_transform(transformer.transform, shapely_geom)
    
    # Convert back to GeoJSON
    return mapping(transformed_geom)


def geojson_to_wkb_element(geojson_geom, srid=4326):
    """
    Convert GeoJSON geometry dict to GeoAlchemy2 WKBElement
    
    Automatically detects and transforms projected coordinates (like UTM) to WGS84.
    
    Args:
        geojson_geom: GeoJSON geometry dict (e.g., {"type": "Point", "coordinates": [lon, lat]})
        srid: Spatial reference system identifier (default 4326 for WGS84)
    
    Returns:
        WKBElement for GeoAlchemy2
    """
    if geojson_geom is None:
        raise ValueError("Geometry cannot be None")
    
    # Validate coordinates are in WGS84 range before converting
    is_valid, min_lon, min_lat, max_lon, max_lat = validate_wgs84_bounds(geojson_geom)
    
    if not is_valid and min_lon is not None:
        # Coordinates are out of WGS84 range - try to detect and transform
        print(f"Detected coordinates out of WGS84 range. "
              f"Bounds: longitude [{min_lon:.6f}, {max_lon:.6f}], latitude [{min_lat:.6f}, {max_lat:.6f}]. "
              f"Attempting to detect source CRS...")
        
        if PYPROJ_AVAILABLE:
            # Try to detect source CRS
            source_crs = detect_source_crs(min_lon, min_lat, max_lon, max_lat)
            
            if source_crs:
                print(f"Detected source CRS: {source_crs}. Transforming to WGS84 (EPSG:4326)...")
                try:
                    # Transform coordinates
                    geojson_geom = transform_geojson_coordinates(geojson_geom, source_crs, "EPSG:4326")
                    
                    # Validate transformed coordinates
                    is_valid, min_lon, min_lat, max_lon, max_lat = validate_wgs84_bounds(geojson_geom)
                    
                    if is_valid:
                        print(f"Successfully transformed coordinates. New bounds: "
                              f"longitude [{min_lon:.6f}, {max_lon:.6f}], latitude [{min_lat:.6f}, {max_lat:.6f}]")
                    else:
                        raise ValueError(f"Transformation failed. Coordinates still out of WGS84 range after transformation.")
                except Exception as e:
                    raise ValueError(
                        f"Failed to transform coordinates from {source_crs} to WGS84: {str(e)}. "
                        f"Please ensure your GeoJSON file uses WGS84 (EPSG:4326) coordinates, "
                        f"or manually convert it using QGIS, ogr2ogr, or Python (with pyproj)."
                    )
            else:
                raise ValueError(
                    f"Could not detect source coordinate system. "
                    f"Coordinates are out of WGS84 range. "
                    f"Bounds: longitude [{min_lon:.6f}, {max_lon:.6f}], latitude [{min_lat:.6f}, {max_lat:.6f}]. "
                    f"Expected: longitude -180 to 180, latitude -90 to 90. "
                    f"\n\nYour coordinates appear to be in a projected coordinate system (like UTM), not WGS84. "
                    f"GeoJSON files should use WGS84 (EPSG:4326) coordinates. "
                    f"Please convert your file to WGS84 before uploading using tools like QGIS, ogr2ogr, or Python (with pyproj)."
                )
        else:
            raise ValueError(
                f"Coordinates are out of WGS84 range. "
                f"Bounds: longitude [{min_lon:.6f}, {max_lon:.6f}], latitude [{min_lat:.6f}, {max_lat:.6f}]. "
                f"Expected: longitude -180 to 180, latitude -90 to 90. "
                f"\n\nYour coordinates appear to be in a projected coordinate system (like UTM), not WGS84. "
                f"To enable automatic transformation, install pyproj: pip install pyproj. "
                f"Alternatively, convert your file to WGS84 before uploading using tools like QGIS or ogr2ogr."
            )
    
    # Convert GeoJSON to Shapely geometry
    shapely_geom = shape(geojson_geom)
    
    # Ensure valid geometry
    if not shapely_geom.is_valid:
        shapely_geom = shapely_geom.buffer(0)  # Fix invalid geometries
    
    # Double-check bounds after conversion
    bounds = shapely_geom.bounds
    if bounds:
        minx, miny, maxx, maxy = bounds
        if not (-180 <= minx <= 180 and -180 <= maxx <= 180 and
                -90 <= miny <= 90 and -90 <= maxy <= 90):
            raise ValueError(
                f"Coordinates are out of WGS84 range. Bounds: ({minx:.6f}, {miny:.6f}, {maxx:.6f}, {maxy:.6f}). "
                f"Expected longitude: -180 to 180, latitude: -90 to 90. "
                f"Please ensure your GeoJSON file uses WGS84 (EPSG:4326) coordinates."
            )
    
    # Convert Shapely geometry to GeoAlchemy2 WKBElement
    return from_shape(shapely_geom, srid=srid)


def wkb_element_to_geojson(wkb_element):
    """
    Convert GeoAlchemy2 WKBElement to GeoJSON geometry dict
    
    Args:
        wkb_element: WKBElement from GeoAlchemy2
    
    Returns:
        GeoJSON geometry dict
    """
    if wkb_element is None:
        return None
    
    from geoalchemy2.shape import to_shape
    shapely_geom = to_shape(wkb_element)
    return mapping(shapely_geom)


def wkt_to_wkb_element(wkt_string, srid=4326):
    """
    Convert WKT string to GeoAlchemy2 WKBElement
    
    Args:
        wkt_string: Well-Known Text string
        srid: Spatial reference system identifier
    
    Returns:
        WKBElement for GeoAlchemy2
    """
    shapely_geom = wkt.loads(wkt_string)
    return from_shape(shapely_geom, srid=srid)

