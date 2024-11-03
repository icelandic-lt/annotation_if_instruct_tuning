# Prompt and Response Evaluation System

This web application is designed for rating, ranking, and improving prompts and responses. It supports multiple languages and includes various evaluation tasks for both prompts and responses.

## Features

- User registration and authentication
- Multilingual support for working languages and interface
- Prompt evaluation tasks
- Response evaluation tasks
- Extended conversation feature
- Leaderboards and user statistics

## Technology Stack

- Backend: Flask
- Frontend: Flask Templates (Jinja2), TailwindCSS, DaisyUI, htmx, Alpine.js
- Database: SQLAlchemy (SQLite for local development, PostgreSQL for production)
- Hosting: Heroku

## Local Development Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/prompt-evaluation-system.git
   cd prompt-evaluation-system
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```
   export FLASK_APP=wsgi.py
   export FLASK_ENV=development
   ```
   On Windows, use `set` instead of `export`.

5. Initialize the database:
   ```
   flask db init
   flask db migrate
   flask db upgrade
   ```

6. Run the development server:
   ```
   flask run
   ```

7. Open your browser and navigate to `http://localhost:5000`

## Heroku Deployment

1. Create a Heroku account and install the Heroku CLI.

2. Login to Heroku CLI:
   ```
   heroku login
   ```

3. Create a new Heroku app:
   ```
   heroku create your-app-name
   ```

4. Add PostgreSQL addon:
   ```
   heroku addons:create heroku-postgresql:hobby-dev
   ```

5. Set environment variables:
   ```
   heroku config:set FLASK_APP=wsgi.py
   heroku config:set SECRET_KEY=your-secret-key
   ```

6. Deploy the application:
   ```
   git push heroku main
   ```

7. Run database migrations:
   ```
   heroku run flask db upgrade
   ```

8. Open the application:
   ```
   heroku open
   ```

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct, and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE.md file for details.