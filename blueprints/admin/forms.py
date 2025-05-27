from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, IntegerField, SelectField, TimeField, TextAreaField, BooleanField, \
    FieldList, FormField, HiddenField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError
from config import Config
import re


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField('Password', validators=[Optional(), Length(min=6)])
    admin_type = SelectField('Admin Type', choices=[('volunteer', 'Volunteer'), ('loc', 'LOC')],
                             validators=[DataRequired()])


class AthleteForm(FlaskForm):
    bib = IntegerField('BIB Number', validators=[DataRequired(), NumberRange(min=1)])
    firstname = StringField('First Name', validators=[DataRequired(), Length(max=100)])
    lastname = StringField('Last Name', validators=[DataRequired(), Length(max=100)])
    country = StringField('Country Code', validators=[DataRequired(), Length(min=3, max=3)])
    gender = SelectField('Gender', choices=[(g, g) for g in Config.GENDERS], validators=[DataRequired()])
    athlete_class = SelectField('Class', choices=[(c, c) for c in Config.CLASSES], validators=[DataRequired()])
    photo = FileField('Photo', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'])])


class GameForm(FlaskForm):
    event = SelectField('Event', validators=[DataRequired()])
    gender = SelectField('Gender', choices=[(g, g) for g in Config.GENDERS], validators=[DataRequired()])
    classes = StringField('Classes (comma separated)', validators=[DataRequired(), Length(max=200)])
    phase = StringField('Phase', validators=[Optional(), Length(max=50)])
    area = StringField('Area', validators=[Optional(), Length(max=50)])
    day = IntegerField('Day', validators=[DataRequired(), NumberRange(min=1, max=8)])
    time = TimeField('Time', validators=[DataRequired()])
    nb_athletes = IntegerField('Number of Athletes', validators=[DataRequired(), NumberRange(min=1)])
    status = SelectField('Status', choices=[
        ('scheduled', 'Scheduled'),
        ('started', 'Started'),
        ('in_progress', 'In Progress'),
        ('finished', 'Finished'),
        ('cancelled', 'Cancelled')
    ], validators=[DataRequired()])
    published = BooleanField('Published')
    start_file = FileField('Start List File', validators=[FileAllowed(['pdf', 'txt'])])
    result_file = FileField('Results File', validators=[FileAllowed(['pdf', 'txt'])])

    def __init__(self, *args, **kwargs):
        super(GameForm, self).__init__(*args, **kwargs)
        all_events = Config.FIELD_EVENTS + Config.TRACK_EVENTS
        self.event.choices = [(e, e) for e in all_events]

    def validate_classes(self, field):
        """Validate that all classes are valid"""
        if field.data:
            classes = [c.strip() for c in field.data.split(',')]
            for cls in classes:
                if cls not in Config.CLASSES:
                    raise ValidationError(f'Invalid class: {cls}')


class AttemptForm(FlaskForm):
    value = StringField('Value', validators=[Optional()])


class ResultForm(FlaskForm):
    # Correction: athlete_bib doit être IntegerField pour validation
    athlete_bib = IntegerField('Athlete BIB', validators=[DataRequired(message="Please select an athlete")])
    rank = StringField('Rank', validators=[Optional(), Length(max=10)])
    value = StringField('Performance Value',
                        validators=[DataRequired(message="Performance value is required"), Length(max=20)])
    record = SelectField('Record', choices=[('', 'None')] + [(r, r) for r in Config.RECORD_TYPES],
                         validators=[Optional()])

    # Champs pour les tentatives (field events)
    attempt_1 = StringField('Attempt 1', validators=[Optional()])
    attempt_2 = StringField('Attempt 2', validators=[Optional()])
    attempt_3 = StringField('Attempt 3', validators=[Optional()])
    attempt_4 = StringField('Attempt 4', validators=[Optional()])
    attempt_5 = StringField('Attempt 5', validators=[Optional()])
    attempt_6 = StringField('Attempt 6', validators=[Optional()])

    def validate_value(self, field):
        """Validate performance value format"""
        if field.data in Config.RESULT_SPECIAL_VALUES:
            return True

        # La validation sera faite côté serveur selon le type d'événement
        return True


class StartListForm(FlaskForm):
    athlete_bib = IntegerField('Athlete BIB', validators=[DataRequired()])
    lane_order = IntegerField('Lane/Order', validators=[Optional(), NumberRange(min=1)])