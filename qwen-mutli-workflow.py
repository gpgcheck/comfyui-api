#!/usr/bin/env python3
"""
ComfyUI API Client
A program to generate images using ComfyUI workflow via API
"""

import json
import os
import time
import uuid
import ssl
import requests
import websocket
import glob
import mimetypes
import urllib3
from datetime import datetime
from typing import Dict, Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Disable urllib3 SSL warnings if SSL verification is disabled
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ComfyUIClient:
    """Client for interacting with ComfyUI API"""
    
    def __init__(self, server_address: Optional[str] = None):
        """
        Initialize ComfyUI client
        
        Args:
            server_address: ComfyUI server address (must include protocol: http:// or https://)
                           (default: from COMFYUI_SERVER_ADDRESS env var or http://127.0.0.1:8188)
        """
        # Priority: explicit parameter > environment variable > default
        # Server address must include protocol (http:// or https://)
        if server_address is None:
            self.server_address = os.getenv("COMFYUI_SERVER_ADDRESS", "http://127.0.0.1:8188")
        else:
            self.server_address = server_address
        self.api_key = os.getenv("COMFYUI_API_KEY", None)
        # SSL verification control (default: False for development, set to "true" to enable)
        ssl_verify = os.getenv("COMFYUI_SSL_VERIFY", "false").lower()
        self.verify_ssl = ssl_verify in ("true", "1", "yes")
        self.client_id = str(uuid.uuid4())
        self.ws = None
        self._check_server_connection()
    
    def _build_url(self, path: str) -> str:
        """
        Build full URL from server address and path
        
        Args:
            path: API path (e.g., "system_stats")
            
        Returns:
            Full URL string
        """
        # Remove leading slash from path if present
        path = path.lstrip('/')
        # Server address must include protocol (http:// or https://)
        base_url = self.server_address.rstrip('/')
        return f"{base_url}/{path}"
    
    def _build_ws_url(self, path: str) -> str:
        """
        Build WebSocket URL from server address and path
        
        Args:
            path: WebSocket path (e.g., "ws")
            
        Returns:
            Full WebSocket URL string
        """
        # Remove leading slash from path if present
        path = path.lstrip('/')
        # Convert http:// to ws:// and https:// to wss://
        if self.server_address.startswith('https://'):
            base_url = self.server_address.replace('https://', 'wss://').rstrip('/')
        else:
            # http:// or default
            base_url = self.server_address.replace('http://', 'ws://').rstrip('/')
        return f"{base_url}/{path}"
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers with API key if available
        
        Returns:
            Dictionary with headers including apikey if set
        """
        headers = {}
        if self.api_key:
            headers["apikey"] = self.api_key
        return headers
    
    def _check_server_connection(self):
        """Check if ComfyUI server is accessible"""
        try:
            response = requests.get(
                self._build_url("system_stats"),
                headers=self._get_headers(),
                verify=self.verify_ssl,
                timeout=5
            )
            response.raise_for_status()
            print(f"✓ Connected to ComfyUI server at {self.server_address}")
        except requests.exceptions.RequestException as e:
            print(f"⚠ Warning: Could not connect to ComfyUI server at {self.server_address}")
            print(f"  Error: {e}")
            print(f"  Please make sure ComfyUI is running and accessible.")
        
    def queue_prompt(self, prompt: Dict) -> str:
        """
        Queue a prompt to ComfyUI
        
        Args:
            prompt: Workflow dictionary
            
        Returns:
            Prompt ID
        """
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        try:
            req = requests.post(
                self._build_url("prompt"),
                data=data, 
                headers=self._get_headers(),
                verify=self.verify_ssl,
                timeout=30
            )
            req.raise_for_status()
            response_json = req.json()
            
            if 'prompt_id' not in response_json:
                print(f"Error: Response does not contain 'prompt_id'")
                print(f"Response: {json.dumps(response_json, indent=2)}")
                if 'error' in response_json:
                    error_msg = response_json.get('error', {})
                    if isinstance(error_msg, dict):
                        error_details = error_msg.get('message', error_msg)
                    else:
                        error_details = error_msg
                    raise ValueError(f"ComfyUI error: {error_details}")
                raise KeyError(f"'prompt_id' not found in response: {response_json}")
            
            return response_json['prompt_id']
        except requests.exceptions.RequestException as e:
            print(f"Error queueing prompt: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                try:
                    response_text = e.response.text
                    print(f"Response text: {response_text[:1000]}")
                    
                    # Try to parse and display node errors in a more readable format
                    try:
                        error_json = json.loads(response_text)
                        if 'node_errors' in error_json:
                            print("\nNode Errors:")
                            for node_id, node_error in error_json['node_errors'].items():
                                print(f"  Node {node_id}:")
                                if 'errors' in node_error:
                                    for err in node_error['errors']:
                                        err_type = err.get('type', 'Unknown')
                                        err_msg = err.get('message', 'Unknown error')
                                        err_details = err.get('details', '')
                                        print(f"    - {err_type}: {err_msg}")
                                        if err_details:
                                            print(f"      Details: {err_details[:200]}")
                        if 'error' in error_json:
                            error_info = error_json['error']
                            if isinstance(error_info, dict):
                                print(f"\nError: {error_info.get('message', 'Unknown error')}")
                                if 'details' in error_info and error_info['details']:
                                    print(f"Details: {error_info['details']}")
                    except:
                        pass
                except:
                    pass
            raise
        except (KeyError, ValueError) as e:
            print(f"Error parsing response: {e}")
            raise
    
    def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        """
        Get generated image from ComfyUI
        
        Args:
            filename: Image filename
            subfolder: Subfolder path
            folder_type: Folder type (output, input, temp)
            
        Returns:
            Image bytes
        """
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = "&".join([f"{k}={v}" for k, v in data.items()])
        response = requests.get(
            f"{self._build_url('view')}?{url_values}",
            headers=self._get_headers(),
            verify=self.verify_ssl
        )
        return response.content
    
    def upload_image(self, image_path: str, subfolder: str = "", overwrite: bool = True) -> Dict:
        """
        Upload image to ComfyUI input directory
        
        Args:
            image_path: Local path to image file
            subfolder: Subfolder in ComfyUI input directory
            overwrite: Whether to overwrite if file exists
            
        Returns:
            Dictionary with filename and subfolder
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type or not mime_type.startswith('image/'):
            mime_type = 'image/png'
        
        print(f"  Uploading: {os.path.basename(image_path)}")
        
        with open(image_path, 'rb') as f:
            files = {'image': (os.path.basename(image_path), f, mime_type)}
            data = {
                'overwrite': str(overwrite).lower(),
                'subfolder': subfolder
            }
            try:
                response = requests.post(
                    self._build_url("upload/image"),
                    files=files,
                    data=data,
                    headers=self._get_headers(),
                    verify=self.verify_ssl,
                    timeout=30
                )
                response.raise_for_status()  # Raise an exception for bad status codes
                
                # Check if response is JSON
                content_type = response.headers.get('content-type', '')
                if 'application/json' not in content_type:
                    print(f"  Warning: Unexpected content type: {content_type}")
                    print(f"  Response text: {response.text[:200]}")
                    # If not JSON, try to use the filename directly
                    return {
                        'filename': os.path.basename(image_path),
                        'subfolder': subfolder,
                        'type': 'input'
                    }
                
                result = response.json()
                return {
                    'filename': result.get('name', os.path.basename(image_path)),
                    'subfolder': result.get('subfolder', subfolder),
                    'type': 'input'
                }
            except requests.exceptions.RequestException as e:
                print(f"  Error uploading image: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    print(f"  Response status: {e.response.status_code}")
                    print(f"  Response text: {e.response.text[:200]}")
                raise
            except ValueError as e:
                # JSON decode error
                print(f"  Error parsing JSON response: {e}")
                print(f"  Response status: {response.status_code}")
                print(f"  Response text: {response.text[:500]}")
                # Fallback: use filename directly
                return {
                    'filename': os.path.basename(image_path),
                    'subfolder': subfolder,
                    'type': 'input'
                }
    
    def get_history(self, prompt_id: str) -> Dict:
        """
        Get prompt history
        
        Args:
            prompt_id: Prompt ID
            
        Returns:
            History dictionary
        """
        response = requests.get(
            self._build_url(f"history/{prompt_id}"),
            headers=self._get_headers(),
            verify=self.verify_ssl
        )
        return response.json()
    
    def wait_for_completion(self, prompt_id: str, timeout: int = 300) -> Dict:
        """
        Wait for prompt completion using WebSocket
        
        Args:
            prompt_id: Prompt ID
            timeout: Timeout in seconds
            
        Returns:
            Result dictionary with output images
        """
        # Build WebSocket URL with API key if available
        ws_url = self._build_ws_url("ws")
        ws_url += f"?clientId={self.client_id}"
        if self.api_key:
            ws_url += f"&apikey={self.api_key}"
        
        # Configure SSL options for WebSocket
        sslopt = None
        if not self.verify_ssl:
            # Disable SSL certificate verification for WebSocket
            sslopt = {
                "cert_reqs": ssl.CERT_NONE,
                "check_hostname": False
            }
        
        # Use create_connection which properly supports sslopt
        self.ws = websocket.create_connection(ws_url, sslopt=sslopt)
        
        start_time = time.time()
        output_images = {}
        
        while time.time() - start_time < timeout:
            out = self.ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        # Execution finished
                        break
                elif message['type'] == 'progress':
                    # Progress update
                    data = message['data']
                    print(f"Progress: {data['value']}/{data['max']} - {data.get('type', '')}")
                elif message['type'] == 'executed':
                    # Node execution completed
                    data = message['data']
                    if 'output' in data and 'images' in data['output']:
                        for image in data['output']['images']:
                            output_images[data['node']] = image
            else:
                # Binary data
                continue
        
        self.ws.close()
        self.ws = None
        
        if time.time() - start_time >= timeout:
            raise TimeoutError(f"Prompt execution timed out after {timeout} seconds")
        
        return output_images
    
    def generate_image(
        self, 
        workflow: Dict, 
        output_dir: str = "./output",
        timeout: int = 300
    ) -> List[str]:
        """
        Generate image from workflow
        
        Args:
            workflow: Workflow dictionary
            output_dir: Output directory for saved images
            timeout: Timeout in seconds
            
        Returns:
            List of saved image paths
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Queueing prompt...")
        prompt_id = self.queue_prompt(workflow)
        print(f"Prompt ID: {prompt_id}")
        
        print("Waiting for completion...")
        output_images = self.wait_for_completion(prompt_id, timeout)
        
        # Get history to find all output images
        history = self.get_history(prompt_id)
        saved_images = []
        
        if prompt_id in history:
            for node_id, node_output in history[prompt_id]['outputs'].items():
                if 'images' in node_output:
                    for image_info in node_output['images']:
                        filename = image_info['filename']
                        subfolder = image_info.get('subfolder', '')
                        folder_type = image_info.get('type', 'output')
                        
                        print(f"Downloading image: {filename}")
                        image_data = self.get_image(filename, subfolder, folder_type)
                        
                        # Add date timestamp to filename
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        name, ext = os.path.splitext(filename)
                        new_filename = f"{name}_{timestamp}{ext}"
                        
                        # Save image
                        output_path = os.path.join(output_dir, new_filename)
                        with open(output_path, 'wb') as f:
                            f.write(image_data)
                        saved_images.append(output_path)
                        print(f"Saved image to: {output_path}")
        
        return saved_images


def load_workflow(workflow_path: str) -> Dict:
    """
    Load workflow from JSON file
    
    Args:
        workflow_path: Path to workflow JSON file
        
    Returns:
        Workflow dictionary
    """
    with open(workflow_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_images_in_folder(folder_path: str, extensions: tuple = ('.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG')) -> List[str]:
    """
    Find image files in a folder
    
    Args:
        folder_path: Path to folder
        extensions: Image file extensions to search for
        
    Returns:
        List of image file paths, sorted by name
    """
    if not os.path.exists(folder_path):
        return []
    
    images = []
    for ext in extensions:
        images.extend(glob.glob(os.path.join(folder_path, f'*{ext}')))
    
    return sorted(images)


def update_workflow_images(
    workflow: Dict, 
    client: Optional[ComfyUIClient] = None,
    image1_path: Optional[str] = None,
    image2_path: Optional[str] = None,
    image3_path: Optional[str] = None
) -> Dict:
    """
    Update image paths in workflow and upload images if needed
    
    Args:
        workflow: Workflow dictionary
        client: ComfyUI client instance for uploading images
        image1_path: Path to first image (node 78)
        image2_path: Path to second image (node 106)
        image3_path: Path to third image (node 108)
        
    Returns:
        Updated workflow dictionary
    """
    if image1_path and "78" in workflow:
        if client:
            # Upload image to ComfyUI
            result = client.upload_image(image1_path)
            workflow["78"]["inputs"]["image"] = result['filename']
        else:
            workflow["78"]["inputs"]["image"] = os.path.basename(image1_path)
    
    if image2_path and "106" in workflow:
        if client:
            result = client.upload_image(image2_path)
            workflow["106"]["inputs"]["image"] = result['filename']
        else:
            workflow["106"]["inputs"]["image"] = os.path.basename(image2_path)
    
    if image3_path and "108" in workflow:
        if client:
            result = client.upload_image(image3_path)
            workflow["108"]["inputs"]["image"] = result['filename']
        else:
            workflow["108"]["inputs"]["image"] = os.path.basename(image3_path)
    
    return workflow


def update_workflow_prompt(workflow: Dict, prompt: str) -> Dict:
    """
    Update prompt in workflow
    
    Args:
        workflow: Workflow dictionary
        prompt: New prompt text
        
    Returns:
        Updated workflow dictionary
    """
    if "111" in workflow:
        workflow["111"]["inputs"]["prompt"] = prompt
    return workflow


def update_workflow_lora(workflow: Dict, lora_name: Optional[str] = None, node_id: str = "89") -> Dict:
    """
    Update LoRA name in workflow
    
    Args:
        workflow: Workflow dictionary
        lora_name: New LoRA filename (optional)
        node_id: Node ID to update (default: "89")
        
    Returns:
        Updated workflow dictionary
    """
    if lora_name and node_id in workflow:
        if "inputs" in workflow[node_id] and "lora_name" in workflow[node_id]["inputs"]:
            workflow[node_id]["inputs"]["lora_name"] = lora_name
            print(f"Updated LoRA name in node {node_id} to: {lora_name}")
    return workflow


def update_workflow_seed(workflow: Dict, seed: Optional[int] = None, node_id: str = "3") -> Dict:
    """
    Update seed value in workflow sampler
    
    Args:
        workflow: Workflow dictionary
        seed: Random seed value (if None, keeps workflow default or uses random)
        node_id: Node ID to update (default: "3" for KSampler)
        
    Returns:
        Updated workflow dictionary
    """
    if seed is not None and node_id in workflow:
        if "inputs" in workflow[node_id] and "seed" in workflow[node_id]["inputs"]:
            workflow[node_id]["inputs"]["seed"] = seed
            print(f"Updated seed in node {node_id} to: {seed}")
    elif seed is None:
        # If seed is None, use random seed for variation
        import random
        random_seed = random.randint(0, 2**32 - 1)
        if node_id in workflow and "inputs" in workflow[node_id] and "seed" in workflow[node_id]["inputs"]:
            workflow[node_id]["inputs"]["seed"] = random_seed
            print(f"Using random seed in node {node_id}: {random_seed}")
    return workflow


def main():
    """Main function"""
    import argparse
    
    # ============================================
    # Configuration: Set image paths and prompt here
    # ============================================
    # Image paths (set to None to use input_images folder or command line arguments)
    IMAGE1_PATH = "input_images/image01.png"
    IMAGE2_PATH = "input_images/image02.png"
    IMAGE3_PATH = "input_images/image03.png"
    
    # Prompt text (set to None to use environment variable or workflow default)
    PROMPT = "put three model in one image"
    
    # LoRA filename (set to None to use workflow default)
    # Available options based on error message:
    # - Qwen-Image-Edit-2509-Lightning-4steps-V1.0-fp32.safetensors
    # - Qwen-Image-Edit-2509-Lightning-8steps-V1.0-bf16.safetensors
    # - Qwen-Image-Edit-2509-Lightning-8steps-V1.0-fp32.safetensors
    LORA_NAME = "Qwen-Image-Edit-2509-Lightning-8steps-V1.0-fp32.safetensors"
    
    # Random seed for image generation (set to None for random seed each time)
    # Seed controls the randomness of generation:
    # - Same seed + same prompt = same result (reproducible)
    # - Different seed = different variations
    # - None = random seed (different result each time)
    SEED = None  # e.g., 940686007127064 or None for random
    # ============================================
    
    parser = argparse.ArgumentParser(description="Generate images using ComfyUI workflow")
    parser.add_argument(
        "--workflow", 
        type=str, 
        default="qwen_image_edit_2509_multi.json",
        help="Path to workflow JSON file"
    )
    parser.add_argument(
        "--server", 
        type=str, 
        default=None,
        help="ComfyUI server address (default: from COMFYUI_SERVER_ADDRESS env var or 127.0.0.1:8188)"
    )
    parser.add_argument(
        "--output-dir", 
        type=str, 
        default="output",
        help="Output directory for generated images (default: output)"
    )
    parser.add_argument(
        "--input-images-dir", 
        type=str, 
        default="input_images",
        help="Directory containing input images (default: input_images)"
    )
    parser.add_argument(
        "--prompt", 
        type=str,
        default=os.getenv("COMFYUI_PROMPT", None),
        help="Edit prompt (default: from COMFYUI_PROMPT env var or workflow default)"
    )
    parser.add_argument(
        "--image1", 
        type=str,
        help="Path to first image (optional, overrides input_images_dir)"
    )
    parser.add_argument(
        "--image2", 
        type=str,
        help="Path to second image (optional, overrides input_images_dir)"
    )
    parser.add_argument(
        "--image3", 
        type=str,
        help="Path to third image (optional, overrides input_images_dir)"
    )
    parser.add_argument(
        "--timeout", 
        type=int, 
        default=300,
        help="Timeout in seconds (default: 300)"
    )
    
    args = parser.parse_args()
    
    # Load workflow
    print(f"Loading workflow from: {args.workflow}")
    workflow = load_workflow(args.workflow)
    
    # Initialize client (None means use environment variable or default)
    client = ComfyUIClient(server_address=args.server if args.server else None)
    
    # Determine image paths
    # Priority: command line > main function variables > input_images folder
    image1_path = args.image1 or IMAGE1_PATH
    image2_path = args.image2 or IMAGE2_PATH
    image3_path = args.image3 or IMAGE3_PATH
    
    # If images not specified, try to load from input_images_dir
    if not (image1_path and image2_path and image3_path):
        if os.path.exists(args.input_images_dir):
            print(f"Loading images from: {args.input_images_dir}")
            input_images = find_images_in_folder(args.input_images_dir)
            
            if len(input_images) >= 3:
                if not image1_path:
                    image1_path = input_images[0]
                    print(f"  Using image1: {os.path.basename(image1_path)}")
                if not image2_path:
                    image2_path = input_images[1]
                    print(f"  Using image2: {os.path.basename(image2_path)}")
                if not image3_path:
                    image3_path = input_images[2]
                    print(f"  Using image3: {os.path.basename(image3_path)}")
            elif len(input_images) > 0:
                print(f"Warning: Found {len(input_images)} image(s) in {args.input_images_dir}, need 3 images")
                # Use available images
                if not image1_path and len(input_images) > 0:
                    image1_path = input_images[0]
                if not image2_path and len(input_images) > 1:
                    image2_path = input_images[1]
                if not image3_path and len(input_images) > 2:
                    image3_path = input_images[2]
            else:
                print(f"Warning: No images found in {args.input_images_dir}")
        else:
            print(f"Warning: Input images directory '{args.input_images_dir}' does not exist")
    
    # Update workflow prompt if needed
    # Priority: command line argument > main function variable > environment variable > workflow default
    prompt = args.prompt or PROMPT or os.getenv("COMFYUI_PROMPT", None)
    if prompt:
        prompt_source = "command line" if args.prompt else ("main function" if PROMPT else "environment variable")
        print(f"Using prompt from {prompt_source}: {prompt[:50]}...")
        workflow = update_workflow_prompt(workflow, prompt)
    else:
        # Use workflow default prompt if available
        if "111" in workflow and "inputs" in workflow["111"] and "prompt" in workflow["111"]["inputs"]:
            default_prompt = workflow["111"]["inputs"]["prompt"]
            if default_prompt:
                print(f"Using workflow default prompt: {default_prompt[:50]}...")
    
    # Update LoRA name if specified
    if LORA_NAME:
        workflow = update_workflow_lora(workflow, LORA_NAME)
    
    # Update seed if specified (None means use random seed)
    workflow = update_workflow_seed(workflow, SEED)
    
    # Upload and update images in workflow
    if image1_path or image2_path or image3_path:
        print("Uploading images to ComfyUI...")
        workflow = update_workflow_images(
            workflow, 
            client=client,
            image1_path=image1_path, 
            image2_path=image2_path, 
            image3_path=image3_path
        )
    
    # Generate image
    try:
        saved_images = client.generate_image(
            workflow, 
            output_dir=args.output_dir,
            timeout=args.timeout
        )
        
        print(f"\n✓ Successfully generated {len(saved_images)} image(s):")
        for img_path in saved_images:
            print(f"  - {img_path}")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

