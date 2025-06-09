from flask import Blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin',
                    template_folder='../../templates/admin')
from .routes import register_routes
register_routes(admin_bp)
from . import auth
