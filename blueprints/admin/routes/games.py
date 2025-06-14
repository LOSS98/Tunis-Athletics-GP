import traceback
from datetime import datetime
import pytz
from flask import render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import current_user

from config import Config
from utils.pdf_generator import PDFGenerator
from ..auth import admin_required, loc_required, technical_delegate_required
from ..forms import GameForm, PDFUploadForm
from database.models import Game, Result, Attempt, StartList
from utils.helpers import save_uploaded_file
from PyPDF2 import PdfMerger
from werkzeug.utils import secure_filename
from database.db_manager import execute_query
import os

def register_routes(bp):
    @bp.route('/games')
    @admin_required
    def games_list():
        search = request.args.get('search', '')
        games = Game.get_with_status()
        if search:
            games = [g for g in games if
                    search.lower() in g['event'].lower() or
                    search.lower() in g['genders'].lower() or
                    search.lower() in g['classes'].lower() or
                    str(g['day']) in search]
        return render_template('admin/games/list.html', games=games, search=search)
    @bp.route('/games/<int:game_id>/wind-velocity', methods=['POST'])
    @admin_required
    def game_update_wind_velocity(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game:
                flash('Game not found', 'danger')
                return redirect(url_for('admin.games_list'))
            wind_velocity = request.form.get('wind_velocity', '').strip()
            if wind_velocity == '':
                flash('Wind velocity is required', 'danger')
                return redirect(url_for('admin.game_results', id=game_id))
            try:
                wind_velocity_float = float(wind_velocity)
            except ValueError:
                flash('Wind velocity must be a valid number', 'danger')
                return redirect(url_for('admin.game_results', id=game_id))
            if wind_velocity_float < -20.0 or wind_velocity_float > 20.0:
                flash('Wind velocity updated but too high !', 'danger')
            Game.update_velocity(game_id, wind_velocity_float)
            if wind_velocity_float > 2.0:
                flash(f'Wind velocity updated to +{wind_velocity_float} m/s (wind-assisted - records ineligible)',
                      'warning')
            elif wind_velocity_float < -2.0:
                flash(f'Wind velocity updated to {wind_velocity_float} m/s (strong headwind)', 'info')
            else:
                flash(f'Wind velocity updated to {wind_velocity_float} m/s', 'success')
            return redirect(url_for('admin.game_results', id=game_id))
        except Exception as e:
            print(f"Error updating wind velocity for game {game_id}: {e}")
            traceback.print_exc()
            flash(f'Error updating wind velocity: {str(e)}', 'danger')
            return redirect(url_for('admin.game_results', id=game_id))
    @bp.route('/games/<int:game_id>/remove-wind-velocity', methods=['POST'])
    @admin_required
    def game_remove_wind_velocity(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game:
                flash('Game not found', 'danger')
                return redirect(url_for('admin.games_list'))
            Game.update_velocity(game_id, 0)
            flash('Wind velocity measurement removed for this event', 'success')
            return redirect(url_for('admin.game_results', id=game_id))
        except Exception as e:
            print(f"Error removing wind velocity for game {game_id}: {e}")
            traceback.print_exc()
            flash(f'Error removing wind velocity: {str(e)}', 'danger')
            return redirect(url_for('admin.game_results', id=game_id))
    @bp.route('/games/create', methods=['GET', 'POST'])
    @admin_required
    def game_create():
        form = GameForm()
        if form.validate_on_submit():
            data = {
                'event': form.event.data,
                'genders': form.genders.data,
                'classes': form.classes.data,
                'phase': form.phase.data,
                'area': form.area.data,
                'day': form.day.data,
                'time': form.time.data,
                'nb_athletes': form.nb_athletes.data,
                'status': form.status.data,
                'published': form.published.data,
                'wpa_points': form.wpa_points.data
            }
            if form.photo_finish.data:
                filename = save_uploaded_file(form.photo_finish.data, 'photo_finish')
                if filename:
                    data['photo_finish'] = filename
            try:
                Game.create(**data)
                flash('Game created successfully', 'success')
                return redirect(url_for('admin.games_list'))
            except Exception as e:
                flash(f'Error creating game: {str(e)}', 'danger')
        return render_template('admin/games/create.html', form=form)
    @bp.route('/games/<int:id>/edit', methods=['GET', 'POST'])
    @admin_required
    def game_edit(id):
        game = Game.get_by_id(id)
        if not game:
            if request.method == 'POST':
                return {'error': 'Game not found'}, 404
            else:
                flash('Game not found', 'danger')
                return redirect(url_for('admin.games_list'))
        if request.method == 'POST':
            try:
                data = {
                    'event': request.form.get('event'),
                    'genders': request.form.get('genders'),
                    'classes': request.form.get('classes'),
                    'phase': request.form.get('phase') if request.form.get('phase') else None,
                    'area': request.form.get('area') if request.form.get('area') else None,
                    'day': int(request.form.get('day')),
                    'time': request.form.get('time'),
                    'nb_athletes': int(request.form.get('nb_athletes')),
                    'status': request.form.get('status'),
                    'published': bool(request.form.get('published')),
                    'wpa_points': bool(request.form.get('wpa_points'))
                }
                Game.update(id, **data)
                if request.headers.get('Content-Type', '').startswith('multipart/form-data'):
                    flash('Game updated successfully', 'success')
                    return redirect(url_for('admin.games_list'))
                else:
                    return '', 200
            except Exception as e:
                if request.headers.get('Content-Type', '').startswith('multipart/form-data'):
                    flash(f'Error updating game: {str(e)}', 'danger')
                    return redirect(url_for('admin.games_list'))
                else:
                    return {'error': str(e)}, 500
        # GET request - show edit form
        from ..forms import GameForm
        form = GameForm()
        # Pre-populate form
        form.event.data = game['event']
        form.genders.data = game['genders']
        form.classes.data = game['classes']
        form.phase.data = game.get('phase')
        form.area.data = game.get('area')
        form.day.data = game['day']
        form.time.data = game['time']
        form.nb_athletes.data = game['nb_athletes']
        form.status.data = game['status']
        form.published.data = game.get('published', False)
        form.wpa_points.data = game.get('wpa_points', False)
        return render_template('admin/games/edit.html', form=form, game=game)
    @bp.route('/games/<int:id>/delete', methods=['POST'])
    @admin_required
    def game_delete(id):
        try:
            Game.delete(id)
            flash('Game deleted successfully', 'success')
        except Exception as e:
            flash(f'Error deleting game: {str(e)}', 'danger')
        return redirect(url_for('admin.games_list'))
    @bp.route('/games/<int:id>/status', methods=['POST'])
    @admin_required
    def game_update_status(id):
        status = request.form.get('status')
        valid_statuses = ['scheduled', 'delayed', 'started', 'in_progress', 'finished', 'cancelled']
        if status not in valid_statuses:
            return jsonify({'error': 'Invalid status'}), 400
        try:
            Game.update_status(id, status)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    @bp.route('/games/<int:id>/auto-rank', methods=['POST'])
    @admin_required
    def game_auto_rank(id):
        try:
            game = Game.get_by_id(id)
            if not game:
                return jsonify({'error': 'Game not found'}), 404
            success = Result.auto_rank_results(id)
            if success:
                return jsonify({'success': True})
            else:
                return jsonify({'error': 'Failed to auto-rank results'}), 500
        except Exception as e:
            print(f"Error in auto-rank: {e}")
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
    @bp.route('/games/<int:id>/publish', methods=['POST'])
    @loc_required
    def game_toggle_publish(id):
        try:
            new_status = Game.toggle_publish(id)
            return jsonify({'published': new_status})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/games/<int:game_id>/generate-pdf')
    @admin_required
    def generate_game_pdf(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game:
                flash('Game not found', 'danger')
                return redirect(url_for('admin.games_list'))

            game['classes_list'] = [c.strip() for c in game['classes'].split(',') if c.strip()]
            results = Result.get_all(game_id=game_id)

            # Charger les tentatives pour les épreuves de terrain
            if game['event'] in Config.get_field_events():
                for result in results:
                    result['attempts'] = Attempt.get_by_result(result['id'])

            # Check for heat group data
            heat_group = None
            combined_results = None

            if Game.is_heat_game(game):
                from database.models.heat_group import HeatGroup
                heat_group = HeatGroup.get_by_id(game['heat_group_id'])
                combined_results = HeatGroup.get_combined_results(game['heat_group_id'])
                for i, result in enumerate(combined_results):
                    result['final_rank'] = i + 1

            generator = PDFGenerator()
            pdf_buffer = generator.generate_results_pdf(game, results, heat_group, combined_results)

            # Generate filename
            gender_short = 'M' if game['genders'] == 'Male' else 'W'
            filename = f"Results_{gender_short}_{game['event'].replace(' ', '_')}_{game['classes']}_{game['day']}.pdf"

            return send_file(
                pdf_buffer,
                as_attachment=False,
                download_name=filename,
                mimetype='application/pdf'
            )

        except Exception as e:
            print(f"Error generating PDF: {e}")
            flash(f'Error generating PDF: {str(e)}', 'danger')
            return redirect(url_for('admin.game_results', id=game_id))

    @bp.route('/games/<int:game_id>/generate-startlist-pdf')
    @admin_required
    def generate_startlist_pdf(game_id):
        """Generate and save start list PDF"""
        try:
            game = Game.get_by_id(game_id)
            if not game:
                flash('Game not found', 'danger')
                return redirect(url_for('admin.games_list'))

            startlist = StartList.get_by_game(game_id)
            if not startlist:
                flash('No start list found for this game', 'warning')
                return redirect(url_for('admin.game_startlist', id=game_id))

            # Generate PDF
            pdf_generator = PDFGenerator()
            pdf_buffer = pdf_generator.generate_startlist_pdf(game, startlist)

            # Save to file
            filename = f"startlist_game_{game_id}_{game['event'].replace(' ', '_')}.pdf"
            filepath = os.path.join('static', 'generated_pdfs', 'startlists', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            with open(filepath, 'wb') as f:
                f.write(pdf_buffer.getvalue())

            # Update database
            Game.update_generated_pdfs(game_id, startlist_pdf=filename)

            flash('Start list PDF generated successfully', 'success')
            return send_file(filepath, as_attachment=True, download_name=filename)

        except Exception as e:
            print(f"Error generating start list PDF: {e}")
            flash(f'Error generating PDF: {str(e)}', 'danger')
            return redirect(url_for('admin.game_startlist', id=game_id))

    @bp.route('/games/<int:game_id>/generate-results-pdf')
    @admin_required
    def generate_results_pdf(game_id):
        """Generate and save results PDF"""
        try:
            game = Game.get_by_id(game_id)
            if not game:
                flash('Game not found', 'danger')
                return redirect(url_for('admin.games_list'))

            results = Result.get_all(game_id=game_id)
            if not results:
                flash('No results found for this game', 'warning')
                return redirect(url_for('admin.game_results', id=game_id))

            # Generate PDF
            pdf_generator = PDFGenerator()
            pdf_buffer = pdf_generator.generate_results_pdf(game, results)

            # Save to file
            filename = f"results_game_{game_id}_{game['event'].replace(' ', '_')}.pdf"
            filepath = os.path.join('static', 'generated_pdfs', 'results', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            with open(filepath, 'wb') as f:
                f.write(pdf_buffer.getvalue())

            # Update database
            Game.update_generated_pdfs(game_id, results_pdf=filename)

            flash('Results PDF generated successfully', 'success')
            return send_file(filepath, as_attachment=True, download_name=filename)

        except Exception as e:
            print(f"Error generating results PDF: {e}")
            flash(f'Error generating PDF: {str(e)}', 'danger')
            return redirect(url_for('admin.game_results', id=game_id))

    @bp.route('/games/<int:game_id>/view-startlist-pdf')
    @admin_required
    def view_startlist_pdf(game_id):
        """View start list PDF"""
        try:
            game = Game.get_by_id(game_id)
            if not game:
                flash('Game not found', 'danger')
                return redirect(url_for('admin.games_list'))

            # Check for manual PDF first, then generated
            pdf_filename = game.get('manual_startlist_pdf') or game.get('generated_startlist_pdf')

            if not pdf_filename:
                flash('No start list PDF found', 'warning')
                return redirect(url_for('admin.game_results', id=game_id))

            # Determine file path
            if game.get('manual_startlist_pdf'):
                filepath = os.path.join('static', 'manual_pdfs', 'startlists', pdf_filename)
            else:
                filepath = os.path.join('static', 'generated_pdfs', 'startlists', pdf_filename)

            if not os.path.exists(filepath):
                flash('PDF file not found on disk', 'danger')
                return redirect(url_for('admin.game_results', id=game_id))

            return send_file(filepath, as_attachment=False, mimetype='application/pdf')

        except Exception as e:
            print(f"Error viewing start list PDF: {e}")
            flash('Error viewing PDF', 'danger')
            return redirect(url_for('admin.game_results', id=game_id))

    @bp.route('/games/<int:game_id>/view-results-pdf')
    @admin_required
    def view_results_pdf(game_id):
        """View results PDF"""
        try:
            game = Game.get_by_id(game_id)
            if not game:
                flash('Game not found', 'danger')
                return redirect(url_for('admin.games_list'))

            # Check for manual PDF first, then generated
            pdf_filename = game.get('manual_results_pdf') or game.get('generated_results_pdf')

            if not pdf_filename:
                flash('No results PDF found', 'warning')
                return redirect(url_for('admin.game_results', id=game_id))

            # Determine file path
            if game.get('manual_results_pdf'):
                filepath = os.path.join('static', 'manual_pdfs', 'results', pdf_filename)
            else:
                filepath = os.path.join('static', 'generated_pdfs', 'results', pdf_filename)

            if not os.path.exists(filepath):
                flash('PDF file not found on disk', 'danger')
                return redirect(url_for('admin.game_results', id=game_id))

            return send_file(filepath, as_attachment=False, mimetype='application/pdf')

        except Exception as e:
            print(f"Error viewing results PDF: {e}")
            flash('Error viewing PDF', 'danger')
            return redirect(url_for('admin.game_results', id=game_id))

    @bp.route('/games/<int:game_id>/publish-auto-pdfs', methods=['POST'])
    @admin_required
    def publish_auto_pdfs(game_id):
        """Generate and publish specific PDF type"""
        try:
            game = Game.get_by_id(game_id)
            if not game:
                return jsonify({'error': 'Game not found'}), 404

            data = request.get_json()
            pdf_type = data.get('type')  # 'startlist' or 'results'

            if pdf_type == 'startlist':
                # Generate start list PDF
                startlist = StartList.get_by_game(game_id)
                if not startlist:
                    return jsonify({'error': 'No start list found'}), 400

                pdf_generator = PDFGenerator()
                pdf_buffer = pdf_generator.generate_startlist_pdf(game, startlist)

                filename = f"startlist_game_{game_id}_{game['event'].replace(' ', '_')}.pdf"
                filepath = os.path.join('static', 'generated_pdfs', 'startlists', filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)

                with open(filepath, 'wb') as f:
                    f.write(pdf_buffer.getvalue())

                Game.update_generated_pdfs(game_id, startlist_pdf=filename)
                return jsonify({'success': True, 'message': 'Start list PDF generated and published'})

            elif pdf_type == 'results':
                # Generate results PDF
                results = Result.get_all(game_id=game_id)
                if not results:
                    return jsonify({'error': 'No results found'}), 400

                # Load attempts for field events
                if game['event'] in Config.get_field_events():
                    for result in results:
                        result['attempts'] = Attempt.get_by_result(result['id'])

                # Check for heat group data
                heat_group = None
                combined_results = None
                if Game.is_heat_game(game):
                    from database.models.heat_group import HeatGroup
                    heat_group = HeatGroup.get_by_id(game['heat_group_id'])
                    combined_results = HeatGroup.get_combined_results(game['heat_group_id'])
                    for i, result in enumerate(combined_results):
                        result['final_rank'] = i + 1

                pdf_generator = PDFGenerator()
                pdf_buffer = pdf_generator.generate_results_pdf(game, results, heat_group, combined_results)

                filename = f"results_game_{game_id}_{game['event'].replace(' ', '_')}.pdf"
                filepath = os.path.join('static', 'generated_pdfs', 'results', filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)

                with open(filepath, 'wb') as f:
                    f.write(pdf_buffer.getvalue())

                Game.update_generated_pdfs(game_id, results_pdf=filename)
                return jsonify({'success': True, 'message': 'Results PDF generated and published'})

            else:
                return jsonify({'error': 'Invalid PDF type'}), 400

        except Exception as e:
            print(f"Error publishing auto PDFs: {e}")
            return jsonify({'error': str(e)}), 500

    @bp.route('/games/<int:game_id>/upload-pdfs', methods=['GET', 'POST'])
    @admin_required
    def upload_game_pdfs(game_id):
        """Upload and overwrite PDFs"""
        game = Game.get_by_id(game_id)
        if not game:
            flash('Game not found', 'danger')
            return redirect(url_for('admin.games_list'))

        form = PDFUploadForm()

        if form.validate_on_submit():
            try:
                uploaded_files = {}

                # Handle startlist PDF
                if form.startlist_pdf.data:
                    filename = secure_filename(f"manual_startlist_game_{game_id}.pdf")
                    filepath = os.path.join('static', 'manual_pdfs', 'startlists', filename)
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    form.startlist_pdf.data.save(filepath)
                    uploaded_files['startlist_pdf'] = filename

                # Handle results PDF
                if form.results_pdf.data:
                    filename = secure_filename(f"manual_results_game_{game_id}.pdf")
                    filepath = os.path.join('static', 'manual_pdfs', 'results', filename)
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    form.results_pdf.data.save(filepath)
                    uploaded_files['results_pdf'] = filename

                if uploaded_files:
                    Game.update_manual_pdfs(game_id, **uploaded_files)
                    flash('PDFs uploaded successfully', 'success')
                else:
                    flash('No files selected', 'warning')

            except Exception as e:
                flash(f'Error uploading PDFs: {str(e)}', 'danger')

            return redirect(url_for('admin.game_results', id=game_id))

        return render_template('admin/games/upload_pdfs.html', form=form, game=game)

    @bp.route('/bulk-generate-pdfs', methods=['POST'])
    @admin_required
    def bulk_generate_pdfs():
        """Generate all missing PDFs"""
        try:
            pdf_type = request.json.get('type', 'both')  # 'startlists', 'results', or 'both'

            games = Game.get_games_for_bulk_generation()
            generated_count = 0

            for game in games:
                game_id = game['id']

                if pdf_type in ['startlists', 'both']:
                    startlist = StartList.get_by_game(game_id)
                    if startlist:
                        pdf_generator = PDFGenerator()
                        pdf_buffer = pdf_generator.generate_startlist_pdf(game, startlist)

                        filename = f"startlist_game_{game_id}_{game['event'].replace(' ', '_')}.pdf"
                        filepath = os.path.join('static', 'generated_pdfs', 'startlists', filename)
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)

                        with open(filepath, 'wb') as f:
                            f.write(pdf_buffer.getvalue())

                        Game.update_generated_pdfs(game_id, startlist_pdf=filename)
                        generated_count += 1

                if pdf_type in ['results', 'both']:
                    results = Result.get_all(game_id=game_id)
                    if results:
                        pdf_generator = PDFGenerator()
                        pdf_buffer = pdf_generator.generate_results_pdf(game, results)

                        filename = f"results_game_{game_id}_{game['event'].replace(' ', '_')}.pdf"
                        filepath = os.path.join('static', 'generated_pdfs', 'results', filename)
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)

                        with open(filepath, 'wb') as f:
                            f.write(pdf_buffer.getvalue())

                        Game.update_generated_pdfs(game_id, results_pdf=filename)
                        generated_count += 1

            return jsonify({
                'success': True,
                'message': f'{generated_count} PDFs generated successfully'
            })

        except Exception as e:
            print(f"Error in bulk PDF generation: {e}")
            return jsonify({'error': str(e)}), 500

    @bp.route('/download-all-pdfs/<pdf_type>')
    @admin_required
    def download_all_pdfs(pdf_type):
        """Download all PDFs merged into one file"""
        try:
            if pdf_type not in ['startlists', 'results']:
                flash('Invalid PDF type', 'danger')
                return redirect(url_for('admin.games_list'))

            games = Game.get_games_with_pdfs()
            merger = PdfMerger()

            pdf_files = []
            for game in games:
                # Check for manual PDF first, then generated
                if pdf_type == 'startlists':
                    filename = game.get('manual_startlist_pdf') or game.get('generated_startlist_pdf')
                    if filename:
                        if game.get('manual_startlist_pdf'):
                            filepath = os.path.join('static', 'manual_pdfs', 'startlists', filename)
                        else:
                            filepath = os.path.join('static', 'generated_pdfs', 'startlists', filename)
                else:  # results
                    filename = game.get('manual_results_pdf') or game.get('generated_results_pdf')
                    if filename:
                        if game.get('manual_results_pdf'):
                            filepath = os.path.join('static', 'manual_pdfs', 'results', filename)
                        else:
                            filepath = os.path.join('static', 'generated_pdfs', 'results', filename)

                if filename and os.path.exists(filepath):
                    pdf_files.append(filepath)

            if not pdf_files:
                flash(f'No {pdf_type} PDFs found', 'warning')
                return redirect(url_for('admin.games_list'))

            # Sort by game day and time
            pdf_files.sort()

            for pdf_file in pdf_files:
                merger.append(pdf_file)

            # Save merged file
            merged_filename = f"all_{pdf_type}_tunis_gp_2025.pdf"
            merged_filepath = os.path.join('static', 'merged_pdfs', merged_filename)
            os.makedirs(os.path.dirname(merged_filepath), exist_ok=True)

            with open(merged_filepath, 'wb') as f:
                merger.write(f)
            merger.close()

            return send_file(merged_filepath, as_attachment=True, download_name=merged_filename)

        except Exception as e:
            print(f"Error merging PDFs: {e}")
            flash(f'Error merging PDFs: {str(e)}', 'danger')
            return redirect(url_for('admin.games_list'))

    @bp.route('/games/<int:game_id>/add-to-startlist', methods=['POST'])
    @admin_required
    def add_athlete_to_startlist_from_results(game_id):
        """Add athlete to start list from results page"""
        try:
            athlete_sdms = request.json.get('athlete_sdms')
            guide_sdms = request.json.get('guide_sdms')

            if not athlete_sdms:
                return jsonify({'error': 'Athlete SDMS required'}), 400

            # Check if already in start list
            existing = StartList.athlete_in_startlist(game_id, athlete_sdms)
            if existing:
                return jsonify({'error': 'Athlete already in start list'}), 400

            # Add to start list
            StartList.create(game_id, athlete_sdms, None, guide_sdms)

            return jsonify({
                'success': True,
                'message': 'Athlete added to start list successfully'
            })

        except Exception as e:
            print(f"Error adding athlete to start list: {e}")
            return jsonify({'error': str(e)}), 500

    @bp.route('/games/<int:game_id>/delete-startlist-pdf', methods=['POST'])
    @admin_required
    def delete_startlist_pdf(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game:
                return jsonify({'error': 'Game not found'}), 404

            deleted_files = []

            if game.get('manual_startlist_pdf'):
                filepath = os.path.join('static', 'manual_pdfs', 'startlists', game['manual_startlist_pdf'])
                if os.path.exists(filepath):
                    os.remove(filepath)
                    deleted_files.append('manual')

            if game.get('generated_startlist_pdf'):
                filepath = os.path.join('static', 'generated_pdfs', 'startlists', game['generated_startlist_pdf'])
                if os.path.exists(filepath):
                    os.remove(filepath)
                    deleted_files.append('generated')

            # Clear database references
            execute_query("""
                UPDATE games 
                SET manual_startlist_pdf = NULL, generated_startlist_pdf = NULL 
                WHERE id = %s
            """, (game_id,))

            return jsonify({
                'success': True,
                'message': f'Start list PDF deleted successfully ({", ".join(deleted_files) if deleted_files else "no files found"})'
            })

        except Exception as e:
            print(f"Error deleting start list PDF: {e}")
            return jsonify({'error': str(e)}), 500

    @bp.route('/games/<int:game_id>/delete-results-pdf', methods=['POST'])
    @admin_required
    def delete_results_pdf(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game:
                return jsonify({'error': 'Game not found'}), 404

            deleted_files = []

            if game.get('manual_results_pdf'):
                filepath = os.path.join('static', 'manual_pdfs', 'results', game['manual_results_pdf'])
                if os.path.exists(filepath):
                    os.remove(filepath)
                    deleted_files.append('manual')

            if game.get('generated_results_pdf'):
                filepath = os.path.join('static', 'generated_pdfs', 'results', game['generated_results_pdf'])
                if os.path.exists(filepath):
                    os.remove(filepath)
                    deleted_files.append('generated')

            # Clear database references
            execute_query("""
                UPDATE games 
                SET manual_results_pdf = NULL, generated_results_pdf = NULL 
                WHERE id = %s
            """, (game_id,))

            return jsonify({
                'success': True,
                'message': f'Results PDF deleted successfully ({", ".join(deleted_files) if deleted_files else "no files found"})'
            })

        except Exception as e:
            print(f"Error deleting results PDF: {e}")
            return jsonify({'error': str(e)}), 500

    @bp.route('/games/<int:id>/toggle-publish-startlist', methods=['POST'])
    @technical_delegate_required
    def toggle_publish_startlist(id):
        new_status = Game.toggle_publish_startlist(id)
        status_text = 'published' if new_status else 'unpublished'
        flash(f'Startlist {status_text} successfully', 'success')
        return redirect(url_for('admin.game_startlist', id=id))

    @bp.route('/games/<int:game_id>/toggle-corrected', methods=['POST'])
    @technical_delegate_required
    def toggle_game_corrected(game_id):
        try:
            new_status = Game.toggle_corrected_status(game_id, current_user.id)
            if new_status:
                message = 'Game marked as CORRECTED'
            else:
                message = 'Game correction status removed'

            tunis_tz = pytz.timezone('Africa/Tunis')

            return jsonify({
                'success': True,
                'message': message,
                'corrected': new_status,
                'corrected_by': current_user.username if new_status else None,
                'corrected_date': datetime.now(tunis_tz).strftime('%Y-%m-%d %H:%M:%S') if new_status else None
            })
        except Exception as e:
            print(f"Error toggling game corrected status: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500