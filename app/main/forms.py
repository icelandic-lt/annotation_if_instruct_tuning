from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, ValidationError
from app.models import User

class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    preferred_language = SelectField('Preferred Working Language', choices=[
        ('is', 'Icelandic'), ('da', 'Danish'), ('nb', 'Norwegian Bokmål'),
        ('nn', 'Norwegian Nynorsk'), ('sv', 'Swedish'), ('nl', 'Dutch'),
        ('de', 'German'), ('fo', 'Faroese')
    ])
    interface_language = SelectField('Interface Language', choices=[('en', 'English'), ('is', 'Icelandic')])
    submit = SubmitField('Save Changes')

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError('Please use a different username.')
