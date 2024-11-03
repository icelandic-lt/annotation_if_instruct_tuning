from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, session
from flask_login import current_user, login_required
from app import db
from app.tasks import bp
from app.models import Prompt, Evaluation, RankingTask, EvaluationTask, User
from app.utils.llm_utils import generate_llm_response
import random
from sqlalchemy.sql.expression import func, select
from datetime import datetime, timedelta
from markdown import markdown
from flask_wtf import FlaskForm
from wtforms import TextAreaField, HiddenField
from wtforms.validators import DataRequired
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

class ConversationForm(FlaskForm):
    action = HiddenField('Action')
    user_prompt = TextAreaField('Prompt', validators=[DataRequired()])

PROMPT_POSTFIXES = [
    "",  # No postfix
    "Respond in the same language as the input above, but make the response exceptionally short.",
    "Respond in the same language as the input above, but make the response exceptionally funny.",
    "Respond in the same language as the input above, but make the response exceptionally long and detailed.",
    "Respond in the same language as the input above, but make the response exceptionally clear and well written.",
    "Respond in the same language as the input above, but make the response written like it's a response for a five year old.",
    "Respond in the same language as the input above, but use a formal and academic tone.",
    "Respond in the same language as the input above, but write it as a poem or song lyrics.",
    "Respond in the same language as the input above, but include three interesting facts related to the topic.",
    "Respond in the same language as the input above, but write it as a dramatic monologue.",
    "Respond in the same language as the input above, but explain it as if you're a time traveler from the year 3000.",
    "Respond in the same language as the input above, but write it in the style of a famous author or historical figure.",
    "Respond in the same language as the input above, but include a short story that illustrates the main point.",
    "Respond in the same language as the input above, but frame it as a series of rhetorical questions.",
    "Respond in the same language as the input above, but write it as a news article headline and brief summary.",
]

class ExtendConversationForm(FlaskForm):
    user_prompt = TextAreaField('Your Response', validators=[DataRequired()])

@bp.route('/prompt_evaluation', methods=['GET', 'POST'])
@login_required
def prompt_evaluation():
    return render_template('tasks/prompt_evaluation.html', title='Prompt Evaluation')

@bp.route('/response_evaluation', methods=['GET', 'POST'])
@login_required
def response_evaluation():
    return render_template('tasks/response_evaluation.html', title='Response Evaluation')

@bp.route('/get_prompt', methods=['GET'])
@login_required
def get_prompt():
    # Fetch a random prompt for evaluation
    prompt = Prompt.query.order_by(db.func.random()).first()
    if not prompt:
        return jsonify({'error': 'No prompts available'}), 404

    # Generate synthetic prompts using LLM
    synthetic_prompts = generate_synthetic_prompts(prompt.prompt_text)

    return jsonify({
        'original_prompt': prompt.prompt_text,
        'synthetic_prompts': synthetic_prompts
    })

@bp.route('/submit_prompt_improvement', methods=['POST'])
@login_required
def submit_prompt_improvement():
    data = request.get_json()
    original_prompt_id = data.get('prompt_id')
    improved_prompt_text = data.get('improved_prompt')

    if not original_prompt_id or not improved_prompt_text:
        return jsonify({'error': 'Missing data'}), 400

    original_prompt = Prompt.query.get(original_prompt_id)
    if not original_prompt:
        return jsonify({'error': 'Prompt not found'}), 404

    new_prompt = Prompt(
        parent_id=original_prompt_id,
        language=original_prompt.language,
        prompt_text=improved_prompt_text,
        is_synthetic=False,
        is_revision=True,
        revised_prompt_id=original_prompt_id,
        revision_author_type='user',
        revision_author_id=current_user.id
    )

    db.session.add(new_prompt)
    db.session.commit()

    return jsonify({'status': 'success', 'new_prompt_id': new_prompt.id})

@bp.route('/get_responses', methods=['GET'])
@login_required
def get_responses():
    # Implement logic to fetch responses for evaluation
    # Return JSON data
    prompt = "This is a sample prompt for response evaluation."
    responses = [
        {"id": 1, "text": "This is response 1", "retrieval": False},
        {"id": 2, "text": "This is response 2", "retrieval": True},
        # ... other responses ...
    ]
    random.shuffle(responses)
    return jsonify({
        'prompt': prompt,
        'responses': responses
    })

@bp.route('/evaluate_prompt/<int:prompt_id>', methods=['GET', 'POST'])
@login_required
def evaluate_prompt(prompt_id):
    prompt = Prompt.query.get_or_404(prompt_id)
    
    if request.method == 'POST':
        data = request.form
        evaluation = Evaluation(
            user_id=current_user.id,
            item_evaluated_id=prompt_id,
            evaluation_type='prompt',
            score_number=data.get('quality_score'),
            score_text=data.get('feedback')
        )
        db.session.add(evaluation)
        db.session.commit()
        flash('Evaluation submitted successfully.')
        return redirect(url_for('tasks.prompt_evaluation'))
    
    return render_template('tasks/evaluate_prompt.html', prompt=prompt)

@bp.route('/extended_conversation/<int:prompt_id>', methods=['GET', 'POST'])
@login_required
def extended_conversation(prompt_id):
    prompt = Prompt.query.get_or_404(prompt_id)
    if request.method == 'POST':
        user_prompt = request.form.get('user_prompt')
        new_prompt = Prompt(
            parent_id=prompt_id,
            prompt_text=user_prompt,
            language=current_user.preferred_language,
            is_synthetic=False,
            revision_author_type='user',
            revision_author_id=current_user.id
        )
        db.session.add(new_prompt)
        db.session.commit()
        
        # Generate synthetic prompt using the entire conversation
        conversation = get_conversation_history(new_prompt.id)
        references = get_relevant_references(prompt_id)
        synthetic_prompt = generate_llm_response(conversation, references)
        
        new_synthetic_prompt = Prompt(
            parent_id=new_prompt.id,
            prompt_text=synthetic_prompt,
            language=current_user.preferred_language,
            is_synthetic=True,
            revision_author_type='model'
        )
        db.session.add(new_synthetic_prompt)
        db.session.commit()
        
        flash('Your prompt and a synthetic prompt have been added to the conversation.')
        return redirect(url_for('tasks.extended_conversation', prompt_id=new_synthetic_prompt.id))
    
    conversation = get_conversation_history(prompt_id)
    return render_template('tasks/extended_conversation.html', conversation=conversation, parent_id=prompt_id)

@bp.route('/flag_for_conversation/<int:prompt_id>', methods=['POST'])
@login_required
def flag_for_conversation(prompt_id):
    prompt = Prompt.query.get_or_404(prompt_id)
    prompt.flagged_for_conversation = True
    db.session.commit()
    flash('Prompt has been flagged for extended conversation.')
    return redirect(url_for('tasks.prompt_evaluation'))

@bp.route('/rank_and_revise/<int:task_id>', methods=['GET'])
@login_required
def rank_and_revise(task_id):
    task = RankingTask.query.get_or_404(task_id)
    prompts = Prompt.query.filter(Prompt.id.in_(task.prompt_ids)).all()
    
    # Get the conversation history
    conversation_history = get_conversation_history(task.parent_prompt_id)
    
    return render_template('tasks/rank_and_revise.html', task=task, prompts=prompts, conversation_history=conversation_history)

@bp.route('/submit_ranking/<int:task_id>', methods=['POST'])
@login_required
def submit_ranking(task_id):
    task = RankingTask.query.get_or_404(task_id)
    data = request.json
    ranking = data.get('ranking')

    if not ranking:
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400

    task.ranking = ranking
    db.session.commit()

    return jsonify({'status': 'success'})

@bp.route('/revise/<int:task_id>', methods=['GET'])
@login_required
def revise(task_id):
    task = RankingTask.query.get_or_404(task_id)
    conversation_history = get_conversation_history(task.parent_prompt_id)
    highest_ranked_prompt = Prompt.query.get(task.ranking[0])
    
    return render_template('tasks/revise.html', 
                           task=task, 
                           conversation_history=conversation_history, 
                           highest_ranked_prompt=highest_ranked_prompt)

@bp.route('/submit_revision/<int:task_id>', methods=['POST'])
@login_required
def submit_revision(task_id):
    task = RankingTask.query.get_or_404(task_id)
    data = request.json
    revised_prompt = data.get('revised_prompt')

    if not revised_prompt:
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400

    new_prompt = Prompt(
        parent_id=task.parent_prompt_id,
        prompt_text=revised_prompt,
        language=task.parent_prompt.language,
        is_synthetic=False,
        is_revision=True,
        revised_prompt_id=task.ranking[0],
        revision_author_type='user',
        revision_author_id=current_user.id,
        flagged_for_conversation=True  # Flag the prompt for conversation extension
    )
    db.session.add(new_prompt)
    
    task.completed_at = datetime.utcnow()
    task.user_id = current_user.id
    
    db.session.commit()

    # Create evaluation tasks for the new prompt
    create_evaluation_tasks(new_prompt.id)

    return jsonify({'status': 'success'})

@bp.route('/rank_and_revise')
@login_required
def get_next_rank_and_revise_task():
    task = RankingTask.query.filter_by(user_id=None, completed_at=None).first()
    if task:
        return redirect(url_for('tasks.rank_and_revise', task_id=task.id))
    else:
        flash('No more ranking tasks available at the moment.', 'info')
        return redirect(url_for('main.index'))

@bp.route('/evaluate/<task_type>')
@login_required
def evaluate(task_type):
    subquery = db.session.query(
        EvaluationTask.id,
        func.count(Evaluation.id).label('eval_count')
    ).outerjoin(Evaluation).group_by(EvaluationTask.id).subquery()

    task = EvaluationTask.query.join(
        subquery, EvaluationTask.id == subquery.c.id
    ).filter(
        EvaluationTask.task_type == task_type,
        EvaluationTask.language == current_user.preferred_language,
        ~EvaluationTask.evaluations.any(Evaluation.user_id == current_user.id),
        subquery.c.eval_count < 5
    ).first()

    if not task:
        flash('No more tasks available for this category.', 'info')
        return redirect(url_for('tasks.evaluation_tasks'))

    conversation_history = get_conversation_history(task.prompt_id)
    return render_template('tasks/evaluate.html', task=task, conversation_history=conversation_history)

@bp.route('/submit_evaluation/<int:task_id>', methods=['POST'])
@login_required
def submit_evaluation(task_id):
    task = EvaluationTask.query.get_or_404(task_id)
    value = request.form.get('value')

    if not value:
        flash('Please provide an evaluation.', 'error')
        return redirect(url_for('tasks.evaluate', task_type=task.task_type))

    evaluation = Evaluation(user_id=current_user.id, task_id=task.id, value=value)
    db.session.add(evaluation)
    db.session.commit()

    flash('Evaluation submitted successfully.', 'success')
    
    # Find the next available task
    subquery = db.session.query(
        EvaluationTask.id,
        func.count(Evaluation.id).label('eval_count')
    ).outerjoin(Evaluation).group_by(EvaluationTask.id).subquery()

    next_task = EvaluationTask.query.join(
        subquery, EvaluationTask.id == subquery.c.id
    ).filter(
        EvaluationTask.task_type == task.task_type,
        EvaluationTask.language == current_user.preferred_language,
        ~EvaluationTask.evaluations.any(Evaluation.user_id == current_user.id),
        subquery.c.eval_count < 5
    ).first()

    if next_task:
        return redirect(url_for('tasks.evaluate', task_type=task.task_type))
    else:
        flash('No more tasks available for this category.', 'info')
        return redirect(url_for('tasks.evaluation_tasks'))

# Helper functions
def get_conversation_history(prompt_id):
    history = []
    current_prompt = Prompt.query.get(prompt_id)
    while current_prompt:
        history.insert(0, {
            'role': 'user' if not current_prompt.is_synthetic else 'assistant',
            'content': current_prompt.prompt_text,
        })
        current_prompt = current_prompt.parent
    return history

def get_relevant_references(prompt_id):
    # Retrieve relevant references for the given prompt
    prompt = Prompt.query.get(prompt_id)
    return [ref.reference_text for ref in prompt.references]

def generate_synthetic_prompts(original_prompt):
    # Generate synthetic prompts using the LLM
    synthetic_prompts = []
    for _ in range(4):  # Generate 4 synthetic prompts
        chat_history = [{'role': 'user', 'content': f"Generate a variation of this prompt: {original_prompt}"}]
        synthetic_prompt = generate_llm_response(chat_history, [])
        synthetic_prompts.append({"text": synthetic_prompt})
    return synthetic_prompts

@bp.route('/conversation_task', methods=['GET', 'POST'])
@login_required
def conversation_task():
    form = ConversationForm()
    if form.validate_on_submit():
        return start_new_conversation(form)

    return render_template('tasks/conversation_task.html', form=form, title='Start a New Conversation')

def start_new_conversation(form):
    user_prompt = form.user_prompt.data
    if not user_prompt:
        flash('Please enter a prompt to start the conversation.', 'error')
        return redirect(url_for('tasks.conversation_task'))

    new_prompt = Prompt(
        prompt_text=user_prompt,
        language=current_user.preferred_language,
        is_synthetic=False,
        revision_author_type='user',
        revision_author_id=current_user.id,
        parent_id=None
    )
    db.session.add(new_prompt)
    db.session.commit()

    # Start response generation in a separate thread
    Thread(target=generate_responses_async, args=(new_prompt.id, current_app._get_current_object())).start()

    flash('New conversation started successfully. Responses are being generated.', 'success')
    return redirect(url_for('tasks.user_conversations'))

@bp.route('/user_conversations')
@login_required
def user_conversations():
    # Get filter preference from query parameter, default to "mine"
    filter_type = request.args.get('filter', 'mine')
    
    # Base query for prompts that are conversation starters (no parent) or are extensions
    base_query = Prompt.query.filter(
        db.or_(
            # Original conversations (no parent)
            (Prompt.parent_id == None) & (Prompt.is_synthetic == False),
            # Extended conversations
            (Prompt.is_synthetic == False) & (Prompt.parent_id != None)
        )
    )
    
    # Always filter by user's preferred language
    if filter_type == 'all':
        base_query = base_query.filter(Prompt.language == current_user.preferred_language)
    elif filter_type == 'mine':
        # Create explicit select statements for subqueries
        ranking_tasks_select = select(RankingTask.parent_prompt_id).filter(
            RankingTask.user_id == current_user.id
        ).scalar_subquery()

        evaluation_tasks_select = select(EvaluationTask.prompt_id).join(
            Evaluation
        ).filter(
            Evaluation.user_id == current_user.id
        ).scalar_subquery()

        # Show conversations where user is author or has participated
        base_query = base_query.filter(
            db.or_(
                Prompt.revision_author_id == current_user.id,  # User created the conversation
                Prompt.children.any(Prompt.revision_author_id == current_user.id),  # User participated
                Prompt.id.in_(ranking_tasks_select),  # User participated in ranking tasks
                Prompt.id.in_(evaluation_tasks_select)  # User participated in evaluations
            )
        )
    
    # Order by most recent first
    prompts = base_query.order_by(Prompt.created_at.desc()).all()
    
    conversations = []
    for prompt in prompts:
        # Get the root prompt if this is an extension
        root_prompt = prompt
        while root_prompt.parent_id is not None:
            root_prompt = root_prompt.parent

        responses = Prompt.query.filter_by(parent_id=prompt.id, is_synthetic=True).all()
        ranking_tasks = RankingTask.query.filter_by(parent_prompt_id=prompt.id).all()
        
        # Get conversation history
        history = get_conversation_history(prompt.id)
        
        # Get all human contributors (excluding synthetic responses)
        contributors = db.session.query(User).join(
            Prompt, 
            (User.id == Prompt.revision_author_id) & 
            (Prompt.revision_author_type == 'user')
        ).filter(
            db.or_(
                User.id == root_prompt.revision_author_id,  # Original author
                Prompt.parent_id == root_prompt.id,  # Direct responses to root
                Prompt.parent_id == prompt.id  # Direct responses to current prompt if it's an extension
            )
        ).distinct().all()
        
        # Get the last message in the conversation
        last_message = get_last_message(prompt.id)

        # Check if this is a revision
        is_revision = getattr(prompt, 'is_revision', False)

        # Check if responses have been generated
        responses_generated = len(responses) > 0 or len(ranking_tasks) > 0

        # Check if the task is stuck (only for non-revisions)
        is_stuck = (not is_revision and 
                   (datetime.utcnow() - prompt.created_at > timedelta(minutes=5)) and 
                   not responses_generated)

        # Check if retry is allowed
        last_retry = session.get(f'last_retry_{prompt.id}')
        retry_allowed = not last_retry or datetime.utcnow() >= datetime.fromisoformat(last_retry) + timedelta(minutes=5)

        # Get all extensions of this conversation
        extensions = []
        if prompt.id == root_prompt.id:  # Only get extensions for root prompts
            extensions = Prompt.query.filter(
                (Prompt.is_synthetic == False) &
                (Prompt.parent_id != None)
            ).filter(
                db.or_(
                    Prompt.parent_id == prompt.id,
                    Prompt.parent_id.in_(
                        select(Prompt.id).filter(Prompt.parent_id == prompt.id)
                    )
                )
            ).all()

        conversations.append({
            'prompt': prompt,
            'root_prompt': root_prompt,
            'is_extension': prompt.id != root_prompt.id,
            'history': history,
            'responses': responses,
            'ranking_tasks': ranking_tasks,
            'responses_generated': responses_generated,
            'flagged_for_conversation': getattr(prompt, 'flagged_for_conversation', False),
            'is_stuck': is_stuck,
            'retry_allowed': retry_allowed,
            'is_author': prompt.revision_author_id == current_user.id,
            'has_participated': any([
                any(r.revision_author_id == current_user.id for r in responses),
                any(t.user_id == current_user.id for t in ranking_tasks)
            ]),
            'contributors': contributors,
            'can_extend': (
                last_message and  # There is a last message
                not last_message.is_synthetic and  # Last message is human-written
                last_message.revision_author_id != current_user.id and  # User didn't write the last message
                not getattr(prompt, 'flagged_for_conversation', False)  # Not already flagged
            ),
            'extensions': extensions,
            'is_revision': is_revision,  # Add this field
            'ready_for_extension': (  # Modify this field
                is_revision and  # Is a revision
                not responses_generated  # No responses generated yet
            )
        })
    
    return render_template('tasks/user_conversations.html', 
                         conversations=conversations,
                         current_filter=filter_type)

def get_last_message(prompt_id):
    """Get the last message in a conversation chain."""
    current_prompt = Prompt.query.get(prompt_id)
    
    while True:
        # Get all non-synthetic children
        next_message = Prompt.query.filter(
            Prompt.parent_id == current_prompt.id,
            Prompt.is_synthetic == False
        ).order_by(Prompt.created_at.desc()).first()
        
        if not next_message:
            # If there are no more human messages, check if there are synthetic responses
            synthetic_response = Prompt.query.filter(
                Prompt.parent_id == current_prompt.id,
                Prompt.is_synthetic == True
            ).order_by(Prompt.created_at.desc()).first()
            
            if synthetic_response:
                return None  # Return None if the last message is synthetic
            return current_prompt  # Return the last human message
            
        current_prompt = next_message

def generate_responses_async(prompt_id, app):
    with app.app_context():
        try:
            prompt = Prompt.query.get(prompt_id)
            if not prompt:
                logging.error(f"Prompt with id {prompt_id} not found")
                return

            logging.info(f"Starting response generation for prompt {prompt_id}")
            responses = generate_responses(prompt, app)
            
            logging.info(f"Generated {len(responses)} responses for prompt {prompt_id}")
            
            # Create ranking tasks after all responses have been generated
            if responses:
                all_prompt_ids = [r.id for r in responses]
                create_ranking_tasks(prompt.id, all_prompt_ids)
                logging.info(f"Created ranking tasks for prompt {prompt_id}")
            else:
                logging.warning(f"No responses generated for prompt {prompt_id}")
            
            db.session.commit()
            logging.info(f"Completed response generation and task creation for prompt {prompt_id}")
        except Exception as e:
            logging.exception(f"Error in generate_responses_async for prompt {prompt_id}: {str(e)}")
            db.session.rollback()

def generate_responses(prompt, app):
    responses = []
    postfixes = PROMPT_POSTFIXES.copy()
    
    # Ensure at least one response has no postfix
    with app.app_context():
        first_response = generate_single_response(prompt, "")
        if first_response:
            responses.append(first_response)
    postfixes.remove("")
    
    # Generate 7 more responses in parallel
    with ThreadPoolExecutor(max_workers=7) as executor:
        future_to_postfix = {}
        for _ in range(7):
            if postfixes:
                postfix = random.choice(postfixes)
                postfixes.remove(postfix)
            else:
                postfix = random.choice(PROMPT_POSTFIXES)
            future = executor.submit(generate_single_response_with_context, prompt, postfix, app)
            future_to_postfix[future] = postfix

        for future in as_completed(future_to_postfix):
            try:
                response = future.result()
                if response and response.id not in [r.id for r in responses]:
                    responses.append(response)
            except Exception as exc:
                logging.exception(f'Response generation produced an exception: {exc}')
    
    logging.info(f"Generated {len(responses)} valid responses for prompt {prompt.id}")
    return responses

def generate_single_response_with_context(prompt, postfix, app):
    with app.app_context():
        return generate_single_response(prompt, postfix)

def generate_single_response(prompt, postfix):
    try:
        conversation_history = get_conversation_history(prompt.id)
        if postfix:
            conversation_history.append({"role": "system", "content": postfix})
        
        response_text = generate_llm_response(conversation_history, [])
        if not response_text:
            logging.warning(f"Empty response generated for prompt {prompt.id}")
            return None

        response = Prompt(
            prompt_text=response_text,
            language=prompt.language,
            is_synthetic=True,
            revision_author_type='model',
            parent_id=prompt.id,
            postfix=postfix  # Save the postfix
        )
        db.session.add(response)
        db.session.commit()
        logging.info(f"Generated response for prompt {prompt.id}: {response.id}")
        return response
    except Exception as e:
        logging.exception(f"Error in generate_single_response: {str(e)}")
        return None

def create_ranking_tasks(parent_prompt_id, all_prompt_ids):
    try:
        num_prompts = len(set(all_prompt_ids))  # Use set to remove duplicates
        if num_prompts < 4:
            logging.warning(f"Not enough unique prompts to create ranking tasks. Only {num_prompts} prompts available.")
            return

        num_tasks = min(2, num_prompts // 4)  # Create at most 2 tasks, or fewer if not enough prompts
        unique_prompt_ids = list(set(all_prompt_ids))  # Create a list of unique prompt IDs
        for _ in range(num_tasks):
            selected_prompts = random.sample(unique_prompt_ids, 4)
            task = RankingTask(
                user_id=None,
                parent_prompt_id=parent_prompt_id,
                prompt_ids=selected_prompts
            )
            db.session.add(task)
            logging.info(f"Created ranking task for parent prompt {parent_prompt_id} with prompts: {selected_prompts}")
        db.session.commit()  # Commit the changes
        logging.info(f"Created {num_tasks} ranking tasks for parent prompt {parent_prompt_id}")
    except Exception as e:
        logging.exception(f"Error in create_ranking_tasks: {str(e)}")
        db.session.rollback()  # Rollback in case of error

def get_random_conversation(language):
    return Prompt.query.filter_by(language=language, parent_id=None).order_by(func.random()).first()

def generate_conversation_extensions(conversation):
    extensions = []
    for _ in range(4):
        conversation_history = get_conversation_history(conversation.id)
        extension_text = generate_llm_response(conversation_history, [])
        extension = Prompt(
            parent_id=conversation.id,
            prompt_text=extension_text,
            language=conversation.language,
            is_synthetic=True,
            revision_author_type='model'
        )
        db.session.add(extension)
        extensions.append(extension)
    db.session.commit()
    return extensions

@bp.route('/extend_conversation/<int:prompt_id>', methods=['GET', 'POST'])
@login_required
def extend_conversation(prompt_id):
    prompt = Prompt.query.get_or_404(prompt_id)
    conversation_history = get_conversation_history(prompt.id)
    form = ExtendConversationForm()
    
    if form.validate_on_submit():
        user_prompt = form.user_prompt.data
        new_prompt = Prompt(
            prompt_text=user_prompt,
            language=prompt.language,
            is_synthetic=False,
            revision_author_type='user',
            revision_author_id=current_user.id,
            parent_id=prompt.id
        )
        db.session.add(new_prompt)
        db.session.commit()

        # Start response generation in a separate thread
        Thread(target=generate_continuations_and_create_tasks, args=(new_prompt.id, current_app._get_current_object())).start()

        flash('Your response has been added to the conversation. New continuations are being generated.', 'success')
        return redirect(url_for('tasks.user_conversations'))

    return render_template('tasks/extend_conversation.html', prompt=prompt, conversation_history=conversation_history, form=form)

def generate_continuations_and_create_tasks(prompt_id, app):
    with app.app_context():
        try:
            prompt = Prompt.query.get(prompt_id)
            if not prompt:
                logging.error(f"Prompt with id {prompt_id} not found")
                return

            logging.info(f"Starting continuation generation for prompt {prompt_id}")
            continuations = generate_continuations(prompt, app)
            
            logging.info(f"Generated {len(continuations)} continuations for prompt {prompt_id}")
            
            # Create ranking tasks after all continuations have been generated
            if continuations:
                all_prompt_ids = [c.id for c in continuations]
                create_ranking_tasks(prompt.id, all_prompt_ids)
                logging.info(f"Created ranking tasks for prompt {prompt_id}")
            else:
                logging.warning(f"No continuations generated for prompt {prompt_id}")
            
            db.session.commit()
            logging.info(f"Completed continuation generation and task creation for prompt {prompt_id}")
        except Exception as e:
            logging.exception(f"Error in generate_continuations_and_create_tasks for prompt {prompt_id}: {str(e)}")
            db.session.rollback()

def generate_continuations(prompt, app):
    continuations = []
    postfixes = PROMPT_POSTFIXES.copy()
    
    # Generate 8 continuations in parallel
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_postfix = {}
        for _ in range(8):
            if postfixes:
                postfix = random.choice(postfixes)
                postfixes.remove(postfix)
            else:
                postfix = random.choice(PROMPT_POSTFIXES)
            future = executor.submit(generate_single_continuation_with_context, prompt, postfix, app)
            future_to_postfix[future] = postfix

        for future in as_completed(future_to_postfix):
            try:
                continuation = future.result()
                if continuation and continuation.id not in [c.id for c in continuations]:
                    continuations.append(continuation)
            except Exception as exc:
                logging.exception(f'Continuation generation produced an exception: {exc}')
    
    logging.info(f"Generated {len(continuations)} valid continuations for prompt {prompt.id}")
    return continuations

def generate_single_continuation_with_context(prompt, postfix, app):
    with app.app_context():
        return generate_single_continuation(prompt, postfix)

def generate_single_continuation(prompt, postfix):
    try:
        conversation_history = get_conversation_history(prompt.id)
        if postfix:
            conversation_history.append({"role": "system", "content": postfix})
        
        continuation_text = generate_llm_response(conversation_history, [])
        if not continuation_text:
            logging.warning(f"Empty continuation generated for prompt {prompt.id}")
            return None

        continuation = Prompt(
            prompt_text=continuation_text,
            language=prompt.language,
            is_synthetic=True,
            revision_author_type='model',
            parent_id=prompt.id,
            postfix=postfix
        )
        db.session.add(continuation)
        db.session.commit()
        logging.info(f"Generated continuation for prompt {prompt.id}: {continuation.id}")
        return continuation
    except Exception as e:
        logging.exception(f"Error in generate_single_continuation: {str(e)}")
        return None

@bp.route('/retry_response_generation/<int:prompt_id>', methods=['POST'])
@login_required
def retry_response_generation(prompt_id):
    prompt = Prompt.query.get_or_404(prompt_id)
    
    # Check if the user is authorized to retry this prompt
    if prompt.revision_author_id != current_user.id:
        flash('You are not authorized to retry this task.', 'error')
        return redirect(url_for('tasks.user_conversations'))

    # Check if 5 minutes have passed since the last retry
    last_retry = session.get(f'last_retry_{prompt_id}')
    if last_retry and datetime.utcnow() < datetime.fromisoformat(last_retry) + timedelta(minutes=5):
        flash('Please wait 5 minutes before retrying again.', 'warning')
        return redirect(url_for('tasks.user_conversations'))

    # Start response generation in a separate thread
    Thread(target=generate_responses_async, args=(prompt.id, current_app._get_current_object())).start()

    # Update the last retry timestamp
    session[f'last_retry_{prompt_id}'] = datetime.utcnow().isoformat()

    flash('Response generation retry initiated.', 'success')
    return redirect(url_for('tasks.user_conversations'))

@bp.route('/create_evaluation_tasks/<int:prompt_id>')
@login_required
def create_evaluation_tasks(prompt_id):
    prompt = Prompt.query.get_or_404(prompt_id)
    task_types = ['pii', 'quality_score', 'seriousness', 'creativity', 'politeness', 'safety', 'friendliness', 'difficulty', 'spam', 'appropriate', 'hate_speech', 'sexual_content', 'child_friendly', 'bias', 'sarcasm', 'topic_tags']
    
    for task_type in task_types:
        new_task = EvaluationTask(prompt_id=prompt.id, task_type=task_type, language=prompt.language)
        db.session.add(new_task)
    
    db.session.commit()
    flash('Evaluation tasks created successfully.', 'success')
    return redirect(url_for('tasks.user_conversations'))

@bp.route('/evaluation_tasks')
@login_required
def evaluation_tasks():
    task_counts = db.session.query(
        EvaluationTask.task_type,
        func.count(EvaluationTask.id).label('total'),
        func.count(Evaluation.id).label('completed')
    ).outerjoin(Evaluation, (EvaluationTask.id == Evaluation.task_id) & (Evaluation.user_id == current_user.id)
    ).filter(EvaluationTask.language == current_user.preferred_language
    ).group_by(EvaluationTask.task_type).all()

    return render_template('tasks/evaluation_tasks.html', task_counts=task_counts)

