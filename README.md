# Signal Artificial Intelligence

This repository provides a client script that communicates with an Ollama server to process messages using an LLM model.

## Requirements

* `signal-cli` (installed and configured)
* `mqtt` (installed and configured on both client and server)
* Static IP address for both client and server machines
* `.env` file on the client machine with phone number for the bot set

## Server Requirements

* `ollama` server with MQTT enabled
* LLM model of choice pulled from ollama: (e.g. `ollama pull llama3.2`) 

## Client Machine Configuration

* Connect to `ollama` server via MQTT
* Process incoming messages received from Signal CLI
* Forward processed message to `ollama` server for response
* Receive response from `ollama` server and forward it back to Signal CLI

## Optional: VPN (Tailscale/Zero Tier)**

For outside communication with the internal server, consider using a VPN like Tailscale or Zero Tier.

## How it Works

1. User sends message through Signal messaging app.
2. Client receives message via `signal-cli` and processes it.
3. Client forwards processed message to Ollama server via MQTT.
4. Ollama server uses LLM model (e.g. `llama3.2`) to process message.
5. Ollama server responds with AI-generated response.
6. Client receives response from Ollama server via MQTT.
7. Client forwards response back to Signal CLI.
8. Signal CLI displays response to user.

## Scalability

This design allows for scalability by separating the client and server configurations, enabling the ability to create multiple bots without overwelming the Ollama server.

## Running the Bot

To run the bot, please make sure you have all the requirements installed and configured. You can run the bot in the normal way with python3 file.py, where file.py is the code file you're trying to run. However i strongly recommend running both files as a service on the respected machines.
**Running as a Service**

If you prefer to run this script as a service, you can create a systemd service file in the `/etc/systemd/system/` directory. This allows for easy management of the bot via the system's service manager.
