# Script to Images Generator

Automatically generate images from video scripts using xAI Grok API.

## Features

- **Script Input Mode**: Input a full storyline/script and let AI automatically break it into scenes
- **Style Selection**: Choose from various image styles (photorealistic, animated, 3D, cartoon, etc.)
- **CSV/JSON Support**: Load structured scene data from files
- **AI Script Parsing**: Uses Grok API to intelligently analyze scripts and extract scenes, props, and scene types
- **Batch Image Generation**: Generate multiple images with sequential naming
- **Error Handling**: Built-in retries and comprehensive logging
- **Multiple Formats**: Support for both base64 and URL image responses

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Script Input Mode (New!)

```bash
python generateimages.py --script_input
```

This mode will:
1. Prompt you to enter your API key
2. Ask for your full storyline/script
3. Let you choose an image style
4. Use AI to parse the script into structured scenes
5. Generate a CSV file automatically
6. Generate images for each scene

### CSV File Mode

```bash
python generateimages.py --input_file sample_scenes.csv
```

### Command Line Options

- `--input_file`: Path to CSV or JSON input file
- `--script_input`: Enable script input mode
- `--api_key`: xAI Grok API key (prompts securely if not provided)
- `--output_dir`: Directory for generated images (default: 'output_images')
- `--template`: Prompt template (default: "A {style} {scene_type} scene showing: {script_line}. With props: {props}.")
- `--image_format`: Image format ('base64' or 'url', default: 'base64')
- `--retry`: Number of retries for failed generations (default: 3)
- `--output_csv`: Output CSV file for script input mode (default: 'generated_scenes.csv')

## Input Formats

### CSV Format
```csv
scene_number,script_line,scene_type,props
1,"Character enters the room excitedly","animated","coin,card"
2,"Character picks up the phone","static","phone"
3,"Character flips a card on the table","animated","card,tracker"
```

### JSON Format
```json
[
  {
    "scene_number": 1,
    "script_line": "Character enters the room excitedly",
    "scene_type": "animated",
    "props": ["coin", "card"]
  }
]
```

## Output

- Images saved as `scene_001.png`, `scene_002.png`, etc.
- Generated CSV file (when using script input mode)
- Comprehensive logging of the generation process

## Style Options

When using script input mode, choose from:
1. photorealistic
2. animated
3. 3D animation
4. cartoon
5. digital art
6. cinematic
7. sketch/artistic

Or type a custom style preference.

## API Requirements

- xAI Grok API key
- Models used:
  - `grok-beta` for script parsing
  - `grok-2-image` for image generation

## Error Handling

- Automatic retries for failed API calls
- Exponential backoff for rate limiting
- Detailed logging for troubleshooting
- Graceful handling of API errors

## Examples

### Generate from existing CSV
```bash
python generateimages.py --input_file my_scenes.csv --api_key your_api_key_here
```

### Interactive script input
```bash
python generateimages.py --script_input
```

### Custom template and output directory
```bash
python generateimages.py --script_input --template "Create a {style} image of: {script_line}" --output_dir my_images
