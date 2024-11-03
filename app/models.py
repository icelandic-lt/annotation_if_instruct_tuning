from app import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy import PickleType

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='regular')
    preferred_language = db.Column(db.String(10))
    interface_language = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    rank_revise_tasks = db.relationship('RankReviseTask', backref='user_rank_revise', lazy='dynamic')
    ranking_tasks = db.relationship('RankingTask', backref='user_ranking', lazy='dynamic')
    evaluations = db.relationship('Evaluation', back_populates='user', overlaps="evaluation_tasks")
    evaluation_tasks = db.relationship('EvaluationTask', secondary='evaluation', back_populates='users', overlaps="evaluations")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

# Association table for prompts and references
prompt_references = db.Table('prompt_references',
    db.Column('prompt_id', db.Integer, db.ForeignKey('prompt.id'), primary_key=True),
    db.Column('reference_id', db.Integer, db.ForeignKey('reference.id'), primary_key=True)
)

class Prompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('prompt.id'))
    language = db.Column(db.String(50))
    prompt_text = db.Column(db.Text)
    is_synthetic = db.Column(db.Boolean, default=False)
    source_id = db.Column(db.String(64), index=True)
    model_used = db.Column(db.String(64))
    source_dataset = db.Column(db.String(64))
    is_revision = db.Column(db.Boolean, default=False)
    revised_prompt_id = db.Column(db.Integer, db.ForeignKey('prompt.id'))
    revision_author_type = db.Column(db.String(10)) # 'user' or 'model'
    revision_author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reference_prompt_prefix = db.Column(db.Text)
    flagged_for_conversation = db.Column(db.Boolean, default=False)
    postfix = db.Column(db.Text)
    evaluation_tasks = db.relationship('EvaluationTask', back_populates='prompt')

    parent = db.relationship('Prompt', 
                           remote_side=[id],
                           backref=db.backref('children', lazy='dynamic'),
                           foreign_keys=[parent_id])
    revised_prompt = db.relationship('Prompt',
                                   remote_side=[id],
                                   backref=db.backref('revisions', lazy='dynamic'),
                                   foreign_keys=[revised_prompt_id])
    references = db.relationship('Reference', secondary=prompt_references, 
                               backref=db.backref('prompts', lazy='dynamic'))

    # Update the revision_author relationship with foreign_keys
    revision_author = db.relationship('User', 
                                    foreign_keys=[revision_author_id],
                                    backref=db.backref('authored_prompts', lazy='dynamic'))

class Reference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference_link = db.Column(db.String(256))
    reference_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Evaluation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('evaluation_task.id'), nullable=False)
    value = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='evaluations', overlaps="evaluation_tasks")
    task = db.relationship('EvaluationTask', back_populates='evaluations', overlaps="users,evaluation_tasks")

class EvaluationTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prompt_id = db.Column(db.Integer, db.ForeignKey('prompt.id'), nullable=False)
    task_type = db.Column(db.String(50), nullable=False)  # e.g., 'pii', 'quality_score', etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    language = db.Column(db.String(10), nullable=False)

    prompt = db.relationship('Prompt', back_populates='evaluation_tasks')
    evaluations = db.relationship('Evaluation', back_populates='task', overlaps="users")
    users = db.relationship('User', secondary='evaluation', back_populates='evaluation_tasks', overlaps="evaluations,user")

# Association table for rankings and items
ranking_items = db.Table('ranking_items',
    db.Column('ranking_id', db.Integer, db.ForeignKey('ranking.id'), primary_key=True),
    db.Column('item_id', db.Integer, primary_key=True),
    db.Column('rank_order', db.Integer)
)

class Ranking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    model_id = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Replace comma-separated item_ranked_ids with proper relationship
    ranked_items = db.relationship('RankingItem', backref='ranking', 
                                 order_by='RankingItem.rank_order')

class RankingItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ranking_id = db.Column(db.Integer, db.ForeignKey('ranking.id'))
    item_id = db.Column(db.Integer)
    rank_order = db.Column(db.Integer)

class RankReviseTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    prompt_id = db.Column(db.Integer, db.ForeignKey('prompt.id'), nullable=False)
    extension1_id = db.Column(db.Integer, db.ForeignKey('prompt.id'), nullable=False)
    extension2_id = db.Column(db.Integer, db.ForeignKey('prompt.id'), nullable=False)
    extension3_id = db.Column(db.Integer, db.ForeignKey('prompt.id'), nullable=False)
    extension4_id = db.Column(db.Integer, db.ForeignKey('prompt.id'), nullable=False)
    ranking = db.Column(db.String(4))  # Store ranking as a string, e.g., "3142"
    revised_prompt_id = db.Column(db.Integer, db.ForeignKey('prompt.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    # Remove this line or change it to match the backref in User model
    # user = db.relationship('User', backref='rank_revise_tasks')
    
    prompt = db.relationship('Prompt', foreign_keys=[prompt_id])
    extension1 = db.relationship('Prompt', foreign_keys=[extension1_id])
    extension2 = db.relationship('Prompt', foreign_keys=[extension2_id])
    extension3 = db.relationship('Prompt', foreign_keys=[extension3_id])
    extension4 = db.relationship('Prompt', foreign_keys=[extension4_id])
    revised_prompt = db.relationship('Prompt', foreign_keys=[revised_prompt_id])

class RankingTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    parent_prompt_id = db.Column(db.Integer, db.ForeignKey('prompt.id'), nullable=False)
    prompt_ids = db.Column(MutableList.as_mutable(PickleType), default=[])
    ranking = db.Column(MutableList.as_mutable(PickleType), default=[])
    revised_prompt_id = db.Column(db.Integer, db.ForeignKey('prompt.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    # Remove this line or change it to match the backref in User model
    # user = db.relationship('User', backref='ranking_tasks')
    
    parent_prompt = db.relationship('Prompt', foreign_keys=[parent_prompt_id])
    revised_prompt = db.relationship('Prompt', foreign_keys=[revised_prompt_id])

    def __init__(self, parent_prompt_id, prompt_ids, *args, **kwargs):
        super(RankingTask, self).__init__(*args, **kwargs)
        self.parent_prompt_id = parent_prompt_id
        self.prompt_ids = prompt_ids or []

    def set_ranking(self, ranking):
        self.ranking = ranking

    def set_revised_prompt(self, revised_prompt_id):
        self.revised_prompt_id = revised_prompt_id

    def complete(self, user_id):
        self.user_id = user_id
        self.completed_at = datetime.utcnow()
