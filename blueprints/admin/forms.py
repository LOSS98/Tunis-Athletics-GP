from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, IntegerField, SelectField, TimeField, TextAreaField, BooleanField, \
    FieldList, FormField, HiddenField
from wtforms.fields.datetime import DateField
from wtforms.fields.numeric import DecimalField, FloatField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError
import re
def get_config_choices(key, default_choices=None):
    try:
        from database.config_manager import get_cached_config
        return get_cached_config(key, default_choices or [])
    except (ImportError, Exception) as e:
        print(f"Warning: Could not load config for {key}: {e}")
        return default_choices or []
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField('Password', validators=[Optional(), Length(min=6)])
    admin_type = SelectField('Admin Type', choices=[
        ('volunteer', 'Volunteer'),
        ('loc', 'LOC'),
        ('technical_delegate', 'Technical Delegate')
    ], validators=[DataRequired()])


class GameForm(FlaskForm):
    event = SelectField('Event', validators=[DataRequired()])
    genders = StringField('Genders (comma separated)', validators=[DataRequired(), Length(max=50)])
    classes = StringField('Classes (comma separated)', validators=[DataRequired(), Length(max=200)])
    phase = StringField('Phase', validators=[Optional(), Length(max=50)])
    area = StringField('Area', validators=[Optional(), Length(max=50)])
    day = IntegerField('Day', validators=[DataRequired(), NumberRange(min=1, max=8)])
    time = TimeField('Time', validators=[DataRequired()])
    nb_athletes = IntegerField('Number of Athletes', validators=[DataRequired(), NumberRange(min=1)])
    status = SelectField('Status', choices=[
        ('scheduled', 'Scheduled'),
        ('delayed', 'Delayed'),
        ('started', 'Started'),
        ('in_progress', 'In Progress'),
        ('finished', 'Finished'),
        ('cancelled', 'Cancelled')
    ], validators=[DataRequired()])
    published = BooleanField('Published')
    wpa_points = BooleanField('Use WPA Points (RAZA Scoring)')

    def __init__(self, *args, **kwargs):
        super(GameForm, self).__init__(*args, **kwargs)
        field_events = get_config_choices('field_events',
                                          ['Javelin Throw', 'Shot Put', 'Discus Throw', 'Club Throw', 'Long Jump',
                                           'High Jump', 'Triple Jump'])
        track_events = get_config_choices('track_events', ['100m', '200m', '400m', '800m', '1500m', '5000m', '4x100m',
                                                           'Universal Relay'])
        all_events = field_events + track_events
        self.event.choices = [(e, e) for e in all_events]



class PDFUploadForm(FlaskForm):
    startlist_pdf = FileField('Start List PDF', validators=[Optional(), FileAllowed(['pdf'], 'PDF files only')])
    results_pdf = FileField('Results PDF', validators=[Optional(), FileAllowed(['pdf'], 'PDF files only')])

class AthleteForm(FlaskForm):
    sdms = IntegerField('SDMS Number', validators=[DataRequired(), NumberRange(min=1)])
    firstname = StringField('First Name', validators=[DataRequired(), Length(max=100)])
    lastname = StringField('Last Name', validators=[DataRequired(), Length(max=100)])
    npc = StringField('NPC Code', validators=[DataRequired(), Length(min=3, max=3)])
    gender = SelectField('Gender', choices=[('Male', 'Male'), ('Female', 'Female')], validators=[DataRequired()])
    athlete_classes = StringField('Classes (comma separated)', validators=[DataRequired(), Length(max=200)])
    date_of_birth = DateField('Date of Birth', validators=[Optional()])
    photo = FileField('Photo', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'])])
    is_guide = BooleanField('Is Guide')
    def validate_athlete_classes(self, field):
        if not field.data:
            raise ValidationError('At least one class is required')
        classes = [c.strip() for c in field.data.split(',')]
        valid_classes = get_config_choices('classes', [])
        invalid_classes = [c for c in classes if c not in valid_classes]
        if invalid_classes:
            raise ValidationError(f'Invalid classes: {", ".join(invalid_classes)}')
class WorldRecordForm(FlaskForm):
    sdms = IntegerField('SDMS (optional)', validators=[Optional()])
    event = SelectField('Event', validators=[DataRequired()])
    athlete_class = SelectField('Class', validators=[DataRequired()])
    performance = StringField('Performance', validators=[DataRequired(), Length(max=20)])
    location = StringField('Location', validators=[DataRequired(), Length(max=100)])
    npc = StringField('NPC Code', validators=[Optional(), Length(min=3, max=3)])
    record_date = DateField('Record Date', validators=[DataRequired()])
    record_type = SelectField('Record Type', choices=[('WR', 'World Record'), ('AR', 'Area Record')],
                              validators=[DataRequired()])
    made_in_competition = BooleanField('Made in this competition')
    def __init__(self, *args, **kwargs):
        super(WorldRecordForm, self).__init__(*args, **kwargs)
        field_events = get_config_choices('field_events', [])
        track_events = get_config_choices('track_events', [])
        all_events = field_events + track_events
        self.event.choices = [(e, e) for e in all_events]
        classes = get_config_choices('classes', [])
        self.athlete_class.choices = [(c, c) for c in classes]
class PersonalBestForm(FlaskForm):
    sdms = IntegerField('SDMS', validators=[DataRequired()])
    event = SelectField('Event', validators=[DataRequired()])
    athlete_class = SelectField('Class', validators=[DataRequired()])
    performance = StringField('Performance', validators=[DataRequired(), Length(max=20)])
    location = StringField('Location', validators=[DataRequired(), Length(max=100)])
    record_date = DateField('Record Date', validators=[DataRequired()])
    made_in_competition = BooleanField('Made in this competition')
    def __init__(self, *args, **kwargs):
        super(PersonalBestForm, self).__init__(*args, **kwargs)
        field_events = get_config_choices('field_events', [])
        track_events = get_config_choices('track_events', [])
        all_events = field_events + track_events
        self.event.choices = [(e, e) for e in all_events]
        classes = get_config_choices('classes', [])
        self.athlete_class.choices = [(c, c) for c in classes]
class AttemptForm(FlaskForm):
    value = StringField('Value', validators=[Optional()])
class ResultForm(FlaskForm):
    athlete_sdms = IntegerField('Athlete SDMS', validators=[DataRequired(message="Please select an athlete")])
    rank = StringField('Rank', validators=[Optional(), Length(max=10)])
    value = StringField('Performance Value',
                        validators=[DataRequired(message="Performance value is required"), Length(max=20)])
    record = SelectField('Record', validators=[Optional()])
    weight = FloatField('Weight', validators=[Optional()], render_kw={"placeholder": "X.XXX kg"})
    attempt_1 = StringField('Attempt 1', validators=[Optional()])
    attempt_2 = StringField('Attempt 2', validators=[Optional()])
    attempt_3 = StringField('Attempt 3', validators=[Optional()])
    attempt_4 = StringField('Attempt 4', validators=[Optional()])
    attempt_5 = StringField('Attempt 5', validators=[Optional()])
    attempt_6 = StringField('Attempt 6', validators=[Optional()])
    wind_attempt_1 = FloatField('Wind attempt 1', validators=[Optional()])
    wind_attempt_2 = FloatField('Wind attempt 2', validators=[Optional()])
    wind_attempt_3 = FloatField('Wind attempt 3', validators=[Optional()])
    wind_attempt_4 = FloatField('Wind attempt 4', validators=[Optional()])
    wind_attempt_5 = FloatField('Wind attempt 5', validators=[Optional()])
    wind_attempt_6 = FloatField('Wind attempt 6', validators=[Optional()])
    def __init__(self, *args, **kwargs):
        super(ResultForm, self).__init__(*args, **kwargs)
        record_types = get_config_choices('record_types', ['WR', 'AR', 'CR', 'NR', 'PB', 'SB'])
        self.record.choices = [('', 'None')] + [(r, r) for r in record_types]
    def validate_value(self, field):
        special_values = get_config_choices('result_special_values', ['DNS', 'DNF', 'DQ', 'NM', 'O', 'X', '-'])
        if field.data in special_values:
            return True
        if ':' in field.data:
            if not re.match(r'^(\d{1,2}:)?\d{1,2}\.\d{1,4}$', field.data):
                raise ValidationError('Invalid time format. Use MM:SS.SSSS or SS.SSSS')
        else:
            try:
                float(field.data)
            except ValueError:
                raise ValidationError('Invalid performance value')
        return True
class StartListForm(FlaskForm):
    athlete_sdms = IntegerField('Athlete SDMS', validators=[DataRequired()])
    lane_order = IntegerField('Lane/Order', validators=[Optional(), NumberRange(min=1)])
    guide_sdms = IntegerField('Guide SDMS', validators=[Optional()])
class HighJumpHeightsForm(FlaskForm):
    heights = StringField('Heights (comma-separated)',
                         validators=[DataRequired()],
                         render_kw={"placeholder": "1.50, 1.55, 1.60, 1.65, 1.70, 1.75, 1.80"})