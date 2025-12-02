from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import tempfile
import json
import csv
from werkzeug.utils import secure_filename
import sys

# Import functions from the main script
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from generateimages import process_script_programmatically, process_file_programmatically

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
