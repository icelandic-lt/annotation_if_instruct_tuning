from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from app import db
from app.main import bp
from app.models import User, Prompt, Evaluation
from app.main.forms import EditProfileForm
from datetime import datetime, timedelta
from sqlalchemy import func, desc

@bp.route('/')
@bp.route('/index')
def index():
    if current_user.is_authenticated:
        # Get the user's statistics
        prompts_ranked = db.session.query(func.count(Prompt.id)).filter(
            Prompt.revision_author_id == current_user.id,
            Prompt.is_revision == True
        ).scalar()

        evaluations_performed = db.session.query(func.count(Evaluation.id)).filter(
            Evaluation.user_id == current_user.id
        ).scalar()

        conversations_count = db.session.query(func.count(Prompt.id)).filter(
            Prompt.revision_author_id == current_user.id,
            Prompt.parent_id != None
        ).scalar()

        # Calculate user rank (this is a simple implementation and might need optimization for large user bases)
        user_scores = db.session.query(
            User.id,
            (func.count(Prompt.id) + func.count(Evaluation.id)).label('score')
        ).outerjoin(Prompt, (User.id == Prompt.revision_author_id) & (Prompt.is_revision == True)
        ).outerjoin(Evaluation, User.id == Evaluation.user_id
        ).group_by(User.id).order_by(desc('score')).all()

        user_rank = next((i for i, (user_id, _) in enumerate(user_scores, 1) if user_id == current_user.id), None)

        return render_template('main/index_authenticated.html', 
                               title='Dashboard',
                               prompts_ranked=prompts_ranked,
                               evaluations_performed=evaluations_performed,
                               conversations_count=conversations_count,
                               user_rank=user_rank)
    else:
        return render_template('main/index_landing.html', title='Welcome')

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.preferred_language = form.preferred_language.data
        current_user.interface_language = form.interface_language.data
        db.session.commit()
        flash('Your changes have been saved.', 'success')
        return redirect(url_for('main.profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.preferred_language.data = current_user.preferred_language
        form.interface_language.data = current_user.interface_language
    return render_template('main/profile.html', title='Profile', form=form)

@bp.route('/leaderboard')
def leaderboard():
    # Get user statistics from the database
    user_stats = db.session.query(
        User,
        func.count(Prompt.id).label('prompts_evaluated'),
        func.count(Evaluation.id).label('evaluations_performed'),
        (func.count(Prompt.id) + func.count(Evaluation.id)).label('total_score')
    ).outerjoin(
        Prompt, (User.id == Prompt.revision_author_id) & (Prompt.is_revision == True)
    ).outerjoin(
        Evaluation, User.id == Evaluation.user_id
    ).group_by(User.id).order_by(desc('total_score')).all()

    # Format the data for the template
    leaderboard_data = [{
        'username': user.username,
        'joined_date': user.created_at.strftime('%Y-%m-%d'),
        'prompts_evaluated': prompts_evaluated,
        'responses_assessed': evaluations_performed,
        'total_score': total_score
    } for user, prompts_evaluated, evaluations_performed, total_score in user_stats]

    return render_template('main/leaderboard.html', 
                         title='Leaderboard', 
                         leaderboard=leaderboard_data)
