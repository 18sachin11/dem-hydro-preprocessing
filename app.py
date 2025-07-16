import streamlit as st
import whitebox
from whitebox.whitebox_tools import WhiteboxTools
import os
import shutil
import tempfile

st.set_page_config(layout="wide")
st.title("DEM Hydro-Preprocessing Web Tool (WhiteboxTools + Streamlit)")

# Initialize WhiteboxTools
wbt = WhiteboxTools()
temp_dir = tempfile.mkdtemp()
wbt.set_working_dir(temp_dir)

# Sidebar: Upload DEM
st.sidebar.header("Upload your DEM (GeoTIFF, UTM projected)")
dem_file = st.sidebar.file_uploader("DEM (.tif)", type=['tif'])

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

    # Display download links
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
