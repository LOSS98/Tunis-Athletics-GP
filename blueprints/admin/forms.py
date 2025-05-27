from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, IntegerField, SelectField, TimeField, TextAreaField, BooleanField, \
    FieldList, FormField
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
    athlete_bib = IntegerField('Athlete BIB', validators=[DataRequired()])
    rank = StringField('Rank', validators=[Optional(), Length(max=10)])
    value = StringField('Performance Value', validators=[DataRequired(), Length(max=20)])
    record = SelectField('Record', choices=[('', 'None')] + [(r, r) for r in Config.RECORD_TYPES],
                         validators=[Optional()])
    attempts = FieldList(FormField(AttemptForm), min_entries=6, max_entries=6)

    def validate_value(self, field):
        """Validate performance value format based on event type"""
        if field.data in Config.RESULT_SPECIAL_VALUES:
            return

        # This validation will be done in the route based on event type
        pass


class StartListForm(FlaskForm):
    athlete_bib = IntegerField('Athlete BIB', validators=[DataRequired()])
    lane_order = IntegerField('Lane/Order', validators=[Optional(), NumberRange(min=1)])