import json
import zipfile
import tempfile
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
import geopandas as gpd
from shapely.geometry import mapping, shape
from fastkml import kml, styles
import gpxpy
import gpxpy.gpx
import pandas as pd
from io import BytesIO
import geojson

from app.utils.geometry import geojson_to_wkb_element


class FileParser:
    """Parser for various geographic file formats"""
    
    SUPPORTED_EXTENSIONS = {
        '.geojson': 'geojson',
        '.json': 'json',
        '.kml': 'kml',
        '.kmz': 'kmz',
        '.shp': 'shapefile',
        '.gpx': 'gpx',
        '.csv': 'csv'
    }
    
    @staticmethod
    def detect_file_type(filename: str) -> str:
        """Detect file type from extension"""
        ext = Path(filename).suffix.lower()
        return FileParser.SUPPORTED_EXTENSIONS.get(ext, 'unknown')
    
    @staticmethod
    def parse_geojson(file_content: bytes, filename: str) -> List[Dict[str, Any]]:
        """Parse GeoJSON file"""
        try:
            data = json.loads(file_content.decode('utf-8'))
            
            features_list = []
            
            # Handle FeatureCollection
            if data.get('type') == 'FeatureCollection':
                features = data.get('features', [])
                for idx, feature in enumerate(features):
                    geom = feature.get('geometry')
                    props = feature.get('properties', {})
                    
                    features_list.append({
                        'name': props.get('name', f"{Path(filename).stem}_{idx}"),
                        'geometry': geom,
                        'properties': props
                    })
            
            # Handle single Feature
            elif data.get('type') == 'Feature':
                geom = data.get('geometry')
                props = data.get('properties', {})
                
                features_list.append({
                    'name': props.get('name', Path(filename).stem),
                    'geometry': geom,
                    'properties': props
                })
            
            # Handle bare geometry
            elif data.get('type') in ['Point', 'LineString', 'Polygon', 'MultiPoint', 'MultiLineString', 'MultiPolygon']:
                features_list.append({
                    'name': Path(filename).stem,
                    'geometry': data,
                    'properties': {}
                })
            
            return features_list
            
        except Exception as e:
            raise ValueError(f"Error parsing GeoJSON: {str(e)}")
    
    @staticmethod
    def parse_shapefile(file_content: bytes, filename: str) -> List[Dict[str, Any]]:
        """Parse Shapefile (requires .shp, .shx, .dbf files)"""
        # Shapefile parsing requires multiple files
        # This assumes the user uploads a zip containing all required files
        raise ValueError("Shapefile upload must be a ZIP file containing .shp, .shx, .dbf, and optionally .prj files")
    
    @staticmethod
    def parse_shapefile_zip(file_content: bytes, filename: str) -> List[Dict[str, Any]]:
        """Parse Shapefile from ZIP archive"""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, 'shapefile.zip')
                with open(zip_path, 'wb') as f:
                    f.write(file_content)
                
                # Extract zip
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)
                
                # Find .shp file
                shp_files = list(Path(tmpdir).glob('*.shp'))
                if not shp_files:
                    raise ValueError("No .shp file found in ZIP archive")
                
                shp_file = shp_files[0]
                
                # Read with geopandas
                gdf = gpd.read_file(str(shp_file))
                
                features_list = []
                for idx, row in gdf.iterrows():
                    geom_dict = mapping(row.geometry) if hasattr(row.geometry, '__geo_interface__') else json.loads(gpd.GeoSeries([row.geometry]).to_json())
                    
                    # Extract properties (all columns except geometry)
                    props = {col: row[col] for col in gdf.columns if col != 'geometry'}
                    # Convert non-serializable types
                    for key, value in props.items():
                        if pd.isna(value):
                            props[key] = None
                        elif isinstance(value, (pd.Timestamp,)):
                            props[key] = value.isoformat()
                        elif not isinstance(value, (str, int, float, bool, type(None))):
                            props[key] = str(value)
                    
                    features_list.append({
                        'name': props.get('name', f"{Path(filename).stem}_{idx}"),
                        'geometry': geom_dict['features'][0]['geometry'] if 'features' in geom_dict else geom_dict,
                        'properties': props
                    })
                
                return features_list
                
        except Exception as e:
            raise ValueError(f"Error parsing Shapefile: {str(e)}")
    
    @staticmethod
    def parse_kml(file_content: bytes, filename: str) -> List[Dict[str, Any]]:
        """Parse KML file"""
        try:
            k = kml.KML()
            k.from_string(file_content.decode('utf-8'))
            
            features_list = []
            feature_idx = 0
            
            def extract_features(element, parent_name=""):
                nonlocal feature_idx
                features = []
                
                if hasattr(element, 'features'):
                    for feature in element.features():
                        if hasattr(feature, 'geometry') and feature.geometry:
                            geom_dict = mapping(feature.geometry)
                            props = {'name': getattr(feature, 'name', None) or f"{Path(filename).stem}_{feature_idx}"}
                            
                            features.append({
                                'name': props['name'],
                                'geometry': geom_dict,
                                'properties': props
                            })
                            feature_idx += 1
                        
                        # Recursively extract from nested features
                        if hasattr(feature, 'features'):
                            features.extend(extract_features(feature, getattr(feature, 'name', '')))
                
                return features
            
            features_list = extract_features(k)
            
            if not features_list:
                raise ValueError("No geometries found in KML file")
            
            return features_list
            
        except Exception as e:
            raise ValueError(f"Error parsing KML: {str(e)}")
    
    @staticmethod
    def parse_kmz(file_content: bytes, filename: str) -> List[Dict[str, Any]]:
        """Parse KMZ file (ZIP containing KML)"""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, 'kmz.zip')
                with open(zip_path, 'wb') as f:
                    f.write(file_content)
                
                # Extract zip
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)
                
                # Find .kml file
                kml_files = list(Path(tmpdir).glob('*.kml'))
                if not kml_files:
                    raise ValueError("No .kml file found in KMZ archive")
                
                kml_file = kml_files[0]
                with open(kml_file, 'rb') as f:
                    kml_content = f.read()
                
                return FileParser.parse_kml(kml_content, filename)
                
        except Exception as e:
            raise ValueError(f"Error parsing KMZ: {str(e)}")
    
    @staticmethod
    def parse_gpx(file_content: bytes, filename: str) -> List[Dict[str, Any]]:
        """Parse GPX file"""
        try:
            gpx = gpxpy.parse(file_content.decode('utf-8'))
            
            features_list = []
            
            # Extract waypoints
            for idx, waypoint in enumerate(gpx.waypoints):
                geom_dict = {
                    "type": "Point",
                    "coordinates": [waypoint.longitude, waypoint.latitude]
                }
                props = {
                    'name': waypoint.name or f"{Path(filename).stem}_waypoint_{idx}",
                    'elevation': waypoint.elevation,
                    'time': waypoint.time.isoformat() if waypoint.time else None,
                    'description': waypoint.description
                }
                
                features_list.append({
                    'name': props['name'],
                    'geometry': geom_dict,
                    'properties': {k: v for k, v in props.items() if v is not None}
                })
            
            # Extract tracks
            for track_idx, track in enumerate(gpx.tracks):
                for segment_idx, segment in enumerate(track.segments):
                    coords = [[point.longitude, point.latitude] for point in segment.points]
                    
                    geom_dict = {
                        "type": "LineString",
                        "coordinates": coords
                    }
                    
                    props = {
                        'name': track.name or f"{Path(filename).stem}_track_{track_idx}_segment_{segment_idx}",
                        'track_name': track.name,
                        'segment_index': segment_idx
                    }
                    
                    features_list.append({
                        'name': props['name'],
                        'geometry': geom_dict,
                        'properties': props
                    })
            
            # Extract routes
            for route_idx, route in enumerate(gpx.routes):
                coords = [[point.longitude, point.latitude] for point in route.points]
                
                geom_dict = {
                    "type": "LineString",
                    "coordinates": coords
                }
                
                props = {
                    'name': route.name or f"{Path(filename).stem}_route_{route_idx}",
                    'route_name': route.name,
                    'description': route.description
                }
                
                features_list.append({
                    'name': props['name'],
                    'geometry': geom_dict,
                    'properties': {k: v for k, v in props.items() if v is not None}
                })
            
            if not features_list:
                raise ValueError("No features found in GPX file")
            
            return features_list
            
        except Exception as e:
            raise ValueError(f"Error parsing GPX: {str(e)}")
    
    @staticmethod
    def parse_csv(file_content: bytes, filename: str) -> List[Dict[str, Any]]:
        """Parse CSV file with lat/lon or WKT"""
        try:
            df = pd.read_csv(BytesIO(file_content))
            
            features_list = []
            
            # Check for WKT column
            wkt_columns = [col for col in df.columns if col.lower() in ['wkt', 'geometry', 'geom']]
            
            if wkt_columns:
                # Parse WKT
                from shapely import wkt as shapely_wkt
                wkt_col = wkt_columns[0]
                
                for idx, row in df.iterrows():
                    try:
                        geom = shapely_wkt.loads(str(row[wkt_col]))
                        geom_dict = mapping(geom)
                    except:
                        continue
                    
                    props = {col: row[col] for col in df.columns if col != wkt_col}
                    # Clean props
                    for key, value in props.items():
                        if pd.isna(value):
                            props[key] = None
                        elif not isinstance(value, (str, int, float, bool, type(None))):
                            props[key] = str(value)
                    
                    features_list.append({
                        'name': props.get('name', f"{Path(filename).stem}_{idx}"),
                        'geometry': geom_dict,
                        'properties': props
                    })
            
            # Check for lat/lon columns
            else:
                lat_cols = [col for col in df.columns if col.lower() in ['lat', 'latitude', 'y', 'ycoord']]
                lon_cols = [col for col in df.columns if col.lower() in ['lon', 'longitude', 'lng', 'x', 'xcoord']]
                
                if lat_cols and lon_cols:
                    lat_col = lat_cols[0]
                    lon_col = lon_cols[0]
                    
                    for idx, row in df.iterrows():
                        if pd.isna(row[lat_col]) or pd.isna(row[lon_col]):
                            continue
                        
                        geom_dict = {
                            "type": "Point",
                            "coordinates": [float(row[lon_col]), float(row[lat_col])]
                        }
                        
                        props = {col: row[col] for col in df.columns if col not in [lat_col, lon_col]}
                        # Clean props
                        for key, value in props.items():
                            if pd.isna(value):
                                props[key] = None
                            elif not isinstance(value, (str, int, float, bool, type(None))):
                                props[key] = str(value)
                        
                        features_list.append({
                            'name': props.get('name', f"{Path(filename).stem}_{idx}"),
                            'geometry': geom_dict,
                            'properties': props
                        })
                else:
                    raise ValueError("CSV must contain either WKT column or lat/lon columns")
            
            if not features_list:
                raise ValueError("No valid geometries found in CSV")
            
            return features_list
            
        except Exception as e:
            raise ValueError(f"Error parsing CSV: {str(e)}")
    
    @staticmethod
    def parse_file(file_content: bytes, filename: str) -> List[Dict[str, Any]]:
        """Main parser method that routes to appropriate parser"""
        file_type = FileParser.detect_file_type(filename)
        
        # Handle ZIP files (could be shapefile or KMZ)
        if filename.lower().endswith('.zip'):
            # Try to detect by contents
            try:
                with zipfile.ZipFile(BytesIO(file_content)) as zip_file:
                    file_list = zip_file.namelist()
                    if any(f.endswith('.shp') for f in file_list):
                        return FileParser.parse_shapefile_zip(file_content, filename)
                    elif any(f.endswith('.kml') for f in file_list):
                        return FileParser.parse_kmz(file_content, filename)
            except:
                pass
        
        # Route to appropriate parser
        parsers = {
            'geojson': FileParser.parse_geojson,
            'json': FileParser.parse_geojson,  # JSON files treated as GeoJSON
            'kml': FileParser.parse_kml,
            'kmz': FileParser.parse_kmz,
            'shapefile': FileParser.parse_shapefile,
            'gpx': FileParser.parse_gpx,
            'csv': FileParser.parse_csv
        }
        
        if file_type not in parsers:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        return parsers[file_type](file_content, filename)

