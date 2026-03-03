import azure.functions as func
import logging
import pyodbc
import os
import re
import json
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.storage.blob import BlobServiceClient
import cv2
import numpy as np
from ultralytics import YOLO
import time
import tempfile

# Global Tracking vars
SPEED_LIMIT = 130
OUTLIER_THRESHOLD = 200

app = func.FunctionApp()

@app.function_name("Processor")
@app.blob_trigger(arg_name="myblob", path="outputcontainer/{name}",
                               connection="VideoConnectionString")    
def blob_trigger(myblob: func.InputStream):
    data = myblob.read()
    blob_size = len(data)
    logging.info(f"Python blob trigger function processed blob"
                f"Name: {myblob.name}"
                f"Blob Size: {blob_size} bytes")
    
    
    #Dummy data
    logging.info(f"Processing blob: {myblob.name}")

    #Extract camera (through video title)
    camera = int(re.search(r"part(\d+)\.mp4", myblob.name).group(1)) + 1

    # Initialize Blob Service Client
    blob_service_client = BlobServiceClient.from_connection_string(os.environ["VideoConnectionString"])
    
    # Fetch the video blob
    local_file_name = f"{os.path.basename(myblob.name)}"
    container_client = blob_service_client.get_container_client("outputcontainer")
    blob_client = container_client.get_blob_client(local_file_name)
    
    # Process the video using FFmpeg (splitting into 2-minute segments)
    temp_dir = tempfile.gettempdir()  # Works on Windows, Linux, macOS
    file_path = os.path.join(temp_dir, local_file_name)
    with open(file_path, "wb") as download_file:
        download_file.write(blob_client.download_blob().readall())

    # After our CV analysis, we derived the following data:
    tracked_vehicles = tracker(file_path, camera)

    #Cleanup
    os.remove(file_path)

    # Retrieve the connection string from environment variables
    sql_conn_str = os.environ["SqlConnectionString"]
    try:
        
        # Connect to azure db
        conn = pyodbc.connect(sql_conn_str)
        cursor = conn.cursor()

        for track_id, info in tracked_vehicles.items():
            if(info['speed'] != 0 and info['speed'] <= OUTLIER_THRESHOLD): # If valid measurement/tracking
                insert_cmd = """
                INSERT INTO Vehicles(vehicle_id, speed, type, timestamp, stream, camera) 
                VALUES (?, ?, ?, ?, ?, ?)
                """    # Insert the record
                cursor.execute(insert_cmd, (track_id, info['speed'], info['vehicle_type'], info['timestamp'], info['stream'], info['camera']))
            
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logging.info("Record inserted into Azure SQL database successfully.")
    except Exception as e:
        logging.error(f"Error inserting data into SQL database: {e}")
                      
    


        

#Helper Funcs
def send_to_service_bus_queue(data: dict):
    # Convert dictionary to JSON string
    message_payload = json.dumps(data)

    # Create a ServiceBusClient using the connection string
    with ServiceBusClient.from_connection_string(conn_str=os.environ["ServiceBusConnectionString"]) as client:
        # Get a sender for the queue
        with client.get_queue_sender(queue_name= "speedingcarsqueue") as sender:
            # Create a ServiceBusMessage
            message = ServiceBusMessage(message_payload)
            
            # Send message to the queue
            sender.send_messages(message)





def tracker(video_name, camera):

    model = YOLO("yolov8n.pt")

    TARGET_CLASSES = [2, 7]  # COCO indices for car and truck

    # Open video capture
    cap = cv2.VideoCapture(video_name)
    
    # Check if video opened successfully
    if not cap.isOpened():
        print("Error opening video file:", video_name)
        return
    
    # Get the width and height of frames
    frame_width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps          = cap.get(cv2.CAP_PROP_FPS) 

    # If fps is 0 or can’t be read, default to 25
    if fps <= 0:
        fps = 25.0
    
    # --------------------------
    # Set up VideoWriter
    # --------------------------
    #output_path = f"{video_name}_tracked.mp4"

    #fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    #sout = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

    # Define the inbound/outbound regions
    outbound_box  = (0, 0, frame_width // 2, frame_height)           
    inbound_box = (frame_width // 2, 0, frame_width, frame_height)  

    #Area of interest
    roi_top    = int(frame_height * 0.53)
    roi_bottom = int(frame_height * 0.66)
    roi_left   = 0
    roi_right  = frame_width
    roi_box    = (roi_left, roi_top, roi_right, roi_bottom)

    # Real distance of ROI “height”
    REAL_ROI_DISTANCE_M = 20.0  # 20 meters from top to bottom

    tracked_vehicles = {}

    frame_index = 0  # keep track of which frame we are on

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        results = model.track(
            source=frame,      # current frame
            conf=0.4,          # confidence threshold
            classes=TARGET_CLASSES,  # only track car/truck
            persist=True,      # preserve tracking ID across frames
            stream=True        # enables generator mode for real-time use
        )
        

        for res in results:
            # This result has .boxes with .id, .conf, .xyxy, .cls, etc.
            detections = res.boxes
            break  # break after getting first frame's result
        
        # Draw inbound/outbound boxes
        # inbound region in red
        cv2.rectangle(
            frame,
            (inbound_box[0], inbound_box[1]),
            (inbound_box[2], inbound_box[3]),
            (0, 0, 255),
            2
        )
        cv2.putText(
            frame, "Inbound", 
            (inbound_box[0] + 20, inbound_box[1] + 40),
            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2
        )
        
        # outbound region in green
        cv2.rectangle(
            frame,
            (outbound_box[0], outbound_box[1]),
            (outbound_box[2], outbound_box[3]),
            (0, 255, 0),
            2
        )
        cv2.putText(
            frame, "Outbound", 
            (outbound_box[0] + 20, outbound_box[1] + 40),
            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2
        )

        # Draw the ROI rectangle on the frame
        cv2.rectangle(
            frame,
            (roi_left, roi_top),
            (roi_right, roi_bottom),
            (128, 0, 0),
            2
        )

        cv2.putText(
            frame,
            "ROI",
            (roi_left + 20, roi_top - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (128, 0, 0),
            2
        )
        
        # Process detections
        for det in detections:
        
            # Track ID (unique ID assigned by ByteTrack)
            # If this is None, it means the tracker did not assign an ID
            track_id = int(det.id)
            if track_id is None:
                continue

            cls_id = int(det.cls[0])  # class id
            conf   = float(det.conf[0])
            
            # YOLOv8 gives xyxy in 'det.xyxy'
            x1, y1, x2, y2 = det.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

            # Compute center of the bounding box
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            
            # Determine if it's in inbound or outbound region
            if is_inside(cx, cy, inbound_box):
                region_text = "Inbound"
                color = (0, 0, 255)  # red for inbound
            elif is_inside(cx, cy, outbound_box):
                region_text = "Outbound"
                color = (0, 255, 0)  # green for outbound
            else:
                region_text = "Unknown"
                color = (255, 255, 255)  # white
            
            # Label the class name 
            class_name = "Car" if cls_id == 2 else "Truck"
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Put text (class name, confidence, region)
            label = f"{track_id}: {class_name} {conf:.2f} - {region_text}"
            cv2.putText(frame, label, (x1, max(0, y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Optionally, draw the center point
            cv2.circle(frame, (cx, cy), 4, color, -1)

            # RECORD THE DATA
            if track_id not in tracked_vehicles:
                # If we haven't seen this track ID before, store initial info
                tracked_vehicles[track_id] = {
                    "timestamp": round((frame_index / fps)) + (camera - 1) * 120 ,
                    "in_roi": False,
                    "vehicle_type": class_name,
                    "stream": region_text,
                    "latest_conf": conf,
                    "speed": 0,
                    "start_frame": None,
                    "end_frame": None,
                    "camera": camera
                }
            else:
                # If we've seen it, maybe update the confidence if needed
                tracked_vehicles[track_id]["latest_conf"] = conf

            # Check if this detection is in the ROI
            in_roi = is_inside(cx, cy, roi_box)
            vehicle_data = tracked_vehicles[track_id]

             # If the vehicle just ENTERED the ROI (was out, now in)
            if (not vehicle_data["in_roi"]) and in_roi:
                vehicle_data["in_roi"] = True
                vehicle_data["start_frame"] = frame_index
                # We reset end_frame just in case
                vehicle_data["end_frame"] = None

             # If the vehicle just EXITED the ROI (was in, now out)
            if vehicle_data["in_roi"] and (not in_roi):
                vehicle_data["in_roi"] = False
                vehicle_data["end_frame"] = frame_index

                # Calculate speed only if we have start_frame and end_frame, otherwise speed = 0
                if (vehicle_data["start_frame"] is not None and vehicle_data["end_frame"] is not None):
                    frames_taken = vehicle_data["end_frame"] - vehicle_data["start_frame"]
                    if frames_taken > 0:
                        time_taken_s = frames_taken / fps  # in seconds
                        # Speed in m/s
                        speed_m_s = REAL_ROI_DISTANCE_M / time_taken_s
                        # Convert to km/h
                        speed = speed_m_s * 3.6

                        #append speed
                        vehicle_data["speed"] = round(speed)
                        
                        logging.info(
                            f"Vehicle ID {track_id} => "
                            f"Time: {time_taken_s:.2f}s, Speed: {speed:.2f} km/h, Camera: {camera}, Timestamp: {round((frame_index / fps)) + (camera - 1) * 120}"
                        )

                        #Check if speeding
                        # Check if speeding
                        if speed >= SPEED_LIMIT and not speed >= OUTLIER_THRESHOLD and not speed == 0:
                            send_to_service_bus_queue(vehicle_data)
                            logging.info("Message sent to Service Bus queue.")
                        else:
                            logging.info("Vehicle speed within limit. No alert sent.")
                        
        # Write this processed frame to the output video
        #sout.write(frame)

        # Show the frame
        #cv2.imshow("Car/Truck Detection", frame)
        frame_index += 1  # increment the frame counter
        
        # Press 'q' to exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

    logging.info("\nTracked Vehicles Summary:")
    for track_id, info in tracked_vehicles.items():
        logging.info(f"Track ID: {track_id} | "
              f"Time Found: {info['timestamp']:.2f}s | "
              f"Stream: {info['stream']} | "
              f"Type: {info['vehicle_type']} | "
              f"Latest Conf: {info['latest_conf']:.2f} | "
              f"Speed: {info['speed']:.2f}")

    return tracked_vehicles # Returns dictionary with vehicles

def is_inside(cx, cy, box):
    """
    Simple utility to check if (cx, cy) is inside the region defined by box.
    box is a tuple (x1, y1, x2, y2).
    """
    x1, y1, x2, y2 = box
    return (x1 <= cx <= x2) and (y1 <= cy <= y2)
