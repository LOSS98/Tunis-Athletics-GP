import os
from datetime import datetime
from werkzeug.utils import secure_filename
from config import Config
import uuid


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def generate_filename(original_filename):
    ext = original_filename.rsplit('.', 1)[1].lower()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    random_string = str(uuid.uuid4())[:8]
    return f"{timestamp}_{random_string}.{ext}"


def save_uploaded_file(file, subfolder):
    if file and allowed_file(file.filename):
        filename = generate_filename(file.filename)
        if subfolder == 'athletes':
            filepath = os.path.join('static/images/athletes', filename)
        else:
            filepath = os.path.join(Config.UPLOAD_FOLDER, subfolder, filename)

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)
        return filename
    return None


def format_time(time_obj):
    if isinstance(time_obj, str):
        return time_obj
    return time_obj.strftime('%H:%M')


def get_status_badge_class(status):
    status_classes = {
        'scheduled': 'bg-blue-500',
        'in_progress': 'bg-yellow-500',
        'finished': 'bg-green-500',
        'cancelled': 'bg-red-500'
    }
    return status_classes.get(status, 'bg-gray-500')


def get_medal_icon(rank):
    if rank == '1':
        return '🥇'
    elif rank == '2':
        return '🥈'
    elif rank == '3':
        return '🥉'
    return ''