#this script shall merge the raster files into a single raster using rasterio library

import os
import rasterio
from rasterio.merge import merge
from typing import List, Optional

# merege the raster file given a list of directory paths of raster files
def merge_raster(raster_paths: List[str], output_path: Optional[str]=None) -> None:
    """Merge the raster files into a single raster file"""
    # open the raster files
    raster_files = [rasterio.open(path) for path in raster_paths]
    # merge the raster files
    raster_merged, raster_transform = merge(raster_files)
    # get the metadata of the raster file
    raster_meta = raster_files[0].meta.copy()
    # update the metadata
    raster_meta.update({"driver": "GTiff",
                        "height": raster_merged.shape[1],
                        "width": raster_merged.shape[2],
                        "transform": raster_transform})

    # if the output path is not given, save the raster file in the same directory as the first raster file
    if output_path is None:
        output_path = os.path.join(os.path.dirname(raster_paths[0]), "raster_merged.tif")
        
    # write the raster file
    with rasterio.open(output_path, "w", **raster_meta) as dst:
        dst.write(raster_merged)
    return None