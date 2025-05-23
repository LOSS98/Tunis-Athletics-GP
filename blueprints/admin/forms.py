from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, IntegerField, SelectField, TimeField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from config import Config

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class AthleteForm(FlaskForm):
    bib = IntegerField('BIB Number', validators=[DataRequired(), NumberRange(min=1)])
    firstname = StringField('First Name', validators=[DataRequired(), Length(max=100)])
    lastname = StringField('Last Name', validators=[DataRequired(), Length(max=100)])
    country = StringField('Country Code', validators=[DataRequired(), Length(min=3, max=3)])
    gender = SelectField('Gender', choices=[(g, g) for g in Config.GENDERS], validators=[DataRequired()])
    athlete_class = SelectField('Class', choices=[(c, c) for c in Config.CLASSES], validators=[DataRequired()])
    photo = FileField('Photo', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'])])

class GameForm(FlaskForm):
    event = StringField('Event', validators=[DataRequired(), Length(max=100)])
    gender = SelectField('Gender', choices=[(g, g) for g in Config.GENDERS], validators=[DataRequired()])
    classes = StringField('Classes', validators=[DataRequired(), Length(max=50)])
    phase = StringField('Phase', validators=[Optional(), Length(max=50)])
    area = StringField('Area', validators=[Optional(), Length(max=50)])
    day = IntegerField('Day', validators=[DataRequired(), NumberRange(min=1)])
    time = TimeField('Time', validators=[DataRequired()])
    duration = IntegerField('Duration (minutes)', validators=[DataRequired(), NumberRange(min=1)])
    nb_athletes = IntegerField('Number of Athletes', validators=[DataRequired(), NumberRange(min=1)])
    status = SelectField('Status', choices=[
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('finished', 'Finished'),
        ('cancelled', 'Cancelled')
    ], validators=[DataRequired()])
    start_file = FileField('Start List File', validators=[FileAllowed(['pdf', 'txt'])])
    result_file = FileField('Results File', validators=[FileAllowed(['pdf', 'txt'])])

class ResultForm(FlaskForm):
    athlete_bib = IntegerField('Athlete BIB', validators=[DataRequired()])
    rank = StringField('Rank', validators=[Optional(), Length(max=10)])
    value = StringField('Performance Value', validators=[DataRequired(), Length(max=20)])
    record = SelectField('Record', choices=[('', 'None')] + [(r, r) for r in Config.RECORD_TYPES], validators=[Optional()])