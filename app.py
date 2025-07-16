import streamlit as st
import tempfile
import os
import numpy as np
import rasterio
from rasterio.transform import from_origin
import richdem as rd
import matplotlib.pyplot as plt
from skimage import measure
from scipy.ndimage import label

st.set_page_config(layout="wide")
st.title("DEM Hydro-Preprocessing with RichDEM")

# Upload DEM
uploaded_file = st.file_uploader("Upload a UTM-projected DEM (.tif)", type=["tif"])

if uploaded_file is not None:
    # Save DEM to a temporary file
    temp_dir = tempfile.mkdtemp()
    dem_path = os.path.join(temp_dir, uploaded_file.name)
    with open(dem_path, "wb") as f:
        f.write(uploaded_file.read())

    # Load DEM using RichDEM
    dem = rd.LoadGDAL(dem_path)

    st.success("DEM loaded successfully!")

    # Step 1: Fill Sinks
    filled_dem = rd.FillDepressions(dem, in_place=False)
    st.success("Step 1: Sinks filled")

    # Step 2: Flow Direction
    flow_dir = rd.FlowDirectionD8(filled_dem)
    st.success("Step 2: Flow direction computed (D8)")

    # Step 3: Flow Accumulation
    flow_acc = rd.FlowAccumulation(flow_dir, method='D8')
    st.success("Step 3: Flow accumulation computed")

    # Step 4: Stream Network Extraction
    threshold = st.slider("Stream threshold (accumulated cells)", 50, 10000, 1000)
    stream_network = (flow_acc > threshold).astype(np.uint8)
    st.success("Step 4: Stream network extracted")

    # Step 5: Watershed Delineation (basic labeling)
    labeled_array, num_features = label(stream_network)
    st.success("Step 5: Watersheds labeled (simple connected component method)")

    # Visualization
    st.subheader("🗺️ Visualizations")
    layer = st.selectbox("Choose layer to view", ["Filled DEM", "Flow Direction", "Flow Accumulation", "Stream Network", "Watersheds"])

    plt.figure(figsize=(8, 6))
    if layer == "Filled DEM":
        plt.imshow(filled_dem, cmap='terrain')
        plt.title("Filled DEM")
    elif layer == "Flow Direction":
        plt.imshow(flow_dir, cmap='plasma')
        plt.title("Flow Direction (D8)")
    elif layer == "Flow Accumulation":
        log_acc = np.log1p(flow_acc)
        plt.imshow(log_acc, cmap='cubehelix')
        plt.title("Log Flow Accumulation")
    elif layer == "Stream Network":
        plt.imshow(stream_network, cmap='Blues')
        plt.title("Stream Network")
    elif layer == "Watersheds":
        plt.imshow(labeled_array, cmap='tab20')
        plt.title("Watersheds (Labeled)")
    plt.colorbar()
    st.pyplot(plt.gcf())

    # Save outputs and allow download
    def save_raster(array, ref_path, out_name):
        with rasterio.open(ref_path) as src:
            profile = src.profile.copy()
            profile.update(dtype=rasterio.float32, count=1)
            out_path = os.path.join(temp_dir, out_name)
            with rasterio.open(out_path, 'w', **profile) as dst:
                dst.write(array.astype(np.float32), 1)
        return out_path

    filled_path = save_raster(filled_dem, dem_path, 'filled_dem.tif')
    acc_path = save_raster(flow_acc, dem_path, 'flow_acc.tif')
    stream_path = save_raster(stream_network, dem_path, 'streams.tif')
    watershed_path = save_raster(labeled_array, dem_path, 'watersheds.tif')

    st.subheader("📥 Download Results")
    st.download_button("Download Filled DEM", open(filled_path, 'rb').read(), file_name='filled_dem.tif')
    st.download_button("Download Flow Accumulation", open(acc_path, 'rb').read(), file_name='flow_acc.tif')
    st.download_button("Download Stream Network", open(stream_path, 'rb').read(), file_name='streams.tif')
    st.download_button("Download Watersheds", open(watershed_path, 'rb').read(), file_name='watersheds.tif')

else:
    st.info("Upload a DEM to begin hydrological preprocessing using RichDEM.")
