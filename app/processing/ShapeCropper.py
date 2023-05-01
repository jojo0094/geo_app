#create the folders directory for app
# this app shall extract raster and vector file into a cropped area given a shapefile
# the shapefile is a polygon that will be used to crop the raster and vector file

import os
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path


@dataclass
class GeoData:
    """Class to hold data"""
    # the path to the shapefile with cropping area 
    shapefile_path: str
    # the path to the raster file and this will be optional
    raster_path: Optional[str] = None
    # the path to the vector file
    vector_path: Optional[str] = None
    # the path to the output directory; this shall automatically be created in the currently working directory
    output_path: str = os.path.join(os.getcwd(), "output")

    def __post_init__(self):
        # check if at least one of raster or vector file exists
        if not self.raster_path and not self.vector_path:
            raise ValueError("At least one of raster or vector file should exist.")

        # create output directory if it doesn't exist
        Path(self.output_path).mkdir(parents=True, exist_ok=True)

        # set the path to the output raster file
        if self.raster_path:
            self.output_raster_path: str = os.path.join(self.output_path, "output_raster")
            Path(self.output_raster_path).mkdir(parents=True, exist_ok=True)

        # set the path to the output vector file
        if self.vector_path:
            self.output_vector_path: str = os.path.join(self.output_path, "output_vector")
            Path(self.output_vector_path).mkdir(parents=True, exist_ok=True)


# create abstract class for cropping method depeding on the file type such raster or shapefile

@dataclass
class Cropper(ABC):
    """Abstract class for cropping"""
    geo_data: GeoData 

    @abstractmethod
    def transform_crs(self):
        pass
    
    @abstractmethod
    def crop(self):
        pass

    @abstractmethod
    def execute(self):
        pass

# create a class for cropping raster file
@dataclass
class RasterCropper(Cropper):
    """Class for cropping raster file"""
    geo_data: GeoData

    def __post_init__(self):
        # open the raster file once and keep the handle for later use
        self.raster = rasterio.open(self.geo_data.raster_path)

    def transform_crs(self):
        """Take corrdinate reference system of the shapefile and transform it to that of the raster file"""
        # read the shapefile
        shapefile = gpd.read_file(self.geo_data.shapefile_path)
        # transform the shapefile to the crs of the raster file
        shapefile_transformed = shapefile.to_crs(self.raster.crs)
        return shapefile_transformed

    def crop(self):
        """Crop the raster file using the shapefile"""
        # read the shapefile
        shapefile_transformed = self.transform_crs()
        # crop the raster file
        raster_cropped, raster_transform = mask(dataset=self.raster, shapes=shapefile_transformed.geometry, crop=True)
        return raster_cropped, raster_transform

    def execute(self):
        """Save the cropped raster file"""
        # crop the raster file
        raster_cropped, raster_transform = self.crop()
        # update the metadata
        raster_meta = self.raster.meta.copy()
        raster_meta.update({"driver": "GTiff",
                            "height": raster_cropped.shape[1],
                            "width": raster_cropped.shape[2],
                            "transform": raster_transform})
        # save the raster file
        with rasterio.open(os.path.join(self.geo_data.output_raster_path, "raster_cropped.tif"), "w", **raster_meta) as dst:
            dst.write(raster_cropped)
        return None


# create a class for cropping vector file
@dataclass
class VectorCropper(Cropper):
    """Class for cropping vector file"""
    geo_data: GeoData

    def __post_init__(self):
        # read the shapefile
        self.shapefile = gpd.read_file(self.geo_data.shapefile_path)

    def transform_crs(self):
        """Take corrdinate reference system of the raster file and transform it to that of the shapefile"""
        # transform the shapefile to the crs of the raster file
        shapefile_transformed = self.shapefile.to_crs(self.geo_data.get_crs)
        return shapefile_transformed

    def crop(self):
        """Crop the vector file using the shapefile"""
        # read the shapefile
        shapefile_transformed = self.transform_crs()
        # crop the vector file
        vector_cropped = gpd.overlay(shapefile_transformed, self.geo_data.vector_path, how="intersection")
        return vector_cropped

    def execute(self):
        """Save the cropped vector file"""
        # crop the vector file
        vector_cropped = self.crop()
        # save the vector file
        vector_cropped.to_file(os.path.join(self.geo_data.output_vector_path, "vector_cropped.shp"))
        return None


# create a class for cropping both raster and vector file
@dataclass
class BothCropper(Cropper):
    """Class for cropping both raster and vector file"""
    geo_data: GeoData

    def __post_init__(self):
        # open the raster file once and keep the handle for later use
        self.raster = rasterio.open(self.geo_data.raster_path)
        # read the shapefile
        self.shapefile = gpd.read_file(self.geo_data.shapefile_path)

    def transform_crs(self):
        """Take corrdinate reference system of the shapefile and transform it to that of the raster file"""
        # transform the shapefile to the crs of the raster file
        shapefile_transformed = self.shapefile.to_crs(self.raster.crs)
        return shapefile_transformed

    def crop(self):
        """Crop the raster and vector file using the shapefile"""
        # read the shapefile
        shapefile_transformed = self.transform_crs()
        # crop the raster file
        raster_cropped, raster_transform = mask(dataset=self.raster, shapes=shapefile_transformed.geometry, crop=True)
        # crop the vector file
        vector_cropped = gpd.overlay(shapefile_transformed, self.geo_data.vector_path, how="intersection")
        return raster_cropped, raster_transform, vector_cropped

    def execute(self):
        """Save the cropped raster and vector file"""
        # crop the raster and vector file
        raster_cropped, raster_transform, vector_cropped = self.crop()
        # update the metadata
        raster_meta = self.raster.meta.copy()
        raster_meta.update({"driver": "GTiff",
                            "height": raster_cropped.shape[1],
                            "width": raster_cropped.shape[2],
                            "transform": raster_transform})
        # save the raster file
        with rasterio.open(os.path.join(self.geo_data.output_raster_path, "raster_cropped.tif"), "w", **raster_meta) as dst:
            dst.write(raster_cropped)
        # save the vector file
        vector_cropped.to_file(os.path.join(self.geo_data.output_vector_path, "vector_cropped.shp"))
        return None


# create application class
@dataclass
class Application:
    """Class for the application"""
    geo_data: GeoData
    cropper: Cropper

    def execute(self):
        """Execute the application"""
        self.cropper.execute()
        return None

