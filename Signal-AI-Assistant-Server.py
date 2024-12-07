## Server Side Code ##
import paho.mqtt.client as mqtt
import asyncio
import ollama
import signal
from concurrent.futures import ThreadPoolExecutor

class PersonalityBot:
    def __init__(self, bot_config):
        # Initialize MQTT clients with callback API v2
        self.response_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        
        # Bot-specific settings - configure client and server IPs
        self.bot_name = bot_config['name']
        self.RESPONSE_BROKER = "0.0.0.0"  # Client IP - for sending responses
        self.REQUEST_BROKER = "0.0.0.0"   # Server IP - for receiving messages
        self.personality_context = bot_config['personality']
        
        # Initialize connection state management
        self.response_in_progress = False
        self.loop = asyncio.get_event_loop()
        self.executor = ThreadPoolExecutor(max_workers=1)

        # Set up initial conversation history with system personality
        self.conversation_history = [
            {
                "role": "system",
                "content": self.personality_context
            }
        ]

    def on_connect(self, client, userdata, flags, reason_code, properties):
        # Handle MQTT broker connection
        print(f"{self.bot_name} connected with reason code: {reason_code}")
        if client == self.client:
            # Subscribe to input channel when connected to request broker
            client.subscribe(f"{self.bot_name.lower()}_in")
            print(f"{self.bot_name} listening on {self.bot_name.lower()}_in")

    def ollama_chat(self, message_content):
        # Process chat messages through Ollama
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": message_content
        })

        # Get response from Ollama model
        response = ollama.chat(model='LARGE_LANGUAGE_MODEL', messages=self.conversation_history) # REPLACE "LARGE_LANGUAGE_MODEL" With LLM Name (Ex. Llama3.2)

        # Add assistant response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": response['message']['content']
        })

        # Keep conversation history manageable
        if len(self.conversation_history) > 11:
            self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-10:]

        return response

    async def process_message(self, message):
        # Handle incoming messages asynchronously
        if self.response_in_progress:
            return
        
        self.response_in_progress = True
        try:
            # Decode and process message
            message_content = message.payload.decode()
            print(f"{self.bot_name} received: {message_content}")
            
            # Get response using thread executor
            response = await self.loop.run_in_executor(
                self.executor, 
                self.ollama_chat,
                message_content
            )

            # Send response back through MQTT
            response_message = response['message']['content']
            print(f"{self.bot_name} responding: {response_message}")
            self.response_client.publish(f"{self.bot_name.lower()}_out", response_message)
            
        except Exception as e:
            print(f"{self.bot_name} error processing message: {e}")
        finally:
            self.response_in_progress = False

    def on_message(self, client, userdata, msg):
        # MQTT message callback handler
        asyncio.run_coroutine_threadsafe(self.process_message(msg), self.loop)

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        # Handle MQTT broker disconnection
        print(f"{self.bot_name} disconnected with reason code: {reason_code}")

    def cleanup(self):
        # Clean up MQTT connections and executor
        print(f"Cleaning up {self.bot_name}'s connections...")
        try:
            self.client.loop_stop()
            self.response_client.loop_stop()
            self.client.disconnect()
            self.response_client.disconnect()
            self.executor.shutdown(wait=False)
        except Exception as e:
            print(f"Error during cleanup: {e}")

    async def start(self):
        # Initialize and start the bot
        # Set up callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        self.response_client.on_connect = self.on_connect
        self.response_client.on_disconnect = self.on_disconnect
        
        try:
            # Connect to MQTT brokers
            self.response_client.connect(self.RESPONSE_BROKER)
            self.client.connect(self.REQUEST_BROKER)
            
            # Start MQTT loops
            self.response_client.loop_start()
            self.client.loop_start()
            
            print(f"{self.bot_name} is online and listening...")
            
            while True:
                await asyncio.sleep(1)
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.cleanup()

# Personality Parameters - Define conversational traits and behaviors 
# to create more natural human-like interactions in responses
BOT_CONFIG = {
    'name': 'Bot_Name',
    'personality': """
    You are Bot_Name, [appearance and characteristics].
    From [location], you [personality essence].
    
    Key traits about you:
    - [List traits]
    - [List characteristics]
    
    Your background:
    - [Background details]
    - [Life experiences]
    
    Remember:
    """
}

async def run_bots():
    # Initialize and run the bot(s)
    # Set up signal handler for graceful shutdown
    def signal_handler(signum, frame):
        print("\nSignal received, cleaning up...")
        for task in asyncio.all_tasks():
            task.cancel()
        
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Create bot instance
        bot = PersonalityBot(BOT_CONFIG)
        await bot.start()
    except asyncio.CancelledError:
        print("Shutting down bot...")
    except Exception as e:
        print(f"Error running bot: {e}")

if __name__ == "__main__":
    print("Starting Bot_Name...")  # Replace with actual bot name
    asyncio.run(run_bots())
