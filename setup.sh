#!/bin/bash
# Setup script for ComfyUI client

echo "Creating virtual environment..."
python3 -m venv .venv

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Setup complete!"
echo "To activate the virtual environment, run:"
echo "  source .venv/bin/activate"
echo ""
echo "To set server address (optional):"
echo "  export COMFYUI_SERVER_ADDRESS=127.0.0.1:8188"
echo ""
echo "To run the client:"
echo "  python comfyui_client.py --workflow qwen_image_edit_2509_multi.json"

