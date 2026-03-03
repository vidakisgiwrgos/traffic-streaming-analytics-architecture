import azure.functions as func
import logging
from azure.storage.blob import BlobServiceClient
import subprocess  # For video processing with FFmpeg
import os
import glob
import tempfile
import platform

# Connection string for Blob Storage

# Connection string for local Azurite storage

CONTAINER_NAME = "storagecontainer"
OUTPUT_CONTAINER = "outputcontainer"


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.function_name('Splitter')
@app.route(route="splitter")

def splitter(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("HTTP trigger function received a request.")
    
    # Get Blob name from query parameter
    blob_name = req.params.get('blob_name')
    if not blob_name:
        return func.HttpResponse(
            "Please pass the blob_name in the query string.", status_code=400
        )

    try:
        # Determine OS
        if platform.system().lower().startswith("win"):
            STORAGE_CONNECTION_STRING = os.environ["VideoConnectionString"]
            ffmpeg_executable = "ffmpeg.exe"
        else:
            STORAGE_CONNECTION_STRING = os.environ["VideoConnectionString"]
            ffmpeg_executable = "ffmpeg"
            
        # Initialize Blob Service Client
        blob_service_client = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
        
        # Fetch the video blob
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        blob_client = container_client.get_blob_client(blob_name)
        
        local_file_name = f"{os.path.basename(blob_name)}"
        # Process the video using FFmpeg (splitting into 2-minute segments)
        temp_dir = tempfile.gettempdir()  # Works on Windows, Linux, macOS
        file_path = os.path.join(temp_dir, local_file_name)
        with open(file_path, "wb") as download_file:
            download_file.write(blob_client.download_blob().readall())
        
        output_pattern = f"{temp_dir}/part%d.mp4"
        ffmpeg_path = os.path.join(os.getcwd(), "bin", ffmpeg_executable)
        subprocess.run([
            ffmpeg_path, "-i", file_path, "-c", "copy", "-map", "0", "-segment_time", "120", 
            "-f", "segment", "-reset_timestamps", "1", output_pattern
        ], check=True)

        # Upload the processed files back to Blob Storage
        output_client = blob_service_client.get_container_client(OUTPUT_CONTAINER)
        
        for i, part_file in enumerate(glob.glob(f"{temp_dir}/part*.mp4")):
            with open(part_file, "rb") as file_data:
                output_client.upload_blob(name=f"part{i}.mp4", data=file_data)
            os.remove(part_file)  # Cleanup local files
        
        os.remove(file_path)  # Cleanup original downloaded file
        
        return func.HttpResponse(f"Processing of {blob_name} completed.", status_code=200)
    
    except Exception as e:
        logging.error(f"Error: {e}")
        return func.HttpResponse(f"An error occurred: {str(e)}", status_code=500)
