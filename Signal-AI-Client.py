import subprocess
import re
import os
import asyncio
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from typing import Optional
from queue import Queue

# Load environment variables
load_dotenv()
PHONE_NUMBER_BOT = os.getenv('PHONE_NUMBER_BOT')

class SignalMQTTBridge:
    def __init__(self):
        # Message queue to store pending responses
        self.response_queue = Queue()
        
        # MQTT client for receiving responses
        self.receive_client = mqtt.Client()
        self.receive_client.on_connect = self.on_connect
        self.receive_client.on_message = self.on_message
        
        # MQTT client for sending messages
        self.send_client = mqtt.Client()
        
        # Store the current sender for response handling
        self.current_sender = None
        
        # Connect to MQTT brokers
        self.receive_client.connect("0.0.0.0")  # CLIENT IP (THIS MACHINE)
        self.send_client.connect("0.0.0.0")     # SERVER IP (WHERE OLLAMA RUNS)
        
        # Start MQTT loops
        self.receive_client.loop_start()
        self.send_client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        # Callback for when the client connects to the MQTT broker
        print(f"Connected to MQTT broker with result code {rc}")
        client.subscribe("bot_out")  # Subscribe to bot's output topic

    def on_message(self, client, userdata, message):
        # Handle incoming MQTT messages by adding them to the response queue
        response = message.payload.decode()
        print(f"Received MQTT response: {response}")
        if self.current_sender:
            self.response_queue.put((self.current_sender, response))

    async def send_signal_message(self, to: str, message: str):
        # Send a Signal message using signal-cli
        try:
            print(f"Attempting to send Signal message: '{message}' to {to}")
            subprocess.run(
                ["/usr/local/bin/signal-cli", "-u", PHONE_NUMBER_BOT, "send", "-m", message, to],
                check=True
            )
            print(f"Successfully sent Signal message: '{message}' to {to}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to send Signal message: {e}")

    async def receive_signal_messages(self):
        # Receive messages using signal-cli
        try:
            result = subprocess.run(
                ["/usr/local/bin/signal-cli", "-u", PHONE_NUMBER_BOT, "receive"],
                capture_output=True,
                text=True,
                check=True
            )
            messages = result.stdout.strip()
            if messages:
                return messages.split("\n\n")
            print("No new Signal messages received.")
            return []
        except subprocess.CalledProcessError as e:
            print(f"Failed to receive Signal messages: {e}")
            return []

    def parse_signal_message(self, raw_message: str):
        # Parse received raw Signal message to extract sender and message body
        envelope_match = re.search(r'Envelope from: .+ (\+\d+) \(device: \d+\) to .+', raw_message)
        body_match = re.search(r'Body: (.+)', raw_message)

        if envelope_match and body_match:
            return envelope_match.group(1), body_match.group(1)
        return None, None

    def publish_to_mqtt(self, message: str):
        # Publish message to MQTT broker
        self.send_client.publish("bot_in", message)  # Publish to bot's input topic
        print(f"Published to MQTT: {message}")

    def cleanup(self):
        # Clean up MQTT connections
        self.send_client.loop_stop()
        self.receive_client.loop_stop()
        self.send_client.disconnect()
        self.receive_client.disconnect()

    async def process_responses(self):
        # Process any pending responses in the queue
        while True:
            try:
                if not self.response_queue.empty():
                    sender, response = self.response_queue.get_nowait()
                    print(f"Processing queued response for {sender}: {response}")
                    await self.send_signal_message(sender, response)
            except Exception as e:
                print(f"Error processing response: {e}")
            await asyncio.sleep(0.1)

    async def run(self):
        # Main loop to handle Signal messages and MQTT communication
        print("Starting Signal-MQTT bridge...")
        try:
            # Start response processing coroutine
            response_task = asyncio.create_task(self.process_responses())
            
            while True:
                messages = await self.receive_signal_messages()
                for raw_message in messages:
                    sender, body = self.parse_signal_message(raw_message)
                    if sender and body:
                        print(f"Signal message received from {sender}: '{body}'")
                        
                        # Set current sender before publishing
                        self.current_sender = sender
                        
                        # Publish the message to MQTT
                        self.publish_to_mqtt(body)
                        
                        # Wait a moment for MQTT response
                        await asyncio.sleep(0.5)
                
                await asyncio.sleep(1)  # Check for new messages every second
                
        except KeyboardInterrupt:
            print("\nShutting down...")
            response_task.cancel()
            self.cleanup()

if __name__ == "__main__":
    bridge = SignalMQTTBridge()
    try:
        asyncio.run(bridge.run())
    except KeyboardInterrupt:
        print("\nExiting...")
        bridge.cleanup()
