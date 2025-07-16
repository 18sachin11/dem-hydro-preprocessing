import streamlit as st
import os
import tempfile
import shutil
import numpy as np
import rasterio
from whitebox.whitebox_tools import WhiteboxTools
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("DEM Hydro-Preprocessing with WhiteboxTools (Streamlit Cloud Compatible)")

# Set up WhiteboxTools
wbt = WhiteboxTools()
wbt.set_whitebox_dir(os.getcwd())  # Ensure whitebox_tools binary is in project root

# Upload DEM
uploaded_file = st.file_uploader("Upload a UTM-projected DEM (.tif)", type=["tif"])

if uploaded_file is not None:
    temp_dir = tempfile.mkdtemp()
    dem_path = os.path.join(temp_dir, uploaded_file.name)
    with open(dem_path, 'wb') as f:
        f.write(uploaded_file.read())

    # Paths for output files
    filled_dem = os.path.join(temp_dir, "filled_dem.tif")
    flow_dir = os.path.join(temp_dir, "flow_dir.tif")
    flow_acc = os.path.join(temp_dir, "flow_acc.tif")
    stream_raster = os.path.join(temp_dir, "streams.tif")
    watershed = os.path.join(temp_dir, "watershed.tif")

    # Step 1: Fill Depressions
    wbt.fill_depressions(dem_path, filled_dem)
    st.success("Step 1: Depressions filled")

    # Step 2: Flow Direction
    wbt.d8_pointer(filled_dem, flow_dir)
    st.success("Step 2: Flow direction computed")

    # Step 3: Flow Accumulation
    wbt.d8_flow_accumulation(filled_dem, flow_acc, out_type='cells')
    st.success("Step 3: Flow accumulation computed")

    # Step 4: Extract Stream Network
    threshold = st.slider("Stream threshold (cells)", 100, 10000, 1000)
    wbt.extract_streams(flow_acc, stream_raster, threshold)
    st.success("Step 4: Stream network extracted")

    # Step 5: Watershed Delineation
    wbt.watershed(flow_dir, stream_raster, watershed)
    st.success("Step 5: Watersheds delineated")

    # Visualization
    st.subheader("🗺️ Visualize Output Layers")
    layer = st.selectbox("Select layer to visualize", ["Filled DEM", "Flow Accumulation", "Streams", "Watershed"])

    def show_raster(path, title, log=False):
        with rasterio.open(path) as src:
            data = src.read(1)
            if log:
                data = np.log1p(data)
            plt.imshow(data, cmap='terrain')
            plt.title(title)
            plt.colorbar()
            st.pyplot(plt.gcf())
            plt.clf()

    if layer == "Filled DEM":
        show_raster(filled_dem, "Filled DEM")
    elif layer == "Flow Accumulation":
        show_raster(flow_acc, "Flow Accumulation (log scale)", log=True)
    elif layer == "Streams":
        show_raster(stream_raster, "Stream Network")
    elif layer == "Watershed":
        show_raster(watershed, "Watersheds")

    # Download section
    st.subheader("📥 Download Outputs")
    for fpath in [filled_dem, flow_acc, stream_raster, watershed]:
        st.download_button(
            label=f"Download {os.path.basename(fpath)}",
            data=open(fpath, 'rb').read(),
            file_name=os.path.basename(fpath),
            mime="application/octet-stream"
        )
else:
    st.info("Please upload a DEM file in GeoTIFF format to begin.")
