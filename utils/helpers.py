import os
from datetime import datetime

from werkzeug.routing import ValidationError
from werkzeug.utils import secure_filename
from config import Config
from flask import current_app
import uuid
import pytz

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS
def generate_filename(original_filename):
    ext = original_filename.rsplit('.', 1)[1].lower()
    tunis_tz = pytz.timezone('Africa/Tunis')
    timestamp = datetime.now(tunis_tz).strftime('%Y%m%d_%H%M%S')
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
def check_flag_exists(npc_code, flag_file_path=None):
    if flag_file_path:
        if flag_file_path.startswith('static/'):
            full_path = os.path.join(current_app.static_folder, flag_file_path.replace('static/', ''))
        else:
            full_path = os.path.join(current_app.root_path, flag_file_path)
        return os.path.exists(full_path)
    else:
        standard_path = os.path.join(current_app.static_folder, 'images', 'flags', f"{npc_code.upper()}.svg")
        return os.path.exists(standard_path)
def get_flag_url(npc_code, flag_file_path=None):
    if flag_file_path and check_flag_exists(npc_code, flag_file_path):
        return f"/{flag_file_path}"
    elif check_flag_exists(npc_code):
        return f"/static/images/flags/{npc_code.upper()}.svg"
    else:
        return None
def validate_svg_file(form, field):
    if field.data:
        filename = field.data.filename
        if filename and not filename.lower().endswith('.svg'):
            raise ValidationError('Only SVG files are allowed!')
def get_pending_records_count():
    try:
        if not current_app:
            return 0
        from database.models.world_record import WorldRecord
        pending_records = WorldRecord.get_pending()
        return len(pending_records) if pending_records else 0
    except Exception as e:
        try:
            current_app.logger.warning(f"Error getting pending records count: {e}")
        except:
            print(f"Warning: Error getting pending records count: {e}")
        return 0
def get_pending_personal_bests_count():
    try:
        if not current_app:
            return 0
        from database.models.personal_best import PersonalBest
        pending_pbs = PersonalBest.get_pending()
        return len(pending_pbs) if pending_pbs else 0
    except Exception as e:
        try:
            current_app.logger.warning(f"Error getting pending personal bests count: {e}")
        except:
            print(f"Warning: Error getting pending personal bests count: {e}")
        return 0


def format_gender_display(gender_string):
    """Convert Male/Female to Men's/Women's for public display"""
    if not gender_string:
        return gender_string

    return gender_string.replace('Male', 'Men\'s').replace('Female', 'Women\'s')