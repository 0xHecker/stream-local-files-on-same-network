import re
import os
import io
import ffmpeg
from PIL import Image
from werkzeug.utils import secure_filename
from flask import Flask, render_template, send_file, jsonify,session, redirect, url_for, request, Response
from functools import wraps

PIN = "XXXXXX"  

app = Flask(__name__)

# Set the root directory to scan for files
ROOT_DIR = os.path.expanduser("/media/shanmukh/HDD/")  # This will use the user's home directory

def require_pin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@require_pin
def index():
    return render_template('index.html')

@app.route('/list')
@require_pin
def list_files():
    path = request.args.get('path')
    if not path:
        path = ROOT_DIR
    print(f"Listing files in directory: {path}")  # Debug print
    items = []
    for item in os.listdir(path):
        full_path = os.path.join(path, item)
        is_dir = os.path.isdir(full_path)
        items.append({
            'name': item,
            'is_dir': is_dir,
            'path': full_path,
            'type': get_file_type(item)
        })
    return jsonify(items)

def get_file_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.mp4', '.avi', '.mov', '.mkv']:
        return 'video'
    elif ext in ['.jpg', '.jpeg', '.png', '.gif']:
        return 'image'
    elif ext == '.pdf':
        return 'pdf'
    else:
        return 'other'

@app.route('/stream')
@require_pin
def stream_file():
    file_path = request.args.get('path')
    file_type = get_file_type(file_path)

    if file_type == 'video':
        return stream_video(file_path)
    elif file_type == 'image':
        return send_file(file_path, mimetype=f'image/{os.path.splitext(file_path)[1][1:]}')
    elif file_type == 'pdf':
        return send_file(file_path, mimetype='application/pdf')
    elif file_type == 'html':
        return send_file(file_path, mimetype='text/html')
    elif file_type == 'code':
        return send_file(file_path, mimetype='text/plain')
    else:
        return "Unsupported file type", 400

def stream_video(path):
    range_header = request.headers.get('Range', None)
    if not range_header:
        return send_file(path, mimetype='video/mp4')

    size = os.path.getsize(path)
    byte1, byte2 = 0, None

    if range_header:
        match = re.search(r'(\d+)-(\d*)', range_header)
        if match:
            groups = match.groups()
            byte1 = int(groups[0])
            if groups[1]:
                byte2 = int(groups[1])

    length = size - byte1
    if byte2 is not None:
        length = byte2 - byte1 + 1

    def generate():
        with open(path, 'rb') as f:
            f.seek(byte1)
            chunk = f.read(1024 * 1024)
            while chunk and (byte2 is None or f.tell() <= byte2):
                yield chunk
                chunk = f.read(1024 * 1024)

    rv = Response(generate(), 206, mimetype='video/mp4', content_type='video/mp4')
    rv.headers.add('Content-Range', f'bytes {byte1}-{byte1 + length - 1}/{size}')
    rv.headers.add('Accept-Ranges', 'bytes')
    rv.headers.add('Content-Length', str(length))
    return rv

@app.route('/get_adjacent_file')
@require_pin
def get_adjacent_file():
    current_path = request.args.get('path')
    direction = request.args.get('direction')  # 'next' or 'prev'
    parent_dir = os.path.dirname(current_path)
    
    files = [f for f in os.listdir(parent_dir) if os.path.isfile(os.path.join(parent_dir, f))]
    files.sort()
    
    current_index = files.index(os.path.basename(current_path))
    
    if direction == 'next':
        new_index = (current_index + 1) % len(files)
    else:  # prev
        new_index = (current_index - 1) % len(files)
    
    new_file = files[new_index]
    new_path = os.path.join(parent_dir, new_file)
    
    return jsonify({
        'path': new_path,
        'type': get_file_type(new_path)
    })

@app.route('/thumbnail')
@require_pin
def get_thumbnail():
    file_path = request.args.get('path')
    try:
        file_type = get_file_type(file_path)
        if file_type == 'image':
            return get_image_thumbnail(file_path)
        else:
            return send_file(DEFAULT_THUMBNAIL, mimetype='image/jpeg')
    except Exception as e:
        print(f"Error generating thumbnail: {str(e)}")
        return send_file(DEFAULT_THUMBNAIL, mimetype='image/jpeg')

def get_image_thumbnail(file_path):
    with Image.open(file_path) as img:
        img.thumbnail((200, 200))
        thumb_io = io.BytesIO()
        img.save(thumb_io, 'JPEG', quality=85)
        thumb_io.seek(0)
        return send_file(thumb_io, mimetype='image/jpeg')
        
def get_file_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']:
        return 'video'
    elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff']:
        return 'image'
    elif ext == '.pdf':
        return 'pdf'
    elif ext in ['.txt', '.py', '.js', '.css', '.json', '.md', '.xml', '.yml', '.yaml', '.sh']:
        return 'code'
    elif ext == '.html':
        return 'html'
    else:
        return 'other'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('pin') == PIN:
            session['authenticated'] = True
            return redirect(url_for('index'))
        else:
            return "Invalid PIN", 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('login'))

app.secret_key = '844555455cx4ty5455xt4t455t34@##@!@$%@#%$^R5$^&*(&*($@#**#$#@@SECRET_KEY#@$#%$EFSEF#'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
