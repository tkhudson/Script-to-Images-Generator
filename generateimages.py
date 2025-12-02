import argparse
import csv
import json
import logging
import os
import time
import base64
import requests  # For downloading if using URL format
import getpass  # For secure API key input
from openai import OpenAI

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_input_file(file_path):
    """
    Load scenes from CSV or JSON file.
    For CSV: expects columns - scene_number, script_line, scene_type, props (optional, comma-separated)
    For JSON: list of dicts with keys: scene_number, script_line, scene_type, props (optional list or str)
    """
    scenes = []
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.csv':
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                scene = {
                    'scene_number': int(row['scene_number']),
                    'script_line': row['script_line'],
                    'scene_type': row['scene_type'],
                    'props': row.get('props', '').split(',') if row.get('props') else [],
                    'style': row.get('style', 'photorealistic')  # Default if not present
                }
                scenes.append(scene)
    elif file_ext == '.json':
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                scene = {
                    'scene_number': int(item['scene_number']),
                    'script_line': item['script_line'],
                    'scene_type': item['scene_type'],
                    'props': item.get('props', []) if isinstance(item.get('props'), list) else item.get('props', '').split(',')
                }
                scenes.append(scene)
    else:
        raise ValueError("Unsupported file format. Use CSV or JSON.")
    
    # Sort by scene_number
    scenes.sort(key=lambda x: x['scene_number'])
    return scenes

def generate_prompt(scene, template):
    """
    Generate prompt using template.
    Template example: "A {style} {scene_type} scene: {script_line}. Include props: {props}"
    Note: Reference images are not supported by xAI API, so incorporate descriptions into the prompt if needed.
    """
    props_str = ', '.join(scene['props']) if scene['props'] else 'no props'
    style = scene.get('style', 'photorealistic')  # Default to photorealistic if not specified

    prompt = template.format(
        style=style,
        scene_type=scene['scene_type'],
        script_line=scene['script_line'],
        props=props_str
    )
    return prompt

def generate_image(client, prompt, image_format='base64', retry_count=3):
    """
    Generate image using xAI Grok API.
    Returns image bytes.
    """
    for attempt in range(retry_count):
        try:
            response_format = "b64_json" if image_format == 'base64' else "url"
            response = client.images.generate(
                model="grok-2-image",
                prompt=prompt,
                n=1,
                response_format=response_format
            )
            if image_format == 'base64':
                # Decode base64 to bytes
                img_bytes = base64.b64decode(response.data[0].b64_json)
            elif image_format == 'url':
                # Download from URL
                img_response = requests.get(response.data[0].url)
                img_response.raise_for_status()
                img_bytes = img_response.content
            else:
                raise ValueError("Unsupported image_format")
            return img_bytes
        except Exception as e:
            logger.error(f"Attempt {attempt+1} failed: {str(e)}")
            if attempt == retry_count - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff

def get_script_input():
    """
    Get multi-line script input from user.
    """
    print("\n" + "="*60)
    print("SCRIPT INPUT MODE")
    print("="*60)
    print("Enter your storyline/script (press Ctrl+D or type 'END' on a new line to finish):")
    print()

    lines = []
    try:
        while True:
            line = input()
            if line.strip().upper() == 'END':
                break
            lines.append(line)
    except EOFError:
        pass

    script = '\n'.join(lines).strip()
    if not script:
        raise ValueError("No script provided.")
    return script

def get_style_preference():
    """
    Get user's preferred image style.
    """
    print("\n" + "="*60)
    print("STYLE PREFERENCE")
    print("="*60)

    styles = [
        "photorealistic",
        "animated",
        "3D animation",
        "cartoon",
        "digital art",
        "cinematic",
        "sketch/artistic"
    ]

    print("Choose your preferred image style:")
    for i, style in enumerate(styles, 1):
        print(f"{i}. {style}")

    while True:
        try:
            choice = input(f"\nEnter choice (1-{len(styles)}) or type custom style: ").strip()
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(styles):
                    return styles[idx]
            elif choice:
                return choice
        except (ValueError, KeyboardInterrupt):
            pass
        print("Invalid choice. Please try again.")

def parse_script_with_ai(client, script, style_preference):
    """
    Use Grok API to parse the script into structured scenes.
    """
    prompt = f"""You are a video production assistant. Analyze this script and break it down into individual scenes for image generation.

SCRIPT:
{script}

INSTRUCTIONS:
1. Break the script into 3-8 logical scenes that would work well for a video
2. For each scene, determine if it should be "animated" (movement/action) or "static" (still moment)
3. Identify any props or objects that should be visible in each scene
4. Keep scene descriptions concise but descriptive

OUTPUT FORMAT: Return ONLY a valid JSON array of objects with this exact structure:
[
  {{
    "scene_number": 1,
    "script_line": "Brief description of what happens in this scene",
    "scene_type": "animated" or "static",
    "props": ["prop1", "prop2"] (empty array if no props)
  }}
]

Make sure the scene descriptions will work well for AI image generation in a {style_preference} style."""

    try:
        response = client.chat.completions.create(
            model="grok-3",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )

        content = response.choices[0].message.content.strip()

        # Try to extract JSON from response
        import json
        try:
            # Look for JSON array in the response
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                scenes = json.loads(json_str)
                return scenes
            else:
                raise ValueError("No JSON array found in response")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content: {content}")
            raise

    except Exception as e:
        logger.error(f"Failed to parse script with AI: {str(e)}")
        raise

def write_scenes_to_csv(scenes, output_file):
    """
    Write scenes to CSV file.
    """
    import csv
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['scene_number', 'script_line', 'scene_type', 'props'])
        writer.writeheader()
        for scene in scenes:
            # Convert props list to comma-separated string and exclude 'style' field
            scene_copy = scene.copy()
            if isinstance(scene_copy['props'], list):
                scene_copy['props'] = ','.join(scene_copy['props'])
            # Remove 'style' field as it's only used for prompts, not stored in CSV
            scene_copy.pop('style', None)
            writer.writerow(scene_copy)

    logger.info(f"Generated CSV file: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Automate image generation from YouTube scripts using xAI Grok API.")
    parser.add_argument('--input_file', help='Path to CSV or JSON input file.')
    parser.add_argument('--script_input', action='store_true', help='Enable script input mode to automatically parse a script into scenes.')
    parser.add_argument('--api_key', help='xAI Grok API key (if not provided, will prompt securely).')
    parser.add_argument('--output_dir', default='output_images', help='Directory to save generated images.')
    parser.add_argument('--template', default="A {style} {scene_type} scene showing: {script_line}. With props: {props}.", help='Prompt template.')
    parser.add_argument('--image_format', default='base64', choices=['base64', 'url'], help='Format for image response: base64 (direct bytes) or url (download from URL).')
    parser.add_argument('--retry', type=int, default=3, help='Number of retries for failed generations.')
    parser.add_argument('--output_csv', default='generated_scenes.csv', help='Output CSV file when using script input mode.')

    args = parser.parse_args()

    # Validate arguments
    if not args.script_input and not args.input_file:
        parser.error("Either --input_file or --script_input must be provided.")

    # Prompt for API key if not provided
    if not args.api_key:
        args.api_key = getpass.getpass("Enter your xAI Grok API key: ")

    # Initialize client
    client = OpenAI(
        api_key=args.api_key,
        base_url="https://api.x.ai/v1"
    )

    # Handle script input mode
    if args.script_input:
        # Get script and style preference from user
        script = get_script_input()
        style_preference = get_style_preference()

        # Parse script with AI
        logger.info("Analyzing script with AI...")
        scenes = parse_script_with_ai(client, script, style_preference)

        # Add style preference to scenes for template use
        for scene in scenes:
            scene['style'] = style_preference

        # Write to CSV
        write_scenes_to_csv(scenes, args.output_csv)

        # Use the generated CSV as input
        args.input_file = args.output_csv
        logger.info(f"Generated {len(scenes)} scenes. Proceeding with image generation...")

    # Load scenes
    scenes = load_input_file(args.input_file)
    logger.info(f"Loaded {len(scenes)} scenes.")

    # Create output dir
    os.makedirs(args.output_dir, exist_ok=True)

    for scene in scenes:
        try:
            # Generate prompt
            prompt = generate_prompt(scene, args.template)
            logger.info(f"Generating image for scene {scene['scene_number']}: {prompt[:50]}...")

            # Generate image
            img_bytes = generate_image(client, prompt, args.image_format, args.retry)

            # Save image
            scene_num_str = f"{scene['scene_number']:03d}"
            output_path = os.path.join(args.output_dir, f"scene_{scene_num_str}.png")
            with open(output_path, 'wb') as f:
                f.write(img_bytes)
            logger.info(f"Saved {output_path}")

            # Optional: add delay to respect rate limits (300 rpm, but safe delay)
            time.sleep(0.2)

        except Exception as e:
            logger.error(f"Failed to generate scene {scene['scene_number']}: {str(e)}")

if __name__ == '__main__':
    main()
