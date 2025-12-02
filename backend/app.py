from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import tempfile
import json
import csv
from werkzeug.utils import secure_filename
import sys
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI

# Import functions from the main script
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from generateimages import process_script_programmatically, process_file_programmatically, load_input_file, parse_script_with_ai, generate_prompt, generate_image

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output_images')
ALLOWED_EXTENSIONS = {'csv', 'json'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Global progress tracking
progress_jobs = {}  # job_id -> {'status': 'parsing|generating|completed|error', 'current_scene': int, 'total_scenes': int, 'scenes': [], 'images': [], 'error': str}
executor = ThreadPoolExecutor(max_workers=1)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

@app.route('/api/generate-from-script', methods=['POST'])
def generate_from_script():
    try:
        data = request.get_json()

        if not data or 'api_key' not in data or 'script' not in data or 'style' not in data:
            return jsonify({'error': 'Missing required fields: api_key, script, style'}), 400

        api_key = data['api_key']
        script = data['script']
        style = data['style']

        # Process script programmatically
        scenes, images = process_script_programmatically(
            api_key=api_key,
            script=script,
            style_preference=style,
            output_dir=app.config['OUTPUT_FOLDER']
        )

        return jsonify({
            'scenes': scenes,
            'images': images,
            'output_dir': app.config['OUTPUT_FOLDER']
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-from-file', methods=['POST'])
def generate_from_file():
    try:
        if 'file' not in request.files or 'api_key' not in request.form:
            return jsonify({'error': 'Missing file or api_key'}), 400

        file = request.files['file']
        api_key = request.form['api_key']

        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file'}), 400

        # Save uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            # Process file programmatically
            images = process_file_programmatically(
                api_key=api_key,
                input_file=file_path,
                output_dir=app.config['OUTPUT_FOLDER']
            )

            return jsonify({
                'images': images,
                'output_dir': app.config['OUTPUT_FOLDER']
            })

        finally:
            # Clean up uploaded file
            if os.path.exists(file_path):
                os.unlink(file_path)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/images/<filename>', methods=['GET'])
def get_image(filename):
    try:
        image_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if not os.path.exists(image_path):
            return jsonify({'error': 'Image not found'}), 404

        return send_file(image_path, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file'}), 400

        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        return jsonify({'file_path': file_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-images', methods=['POST'])
def generate_images():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        api_key = data.get('api_key')
        style = data.get('style')
        script = data.get('script')
        file_path = data.get('file_path')

        if not api_key or not style or (not script and not file_path):
            return jsonify({'error': 'Missing required fields: api_key, style, and either script or file_path'}), 400

        job_id = str(uuid.uuid4())
        progress_jobs[job_id] = {
            'status': 'initializing',
            'current_scene': 0,
            'total_scenes': 0,
            'scenes': [],
            'images': [],
            'error': None
        }

        # Start async generation
        executor.submit(do_generate, job_id, api_key, style, script, file_path)

        return jsonify({'job_id': job_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def do_generate(job_id, api_key, style, script, file_path):
    import time
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

        progress_jobs[job_id]['status'] = 'parsing'

        if script:
            # Parse script to get scenes
            scenes = parse_script_with_ai(client, script, style)
            for scene in scenes:
                scene['style'] = style
        elif file_path:
            # Load scenes from file
            scenes = load_input_file(file_path)

        progress_jobs[job_id]['scenes'] = scenes
        progress_jobs[job_id]['total_scenes'] = len(scenes)
        progress_jobs[job_id]['status'] = 'generating'

        generated_images = []
        for i, scene in enumerate(scenes):
            progress_jobs[job_id]['current_scene'] = i + 1

            # Generate prompt and image
            prompt = generate_prompt(scene, "A {style} {scene_type} scene showing: {script_line}. With props: {props}.")
            img_bytes = generate_image(client, prompt, 'base64', 3)

            scene_num_str = f"{scene['scene_number']:03d}"
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"scene_{scene_num_str}.png")
            with open(output_path, 'wb') as f:
                f.write(img_bytes)

            generated_images.append(f"scene_{scene_num_str}.png")
            time.sleep(0.2)  # Rate limiting

        progress_jobs[job_id]['images'] = generated_images
        progress_jobs[job_id]['status'] = 'completed'

        # Clean up uploaded file if it was used
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)

    except Exception as e:
        progress_jobs[job_id]['status'] = 'error'
        progress_jobs[job_id]['error'] = str(e)

@app.route('/api/progress/<job_id>', methods=['GET'])
def get_progress(job_id):
    if job_id not in progress_jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = progress_jobs[job_id]
    return jsonify({
        'status': job['status'],
        'current_scene': job['current_scene'],
        'total_scenes': job['total_scenes'],
        'scenes': job['scenes'],
        'images': job['images'],
        'error': job['error']
    })

@app.route('/api/download-all', methods=['POST'])
def download_all():
    try:
        # This would create a ZIP file of all images
        # For now, return a placeholder
        return jsonify({'error': 'Download all functionality not implemented yet'}), 501
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
