from app import create_app, db
from app.models import User, Prompt, Evaluation, Reference

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Prompt': Prompt, 'Reference': Reference, 'Evaluation': Evaluation}