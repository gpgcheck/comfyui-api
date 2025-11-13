# ComfyUI Image Generation Client

A Python program to generate images using ComfyUI API with the Qwen image editing workflow.

## Setup

### 1. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate
```

Or use the setup script:
```bash
./setup.sh
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables (Optional)

Create a `.env` file in the project root to configure settings:

```bash
# Copy the example file
cp env.example .env

# Edit .env file with your settings
# COMFYUI_SERVER_ADDRESS=127.0.0.1:8188
# COMFYUI_PROMPT=change the woman's shirt to red and change the background to a forest
```

Or set environment variables directly:

```bash
# On macOS/Linux:
export COMFYUI_SERVER_ADDRESS=127.0.0.1:8188
export COMFYUI_PROMPT="change the woman's shirt to red and change the background to a forest"

# On Windows:
# set COMFYUI_SERVER_ADDRESS=127.0.0.1:8188
# set COMFYUI_PROMPT=change the woman's shirt to red and change the background to a forest
```

- `COMFYUI_SERVER_ADDRESS`: Server address (default: `127.0.0.1:8188`)
- `COMFYUI_PROMPT`: Edit prompt text (default: uses workflow default prompt)

**Note**: The program automatically loads variables from `.env` file if it exists.

### 4. Prepare Input Images

Create an `input_images` folder and place your three input images there:

```bash
mkdir -p input_images
# Place your images in input_images folder
# The program will automatically use the first 3 images found (sorted by name)
```

### 5. Start ComfyUI Server

Make sure ComfyUI is running and accessible at the configured server address.

## Usage

### Method 1: Set Variables in main() Function (Recommended)

Edit `comfyui_client.py` and set the variables at the beginning of the `main()` function:

```python
# Configuration: Set image paths and prompt here
IMAGE1_PATH = "input_images/image1.png"
IMAGE2_PATH = "input_images/image2.jpg"
IMAGE3_PATH = "input_images/image3.jpg"

PROMPT = "change the woman's shirt to red and change the background to a forest"
```

Then run:
```bash
python comfyui_client.py --workflow qwen_image_edit_2509_multi.json
```

### Method 2: Auto-load from input_images folder

The program will automatically:
- Load 3 images from `input_images` folder (sorted by filename)
- Upload them to ComfyUI
- Save generated images to `output` folder

```bash
python comfyui_client.py --workflow qwen_image_edit_2509_multi.json
```

### With Custom Prompt

You can set the prompt in four ways (priority order):
1. Command line argument `--prompt` (highest priority)
2. Variable `PROMPT` in main() function
3. Environment variable `COMFYUI_PROMPT`
4. Workflow default prompt (lowest priority)

```bash
# Using command line argument
python comfyui_client.py \
  --workflow qwen_image_edit_2509_multi.json \
  --prompt "change the woman's shirt to red and change the background to a forest"

# Using environment variable
export COMFYUI_PROMPT="change the woman's shirt to red and change the background to a forest"
python comfyui_client.py --workflow qwen_image_edit_2509_multi.json
```

### With Custom Images

You can override the default `input_images` folder by specifying individual image paths:

```bash
python comfyui_client.py \
  --workflow qwen_image_edit_2509_multi.json \
  --image1 path/to/image1.png \
  --image2 path/to/image2.jpg \
  --image3 path/to/image3.jpg \
  --prompt "your edit prompt here"
```

### With Custom Input Images Directory

```bash
python comfyui_client.py \
  --workflow qwen_image_edit_2509_multi.json \
  --input-images-dir ./my_images \
  --prompt "your edit prompt here"
```

### With Custom Server Address

You can set the server address in three ways (priority order):
1. Command line argument `--server` (highest priority)
2. Environment variable `COMFYUI_SERVER_ADDRESS`
3. Default value `127.0.0.1:8188` (lowest priority)

```bash
# Using command line argument
python comfyui_client.py \
  --server 192.168.1.100:8188 \
  --workflow qwen_image_edit_2509_multi.json

# Using environment variable
export COMFYUI_SERVER_ADDRESS=192.168.1.100:8188
python comfyui_client.py --workflow qwen_image_edit_2509_multi.json
```

### With Custom Output Directory

By default, images are saved to `output` folder. You can change it:

```bash
python comfyui_client.py \
  --workflow qwen_image_edit_2509_multi.json \
  --output-dir ./my_output
```

## Command Line Arguments

- `--workflow`: Path to workflow JSON file (default: `qwen_image_edit_2509_multi.json`)
- `--server`: ComfyUI server address (default: from `COMFYUI_SERVER_ADDRESS` env var or `127.0.0.1:8188`)
- `--output-dir`: Output directory for generated images (default: `output`)
- `--input-images-dir`: Directory containing input images (default: `input_images`)
- `--prompt`: Edit prompt (default: from `COMFYUI_PROMPT` env var or workflow default)
- `--image1`: Path to first image (optional, overrides `--input-images-dir`)
- `--image2`: Path to second image (optional, overrides `--input-images-dir`)
- `--image3`: Path to third image (optional, overrides `--input-images-dir`)
- `--timeout`: Timeout in seconds (default: 300)

## Workflow Information

This workflow uses:
- Qwen image editing models
- Multi-image input support
- Image editing with text prompts

The workflow expects:
- Image 1: Main image to edit (node 78)
- Image 2: Reference image 1 (node 106)
- Image 3: Reference image 2 (node 108)
- Prompt: Text description of desired edits (node 111)

## Notes

- **Input Images**: The program automatically loads images from `input_images` folder (sorted by filename). If you specify `--image1`, `--image2`, or `--image3`, those will override the folder-based loading.
- **Image Upload**: Images are automatically uploaded to ComfyUI's input directory via API, so you don't need to manually copy them.
- **Output**: Generated images are saved to the `output` folder by default.
- **Image Order**: When loading from `input_images` folder, images are used in alphabetical order (first 3 images found).
- **Image Path Priority**: Command line `--image1/2/3` > Variables in main() `IMAGE1/2/3_PATH` > `input_images` folder.
- **Prompt Priority**: Command line `--prompt` > Variable in main() `PROMPT` > Environment variable `COMFYUI_PROMPT` > Workflow default prompt.
- The program uses WebSocket to monitor progress and completion.

