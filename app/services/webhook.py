import requests

def send_webhook_notification(url, event, data):
    try:
        requests.post(url, json={"event": event, "data": data})
    except Exception as e:
        # Log error or handle as needed
        pass