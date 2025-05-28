from flask import render_template, redirect, url_for, flash, request
from ..auth import loc_required
from ..forms import UserForm
from database.models import User
from database.db_manager import execute_one

def register_routes(bp):
    @bp.route('/users')
    @loc_required
    def users_list():
        users = User.get_all()
        return render_template('admin/users/list.html', users=users)

    @bp.route('/users/create', methods=['GET', 'POST'])
    @loc_required
    def user_create():
        form = UserForm()
        if form.validate_on_submit():
            try:
                User.create(
                    form.username.data,
                    form.password.data,
                    form.admin_type.data
                )
                flash('User created successfully', 'success')
                return redirect(url_for('admin.users_list'))
            except Exception as e:
                flash(f'Error creating user: {str(e)}', 'danger')

        return render_template('admin/users/create.html', form=form)

    @bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
    @loc_required
    def user_edit(id):
        user = execute_one("SELECT * FROM users WHERE id = %s", (id,))
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('admin.users_list'))

        form = UserForm()
        if form.validate_on_submit():
            data = {'admin_type': form.admin_type.data}
            if form.password.data:
                data['password'] = form.password.data

            try:
                User.update(id, **data)
                flash('User updated successfully', 'success')
                return redirect(url_for('admin.users_list'))
            except Exception as e:
                flash(f'Error updating user: {str(e)}', 'danger')

        elif request.method == 'GET':
            form.username.data = user['username']
            form.admin_type.data = user.get('admin_type', 'volunteer')

        return render_template('admin/users/edit.html', form=form, user=user)

    @bp.route('/users/<int:id>/delete', methods=['POST'])
    @loc_required
    def user_delete(id):
        try:
            User.delete(id)
            flash('User deleted successfully', 'success')
        except Exception as e:
            flash(f'Error deleting user: {str(e)}', 'danger')

        return redirect(url_for('admin.users_list'))
