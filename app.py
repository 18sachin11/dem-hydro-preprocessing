import streamlit as st
import whitebox
from whitebox.whitebox_tools import WhiteboxTools
import os
import shutil
import tempfile
import folium
from streamlit_folium import st_folium
import rasterio
import numpy as np
from folium.raster_layers import ImageOverlay
from rasterio.plot import reshape_as_image
from matplotlib import cm

st.set_page_config(layout="wide")
st.title("DEM Hydro-Preprocessing Web Tool (WhiteboxTools + Streamlit)")

# Initialize WhiteboxTools
wbt = WhiteboxTools()
temp_dir = tempfile.mkdtemp()
wbt.set_working_dir(temp_dir)

# Sidebar: Upload DEM
st.sidebar.header("Upload your DEM (GeoTIFF, UTM projected)")
dem_file = st.sidebar.file_uploader("DEM (.tif)", type=['tif'])

# Helper: visualize raster on folium map
def visualize_raster(raster_path, map_center):
    with rasterio.open(raster_path) as src:
        bounds = src.bounds
        arr = src.read(1)
        arr = np.ma.masked_where((arr == src.nodata) | np.isnan(arr), arr)
        colormap = cm.viridis
        normed = (arr - arr.min()) / (arr.max() - arr.min())
        rgba = colormap(normed, bytes=True)
        image = reshape_as_image(rgba)

    fmap = folium.Map(location=map_center, zoom_start=10)
    folium.raster_layers.ImageOverlay(
        image=image,
        bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
        opacity=0.7,
        interactive=True,
        cross_origin=False
    ).add_to(fmap)
    return fmap

if dem_file is not None:
    # Save uploaded DEM to temp directory
    dem_path = os.path.join(temp_dir, dem_file.name)
    with open(dem_path, 'wb') as f:
        f.write(dem_file.getbuffer())

    st.success("DEM uploaded successfully!")

    # Fill Depressions
    filled_dem = os.path.join(temp_dir, "filled_dem.tif")
    wbt.fill_depressions(dem_path, filled_dem)
    st.success("Step 1: Sinks filled")

    # Flow Direction (D8 Pointer)
    flow_dir = os.path.join(temp_dir, "flow_dir.tif")
    wbt.d8_pointer(filled_dem, flow_dir)
    st.success("Step 2: Flow direction generated")

    # Flow Accumulation
    flow_acc = os.path.join(temp_dir, "flow_acc.tif")
    wbt.d8_flow_accumulation(filled_dem, flow_acc, out_type='cells')
    st.success("Step 3: Flow accumulation map created")

    # Extract Streams
    stream_raster = os.path.join(temp_dir, "streams.tif")
    threshold = st.sidebar.slider("Stream threshold (accumulated cells)", 100, 10000, 1000)
    wbt.extract_streams(flow_acc, stream_raster, threshold)
    st.success("Step 4: Stream network extracted")

    # Delineate Catchments
    outlet_id = os.path.join(temp_dir, "outlet_id.tif")  # optional, not used here
    catchment = os.path.join(temp_dir, "catchment.tif")
    wbt.watershed(flow_dir, stream_raster, catchment)
    st.success("Step 5: Catchments delineated")

    # Visualization
    st.subheader("🗺️ Map Preview")
    st.write("Select a layer to visualize:")
    selected = st.selectbox("Choose output layer", ["Filled DEM", "Flow Accumulation", "Streams", "Catchments"])

    preview_file = {
        "Filled DEM": filled_dem,
        "Flow Accumulation": flow_acc,
        "Streams": stream_raster,
        "Catchments": catchment
    }[selected]

    try:
        with rasterio.open(preview_file) as src:
            bounds = src.bounds
            center = [(bounds.top + bounds.bottom)/2, (bounds.left + bounds.right)/2]
        fmap = visualize_raster(preview_file, center)
        st_data = st_folium(fmap, width=700, height=500)
    except Exception as e:
        st.warning(f"Could not render map preview: {e}")

    # Download results
    st.markdown("### 🗂️ Download Results")
    for out_file in [filled_dem, flow_dir, flow_acc, stream_raster, catchment]:
        st.download_button(
            label=f"Download {os.path.basename(out_file)}",
            data=open(out_file, "rb").read(),
            file_name=os.path.basename(out_file),
            mime="application/octet-stream"
        )

else:
    st.warning("Please upload a UTM-projected DEM (GeoTIFF format) to begin.")
