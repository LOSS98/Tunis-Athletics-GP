from flask import Blueprint
public_bp = Blueprint('public', __name__, template_folder='../../templates/public')
from .routes import register_routes
register_routes(public_bp)
