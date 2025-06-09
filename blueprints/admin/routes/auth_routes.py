from flask import render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from ..auth import admin_required
from ..forms import LoginForm
from database.models import User
def register_routes(bp):
    @bp.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('admin.dashboard'))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.verify_password(form.username.data, form.password.data)
            if user:
                login_user(user)
                return redirect(url_for('admin.dashboard'))
            flash('Invalid username or password', 'danger')
        return render_template('admin/login.html', form=form)
    @bp.route('/logout')
    @admin_required
    def logout():
        logout_user()
        return redirect(url_for('public.index'))
    @bp.route('/setup', methods=['GET'])
    def setup():
        from config import Config
        admin = User.get_by_username(Config.ADMIN_USERNAME)
        if not admin:
            User.create(Config.ADMIN_USERNAME, Config.ADMIN_PASSWORD, 'loc')
            flash('Admin user created successfully', 'success')
        else:
            flash('Admin user already exists', 'info')
        return redirect(url_for('admin.login'))
