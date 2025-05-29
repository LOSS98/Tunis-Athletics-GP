from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, DateField, BooleanField
from wtforms.validators import DataRequired, NumberRange, Optional


class ConfigForm(FlaskForm):
    classes = TextAreaField('Classes',
                            description='List of disability classes (comma-separated)',
                            validators=[DataRequired()])

    record_types = StringField('Record Types',
                               description='Available record types (comma-separated)',
                               validators=[DataRequired()])

    result_special_values = StringField('Special Result Values',
                                        description='Special values for results (comma-separated)',
                                        validators=[DataRequired()])

    field_events = StringField('Field Events',
                               description='Field events (comma-separated)',
                               validators=[DataRequired()])

    track_events = StringField('Track Events',
                               description='Track events (comma-separated)',
                               validators=[DataRequired()])

    wind_affected_field_events = StringField('Wind-Affected Field Events',
                                           description='Field events affected by wind velocity (comma-separated)',
                                           validators=[Optional()])


class StatsConfigForm(FlaskForm):
    countries_count = IntegerField('Number of Countries',
                                   validators=[DataRequired(), NumberRange(min=1)],
                                   description='Total number of participating countries')

    athletes_count = IntegerField('Number of Athletes',
                                  validators=[DataRequired(), NumberRange(min=1)],
                                  description='Total number of registered athletes')

    volunteers_count = IntegerField('Number of Volunteers',
                                    validators=[DataRequired(), NumberRange(min=0)],
                                    description='Total number of volunteers')

    loc_count = IntegerField('Number of LOC Members',
                             validators=[DataRequired(), NumberRange(min=1)],
                             description='Total number of Local Organizing Committee members')

    officials_count = IntegerField('Number of Officials',
                                   validators=[DataRequired(), NumberRange(min=1)],
                                   description='Total number of technical officials')


class CompetitionDayForm(FlaskForm):
    day_number = IntegerField('Day Number',
                              validators=[DataRequired(), NumberRange(min=1, max=30)],
                              description='Competition day number')

    date_start = DateField('Start Date',
                           validators=[DataRequired()],
                           description='Date when this competition day starts')

    date_end = DateField('End Date',
                         validators=[Optional()],
                         description='Date when this competition day ends (optional, defaults to start date)')

    description = StringField('Description',
                              validators=[Optional()],
                              description='Optional description for this day (e.g., "Opening Ceremony", "Finals")')

    is_active = BooleanField('Active',
                             default=True,
                             description='Whether this day is active for automatic day detection')


class CurrentDayForm(FlaskForm):
    current_day = IntegerField('Current Day',
                               validators=[DataRequired(), NumberRange(min=1, max=30)],
                               description='Manually set the current competition day')