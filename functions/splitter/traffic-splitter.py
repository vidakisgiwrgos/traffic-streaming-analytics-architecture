import azure.functions as func
import logging
import json

app = func.FunctionApp()

@app.function_name("SpeedingAlerts")
@app.service_bus_queue_trigger(arg_name="msg", queue_name="speedingcarsqueue",
                               connection="SpeedingCarsQueue_SERVICEBUS") 
def realTimeAlerts(msg: func.ServiceBusMessage):
    # The message is accessible via msg.get_body()
    message_body = msg.get_body().decode('utf-8')
    logging.info(f"Service Bus queue triggered AlertFunction. Message: {message_body}")

    try:
        data = json.loads(message_body)
        speed = data.get("speed")
        vehicle_type = data.get("vehicle_type")
        timestamp = data.get("timestamp")
        camera = data.get("camera")

        # Perform your alert logic here
        # For example, send an email, SMS or log to a monitoring service.
        alert_message = f"ALERT: {vehicle_type} exceeded speed limit at {speed} mph on timestamp {timestamp} at camera {camera}"
        logging.warning(alert_message)

       
        
    except json.JSONDecodeError:
        logging.error("Failed to decode message body as JSON.")
    except Exception as e:
        logging.error(f"An error occurred while processing the alert: {e}")
