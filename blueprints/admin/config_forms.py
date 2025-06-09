from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, IntegerField, TextAreaField, DateField, BooleanField, SelectField, HiddenField
from wtforms.validators import DataRequired, NumberRange, Optional, Length
from utils.helpers import validate_svg_file
class ConfigForm(FlaskForm):
    classes = HiddenField('Classes')
    record_types = HiddenField('Record Types')
    result_special_values = HiddenField('Special Result Values')
    field_events = HiddenField('Field Events')
    track_events = HiddenField('Track Events')
    wind_affected_field_events = HiddenField('Wind Affected Field Events')
    weight_field_events = HiddenField('Weight Field Events')
class StatsConfigForm(FlaskForm):
    npcs_count = IntegerField('Number of NPCs',
                                   validators=[DataRequired(), NumberRange(min=1)],
                                   description='Total number of participating NPCs')
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
class NPCForm(FlaskForm):
    code = StringField('NPC Code',
                       validators=[DataRequired(), Length(min=3, max=3)],
                       description='3-letter NPC code (ISO 3166-1 alpha-3)')
    name = StringField('NPC Name',
                       validators=[DataRequired(), Length(max=100)],
                       description='Full NPC name')
    region_code = SelectField('Region',
                              validators=[Optional()],
                              description='Region for area records grouping')
    flag_file = FileField('Flag File (SVG only)',
                          validators=[Optional(), validate_svg_file],
                          description='Upload SVG flag file')
    def __init__(self, *args, **kwargs):
        super(NPCForm, self).__init__(*args, **kwargs)
        try:
            from database.models.region import Region
            regions = Region.get_all()
            self.region_code.choices = [('', 'Select Region')] + [(r['code'], r['name']) for r in regions]
        except:
            self.region_code.choices = [('', 'Select Region')]
class RecordTypeForm(FlaskForm):
    abbreviation = StringField('Abbreviation',
                               validators=[DataRequired(), Length(min=1, max=10)],
                               description='Short abbreviation (e.g., WR, AR, CR)')
    full_name = StringField('Full Name',
                            validators=[DataRequired(), Length(max=100)],
                            description='Complete record type name')
    scope_type = SelectField('Scope Type',
                             choices=[
                                 ('world', 'World'),
                                 ('continental', 'Continental'),
                                 ('regional', 'Regional'),
                                 ('national', 'National'),
                                 ('personal', 'Personal'),
                                 ('seasonal', 'Seasonal'),
                                 ('competition', 'Competition')
                             ],
                             validators=[DataRequired()],
                             description='Geographic or temporal scope of this record')
    scope_values = StringField('Scope Values',
                               validators=[Optional()],
                               description='Comma-separated npcs/continents (e.g., "FRA,GBR" or "Europe,Asia")')
    description = TextAreaField('Description',
                                validators=[Optional()],
                                description='Additional information about this record type')