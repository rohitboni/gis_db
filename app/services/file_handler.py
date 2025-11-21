import os
import json
import boto3
from typing import Dict, Any, Optional
from fastapi import UploadFile
import geopandas as gpd
from shapely.geometry import shape, mapping
from io import BytesIO
import tempfile


class FileHandler:
    def __init__(self, s3_bucket: Optional[str] = None, aws_region: str = "us-east-1"):
        self.s3_bucket = s3_bucket
        self.aws_region = aws_region
        self.s3_client = None
        
        if s3_bucket:
            self.s3_client = boto3.client('s3', region_name=aws_region)
    
    async def upload_to_s3(self, file: UploadFile, key: str) -> str:
        """Upload file to S3 and return the S3 path"""
        if not self.s3_client:
            raise ValueError("S3 client not initialized. Set S3_BUCKET_NAME in environment.")
        
        file_content = await file.read()
        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=key,
            Body=file_content,
            ContentType=file.content_type
        )
        
        return f"s3://{self.s3_bucket}/{key}"
    
    async def process_geojson(self, file: UploadFile) -> Dict[str, Any]:
        """Process GeoJSON file and extract geometries and properties"""
        content = await file.read()
        geojson_data = json.loads(content)
        
        if geojson_data.get("type") == "FeatureCollection":
            features = geojson_data.get("features", [])
        elif geojson_data.get("type") == "Feature":
            features = [geojson_data]
        else:
            raise ValueError("Invalid GeoJSON format")
        
        geometries = []
        properties_list = []
        
        for feature in features:
            geom = feature.get("geometry")
            props = feature.get("properties", {})
            
            if geom:
                geometries.append(shape(geom))
                properties_list.append(props)
        
        # Calculate bounding box
        if geometries:
            gdf = gpd.GeoDataFrame(geometry=geometries, crs="EPSG:4326")
            bbox = list(gdf.total_bounds)  # [minx, miny, maxx, maxy]
            
            # For multi-geometry, we'll store the first geometry or create a collection
            # In production, you might want to store each feature separately
            first_geometry = geometries[0] if geometries else None
            
            return {
                "geometry": mapping(first_geometry) if first_geometry else None,
                "properties": properties_list[0] if properties_list else {},
                "bbox": bbox,
                "feature_count": len(features)
            }
        
        return {
            "geometry": None,
            "properties": {},
            "bbox": None,
            "feature_count": 0
        }
    
    async def process_shapefile(self, file: UploadFile, additional_files: Dict[str, UploadFile]) -> Dict[str, Any]:
        """Process Shapefile (requires .shp, .shx, .dbf, and optionally .prj files)"""
        # Create temporary directory for shapefile components
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save main .shp file
            shp_path = os.path.join(tmpdir, file.filename)
            content = await file.read()
            with open(shp_path, "wb") as f:
                f.write(content)
            await file.seek(0)  # Reset file pointer
            
            # Save additional files (.shx, .dbf, .prj)
            for ext, upload_file in additional_files.items():
                file_path = os.path.join(tmpdir, upload_file.filename)
                content = await upload_file.read()
                with open(file_path, "wb") as f:
                    f.write(content)
                await upload_file.seek(0)  # Reset file pointer
            
            # Read shapefile with geopandas
            gdf = gpd.read_file(shp_path)
            
            # Convert to WGS84 if needed
            if gdf.crs and gdf.crs != "EPSG:4326":
                gdf = gdf.to_crs("EPSG:4326")
            
            # Get first geometry (or create collection)
            first_geom = gdf.geometry.iloc[0] if len(gdf) > 0 else None
            
            # Get properties from first row
            properties = gdf.iloc[0].drop('geometry').to_dict() if len(gdf) > 0 else {}
            
            # Calculate bounding box
            bbox = list(gdf.total_bounds) if len(gdf) > 0 else None
            
            return {
                "geometry": mapping(first_geom) if first_geom else None,
                "properties": properties,
                "bbox": bbox,
                "feature_count": len(gdf)
            }
    
    async def process_kml(self, file: UploadFile) -> Dict[str, Any]:
        """Process KML file"""
        content = await file.read()
        
        # Use fiona to read KML
        with tempfile.NamedTemporaryFile(suffix=".kml", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            gdf = gpd.read_file(tmp_path, driver='KML')
            
            if gdf.crs and gdf.crs != "EPSG:4326":
                gdf = gdf.to_crs("EPSG:4326")
            
            first_geom = gdf.geometry.iloc[0] if len(gdf) > 0 else None
            properties = gdf.iloc[0].drop('geometry').to_dict() if len(gdf) > 0 else {}
            bbox = list(gdf.total_bounds) if len(gdf) > 0 else None
            
            return {
                "geometry": mapping(first_geom) if first_geom else None,
                "properties": properties,
                "bbox": bbox,
                "feature_count": len(gdf)
            }
        finally:
            os.unlink(tmp_path)

