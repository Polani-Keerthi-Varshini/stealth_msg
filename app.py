from flask import Flask, request, jsonify, render_template, url_for
from PIL import Image
import numpy as np
import base64
import io
import uuid
import os

app = Flask(__name__, static_folder='static')
app.config['UPLOAD_FOLDER'] = 'static/encoded_images'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def compress_image(image, max_size=(800, 800)):
    """Compress image while maintaining aspect ratio"""
    img_copy = image.copy()
    img_copy.thumbnail(max_size, Image.Resampling.LANCZOS)
    return img_copy

def encode_message(image, message):
    # Compress image first
    compressed_image = compress_image(image)
    
    # Convert image to numpy array
    img_array = np.array(compressed_image)
    
    # Convert message to binary
    binary_message = ''.join(format(ord(char), '08b') for char in message)
    binary_message += '00000000'  # Add delimiter
    
    if len(binary_message) > img_array.size:
        raise ValueError("Message too long for this image")
    
    # Create a copy of the image array
    encoded_array = img_array.copy()
    flat_encoded = encoded_array.flatten()
    
    # Encode the message
    for i, bit in enumerate(binary_message):
        flat_encoded[i] = (flat_encoded[i] & 0xFE) | int(bit)
    
    # Reshape back to original dimensions
    encoded_array = flat_encoded.reshape(img_array.shape)
    
    return Image.fromarray(encoded_array.astype(np.uint8))

def decode_message(image):
    img_array = np.array(image)
    binary_message = ''
    flat_img = img_array.flatten()
    
    for i in range(len(flat_img)):
        binary_message += str(flat_img[i] & 1)
        if len(binary_message) % 8 == 0:
            byte = binary_message[-8:]
            if byte == '00000000':
                binary_message = binary_message[:-8]
                break
    
    message = ''
    for i in range(0, len(binary_message), 8):
        byte = binary_message[i:i+8]
        message += chr(int(byte, 2))
    
    return message

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/encode', methods=['POST'])
def encode():
    try:
        image_file = request.files['image']
        message = request.form['message']
        
        # Open and process image
        image = Image.open(image_file).convert('RGB')
        
        # Encode the message
        encoded_image = encode_message(image, message)
        
        # Save image with unique filename
        filename = f"encoded_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        encoded_image.save(filepath, 'PNG', optimize=True)
        
        # Get public URL for the image
        image_url = url_for('static', filename=f'encoded_images/{filename}', _external=True)
        
        # Create base64 for preview
        buffered = io.BytesIO()
        encoded_image.save(buffered, format="PNG", optimize=True)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return jsonify({
            'status': 'success',
            'image': img_str,
            'share_url': image_url  # Shareable link for social media sharing
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400



@app.route('/decode', methods=['POST'])
def decode():
    try:
        image_file = request.files['image']
        image = Image.open(image_file).convert('RGB')
        message = decode_message(image)
        
        if not message:
            raise ValueError("No hidden message found")
        
        return jsonify({
            'status': 'success',
            'message': message
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

if __name__ == '__main__':
    app.run(debug=True)
