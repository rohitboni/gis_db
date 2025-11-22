"""
File format converter service for converting between different GIS file formats.
Supports conversion between GeoJSON, Shapefile, KML, GPX, and CSV formats.
"""
import json
import zipfile
import tempfile
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from io import BytesIO
import geopandas as gpd
from shapely.geometry import mapping, shape
from fastkml import kml, styles
import gpxpy
import gpxpy.gpx
import pandas as pd
from geoalchemy2.shape import to_shape


class FileConverter:
    """Converter for various geographic file formats"""
    
    SUPPORTED_OUTPUT_FORMATS = {
        'geojson': 'geojson',
        'json': 'geojson',  # JSON is treated as GeoJSON
        'shp': 'shapefile',
        'shapefile': 'shapefile',
        'zip': 'shapefile',  # Shapefile output is always ZIP
        'kml': 'kml',
        'kmz': 'kmz',
        'gpx': 'gpx',
        'csv': 'csv'
    }
    
    @staticmethod
    def features_to_geopandas(features: List[Dict[str, Any]]) -> gpd.GeoDataFrame:
        """
        Convert a list of features (from database) to a GeoPandas GeoDataFrame.
        
        Args:
            features: List of Feature objects from database
            
        Returns:
            GeoDataFrame with all features and their properties
        """
        from shapely import wkt
        
        geometries = []
        properties_list = []
        
        for feature in features:
            # Convert PostGIS geometry to Shapely geometry
            if hasattr(feature.geometry, '__geo_interface__'):
                geom = shape(feature.geometry.__geo_interface__)
            else:
                # Convert using geoalchemy2
                geom = to_shape(feature.geometry)
            
            geometries.append(geom)
            
            # Collect properties
            props = feature.properties.copy() if feature.properties else {}
            props['name'] = feature.name  # Ensure name is included
            properties_list.append(props)
        
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame(properties_list, geometry=geometries, crs='EPSG:4326')
        
        return gdf
    
    @staticmethod
    def convert_to_geojson(gdf: gpd.GeoDataFrame) -> bytes:
        """Convert GeoDataFrame to GeoJSON format"""
        # Convert to GeoJSON
        geojson_str = gdf.to_json()
        return geojson_str.encode('utf-8')
    
    @staticmethod
    def convert_to_shapefile(gdf: gpd.GeoDataFrame) -> bytes:
        """Convert GeoDataFrame to Shapefile (ZIP format)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            shp_path = os.path.join(tmpdir, 'output.shp')
            
            # Save as shapefile
            gdf.to_file(shp_path, driver='ESRI Shapefile')
            
            # Create ZIP archive with all shapefile components
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file in Path(tmpdir).glob('*'):
                    if file.is_file():
                        zip_file.write(file, file.name)
            
            zip_buffer.seek(0)
            return zip_buffer.read()
    
    @staticmethod
    def convert_to_kml(gdf: gpd.GeoDataFrame, filename: str = "output") -> bytes:
        """Convert GeoDataFrame to KML format"""
        try:
            k = kml.KML()
            ns = '{http://www.opengis.net/kml/2.2}'
            doc = kml.Document(ns, 'docid', filename, filename)
            
            for idx, row in gdf.iterrows():
                # Create placemark for each feature
                feature_name = str(row.get('name', f"Feature_{idx}"))
                placemark = kml.Placemark(
                    ns,
                    f"placemark_{idx}",
                    feature_name,
                    feature_name
                )
                
                # Set geometry
                if row.geometry is not None and not row.geometry.is_empty:
                    placemark.geometry = row.geometry
                
                doc.append(placemark)
            
            k.append(doc)
            return k.to_string(prettyprint=True).encode('utf-8')
        except Exception as e:
            # Fallback: Use geopandas to_kml if available, otherwise use simple conversion
            try:
                # Try using geopandas built-in KML export
                with tempfile.NamedTemporaryFile(mode='w', suffix='.kml', delete=False) as tmp:
                    gdf.to_file(tmp.name, driver='KML')
                    with open(tmp.name, 'rb') as f:
                        content = f.read()
                    os.unlink(tmp.name)
                    return content
            except:
                # Last resort: convert to GeoJSON and wrap in minimal KML
                geojson_str = gdf.to_json()
                kml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{filename}</name>
    <Placemark>
      <name>Features</name>
      <ExtendedData>
        <Data name="geojson">
          <value><![CDATA[{geojson_str}]]></value>
        </Data>
      </ExtendedData>
    </Placemark>
  </Document>
</kml>'''
                return kml_content.encode('utf-8')
    
    @staticmethod
    def convert_to_kmz(gdf: gpd.GeoDataFrame, filename: str = "output") -> bytes:
        """Convert GeoDataFrame to KMZ format (ZIP containing KML)"""
        # First convert to KML
        kml_content = FileConverter.convert_to_kml(gdf, filename)
        
        # Create KMZ (ZIP) file
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('doc.kml', kml_content)
        
        zip_buffer.seek(0)
        return zip_buffer.read()
    
    @staticmethod
    def convert_to_gpx(gdf: gpd.GeoDataFrame, filename: str = "output") -> bytes:
        """Convert GeoDataFrame to GPX format"""
        gpx = gpxpy.gpx.GPX()
        
        for idx, row in gdf.iterrows():
            geom = row.geometry
            
            if geom is None or geom.is_empty:
                continue
            
            # Handle Point geometries
            if geom.geom_type == 'Point':
                waypoint = gpxpy.gpx.GPXWaypoint(
                    latitude=geom.y,
                    longitude=geom.x,
                    name=row.get('name', f"Waypoint_{idx}")
                )
                if 'elevation' in row:
                    waypoint.elevation = float(row['elevation'])
                gpx.waypoints.append(waypoint)
            
            # Handle LineString and MultiLineString geometries
            elif geom.geom_type in ['LineString', 'MultiLineString']:
                track = gpxpy.gpx.GPXTrack()
                track.name = row.get('name', f"Track_{idx}")
                
                segment = gpxpy.gpx.GPXTrackSegment()
                
                if geom.geom_type == 'LineString':
                    coords = list(geom.coords)
                else:  # MultiLineString
                    coords = []
                    for line in geom.geoms:
                        coords.extend(list(line.coords))
                
                for coord in coords:
                    point = gpxpy.gpx.GPXTrackPoint(
                        latitude=coord[1],
                        longitude=coord[0]
                    )
                    if len(coord) > 2:
                        point.elevation = coord[2]
                    segment.points.append(point)
                
                track.segments.append(segment)
                gpx.tracks.append(track)
        
        return gpx.to_xml().encode('utf-8')
    
    @staticmethod
    def convert_to_csv(gdf: gpd.GeoDataFrame) -> bytes:
        """Convert GeoDataFrame to CSV format with WKT geometry"""
        # Create a copy to avoid modifying original
        gdf_copy = gdf.copy()
        
        # Convert geometry to WKT
        gdf_copy['geometry'] = gdf_copy['geometry'].apply(lambda x: x.wkt if x is not None and not x.is_empty else None)
        
        # Convert to CSV
        csv_buffer = BytesIO()
        gdf_copy.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        return csv_buffer.read()
    
    @staticmethod
    def convert_features(
        features: List[Any],
        output_format: str,
        filename: str = "output"
    ) -> Tuple[bytes, str, str]:
        """
        Convert a list of database features to the specified output format.
        
        Args:
            features: List of Feature objects from database
            output_format: Desired output format (geojson, shapefile, kml, kmz, gpx, csv)
            filename: Base filename for output
            
        Returns:
            Tuple of (file_content_bytes, mime_type, file_extension)
        """
        if not features:
            raise ValueError("No features provided for conversion")
        
        # Normalize output format
        output_format = output_format.lower().strip('.')
        if output_format not in FileConverter.SUPPORTED_OUTPUT_FORMATS:
            raise ValueError(f"Unsupported output format: {output_format}. Supported: {', '.join(FileConverter.SUPPORTED_OUTPUT_FORMATS.keys())}")
        
        # Convert to GeoDataFrame
        gdf = FileConverter.features_to_geopandas(features)
        
        # Convert to requested format
        format_map = {
            'geojson': (FileConverter.convert_to_geojson, 'application/geo+json', '.geojson'),
            'json': (FileConverter.convert_to_geojson, 'application/json', '.json'),
            'shapefile': (FileConverter.convert_to_shapefile, 'application/zip', '.zip'),
            'shp': (FileConverter.convert_to_shapefile, 'application/zip', '.zip'),
            'zip': (FileConverter.convert_to_shapefile, 'application/zip', '.zip'),
            'kml': (lambda gdf, f=filename: FileConverter.convert_to_kml(gdf, f), 'application/vnd.google-earth.kml+xml', '.kml'),
            'kmz': (lambda gdf, f=filename: FileConverter.convert_to_kmz(gdf, f), 'application/vnd.google-earth.kmz', '.kmz'),
            'gpx': (lambda gdf, f=filename: FileConverter.convert_to_gpx(gdf, f), 'application/gpx+xml', '.gpx'),
            'csv': (FileConverter.convert_to_csv, 'text/csv', '.csv')
        }
        
        converter_func, mime_type, extension = format_map[output_format]
        file_content = converter_func(gdf)
        
        return file_content, mime_type, extension
    
    @staticmethod
    def merge_multiple_files(
        file_features_list: List[Tuple[str, List[Any]]],
        output_format: str
    ) -> Tuple[bytes, str, str]:
        """
        Merge multiple files' features into a single output file.
        
        Args:
            file_features_list: List of tuples (filename, [features])
            output_format: Desired output format
            
        Returns:
            Tuple of (file_content_bytes, mime_type, file_extension)
        """
        all_features = []
        
        # Collect all features from all files
        for filename, features in file_features_list:
            all_features.extend(features)
        
        if not all_features:
            raise ValueError("No features found in any of the files")
        
        # Use the first filename as base, or create a merged name
        base_filename = file_features_list[0][0] if file_features_list else "merged"
        if len(file_features_list) > 1:
            base_filename = f"merged_{len(file_features_list)}_files"
        
        # Convert all features together
        return FileConverter.convert_features(all_features, output_format, base_filename)

