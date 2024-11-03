# **Revised Specifications: Prompt and Response Evaluation System**

## **1. Introduction**

This document provides a detailed specification for developing a web application designed to rate, rank, and improve prompts and responses. The system supports multiple languages and includes various evaluation tasks for both prompts and responses. This specification also outlines the recommended order of feature implementation to ensure an efficient development process.

---

## **2. Implementation Roadmap**

To streamline development, the features should be implemented in the following order:

1. **Project Setup and Basic Structure**
2. **User Management**
3. **Multilingual Support**
4. **Database Schema Design**
5. **Prompt Evaluation Task**
6. **Response Evaluation Task**
7. **Evaluation Tasks Interface**
8. **Extended Conversation Feature**
9. **User Interface Enhancements**
10. **Administrator Interface**
11. **Performance and Scalability Enhancements**
12. **Security Measures**
13. **Deployment and Maintenance**

---

## **3. Technology Stack**

### **3.1 Backend**

- **Flask**: A lightweight WSGI web application framework for Python.

### **3.2 Frontend**

- **Flask Templates (Jinja2)**: For rendering dynamic HTML pages.
- **TailwindCSS**: A utility-first CSS framework for rapid UI development.
- **DaisyUI**: A plugin for TailwindCSS that provides pre-designed components.
- **Alpine.js**: A minimal JavaScript framework for adding interactivity.

### **3.3 Database**

- **SQLAlchemy**: An ORM for database interactions.
  - Implement naming conventions for migrations (constraints, indexes, etc.).
- **Local Development**: SQLite for simplicity.
- **Production**: PostgreSQL hosted on Heroku.

### **3.4 Hosting**

- **Heroku**: For deploying the application with support for PostgreSQL.

---

## **4. User Management**

### **4.1 User Registration and Authentication**

- Implement a secure registration system:
  - Collect username, email, and password.
  - Validate inputs and handle errors gracefully.
- Authentication:
  - Secure login with hashed passwords (e.g., using bcrypt).
  - Implement session management and secure cookies.
- Password recovery and email verification can be added in future iterations.

### **4.2 User Roles**

- **Regular Users**:
  - Access to evaluation tasks.
  - Ability to update profile preferences.
- **Administrators**:
  - All regular user capabilities.
  - Additional permissions to:
    - Ban or unban users.
    - Access data export functionalities.
    - View user statistics and manage content.

### **4.3 User Profiles**

- Store user preferences:
  - Preferred working language for tasks.
  - Interface language (English or Icelandic).
- Allow users to update their profile information.

---

## **5. Multilingual Support**

### **5.1 Data Management**

- Use a single dataset with language tags for all content.
- Implement ID strings to link original prompts to their sources (e.g., OpenAssistant).

### **5.2 Supported Languages**

- **Working Languages**:
  - Icelandic, Danish, Norwegian Bokmål, Norwegian Nynorsk, Swedish, Dutch, German, Faroese.
- **Interface Languages**:
  - English and Icelandic.
- Design the system to easily add more interface languages:
  - Use a translation framework or maintain translation files.

---

## **6. Database Schema Design**

Design the database to accommodate all user data, prompts, responses, evaluations, and conversations.

### **6.1 Models**

- **User**:
  - id: Unique identifier for the user (Integer, primary key)
  - username: User's chosen display name (String, unique)
  - email: User's email address (String, unique)
  - password_hash: Hashed version of the user's password (String)
  - role: User's role in the system (String, e.g., 'regular', 'admin')
  - preferred_language: User's preferred working language for tasks (String)
  - interface_language: User's preferred language for the interface (String, limited to 'English' or 'Icelandic')
  - created_at: Timestamp of when the user account was created
  - last_login: Timestamp of the user's last login
- **Prompt**:
  - ID: Unique identifier for the prompt
  - parent_id: ID of the prompt this prompt is responding to (null if it's the start of a conversation)
  - language: The language of the prompt
  - prompt_text: The actual content of the prompt
  - is_synthetic: Boolean indicating whether the prompt is human-written (false) or synthetic (true)
  - source_id: ID of the original prompt if this is a synthetic version (null if human-written)
  - model_used: The model used to generate the prompt (null if human-written)
  - source_dataset: The dataset the prompt originated from (if applicable, null otherwise)
  - is_revision: Boolean indicating whether this prompt is a revision of another prompt
  - revised_prompt_id: ID of the prompt that was revised (null if not a revision)
  - revision_author_type: Enum ('human', 'model') indicating who made the revision
  - revision_author_id: ID of the user or model that made the revision
  - created_at: Timestamp of when the prompt was created
  - reference_ids: Array of reference IDs that were used to generate the prompt
  - reference_prompt_prefix: The prefix of the prompt that was used to generate the prompt (can be empty)
- **Reference**:
  - ID: Unique identifier for the reference
  - reference_link: Link to the original source of the reference
  - reference_text: The actual content of the reference
  - created_at: Timestamp of when the reference was created
- **Evaluation**:
  - ID: Unique identifier for the evaluation
  - user_id: ID of the user who performed the evaluation if it was a human, otherwise it should be null
  - model_id: ID of the model that performed the evaluation if it was a model, otherwise it should be null
  - item_evaluated_id: ID of the prompt being evaluated
  - evaluation_type: Enum ('quality_score', 'serious_humorous', 'ordinary_creative', 'rude_polite', 'violent_harmless', 'unfriendly_friendly', 'contains_pii', 'is_spam', 'not_appropriate', 'hate_speech', 'sexual_content', 'not_child_friendly', 'contains_bias', 'contains_sarcasm','difficulty_level','topic_tags')
  - score_number: Integer score given in the evaluation (can be null)
  - score_text: Textual score given in the evaluation (can be empty)
  - created_at: Timestamp of when the evaluation was created
- **Ranking**:
  - ID: Unique identifier for the ranking
  - user_id: ID of the user who performed the ranking if it was a human, otherwise it should be null
  - model_id: ID of the model that performed the ranking if it was a model, otherwise it should be null
  - item_ranked_ids: Array of IDs of the responses being ranked
  - created_at: Timestamp of when the ranking was created


### **6.2 Indexing**

- Create indexes on frequently queried fields (e.g., user ID, prompt ID, language).

---

## **7. Prompt Evaluation Task**

### **7.1 Prompt Generation**

- Use the Llama 3.1 model via together.ai API to create synthetic prompts.
- Generate four synthetic versions of each prompt in each language.
- Develop a prompt reformulation template to ensure consistency.
- Implement CSV upload functionality:
  - Columns: "Original", "Target Language", "Reformulated".
  - Validate and process uploads securely.

### **7.2 Prompt Display**

- Show the original English prompt for reference.
- Display the reformulated prompts in the user's preferred working language.

### **7.3 Prompt Selection and Improvement**

- Allow users to select their preferred prompt from up to a configurable maximum number.
  - Randomize if more synthetic prompts are available.
- Enable users to rewrite and improve the selected prompt.
  - Store revisions separately, linked to the synthetic prompt.

---

## **8. Response Evaluation Task**

### **8.1 Response Generation**

- Use the Llama 3.1 420B model via together.ai API to generate responses.
- For each prompt, create eight responses:
  1. **Without Retrieval**:
     - Short, longer, informative/serious, and funny responses.
  2. **With Retrieval (RAG Approach)**:
     - Same variations as above.

### **8.2 Task Structure**

- Evaluate responses with and without retrieval together.
- Display the prompt and all synthetic responses in the user's language.

### **8.3 Response Ranking**

- Users rank the responses by overall quality using a drag-and-drop interface.
- No specific criteria; based on user's judgment.

### **8.4 Response Improvement**

- Allow users to rewrite the best response.
- Store user improvements separately.

### **8.5 Source Document Display (for RAG Responses)**

- Include a collapsible section showing source documents.
- Highlight documents containing the correct answer.

---

## **9. Evaluation Tasks Interface**

### **9.1 Likert Scale Evaluations (5-point Scale)**

- **Criteria**:
  1. Quality Score: Low to High
  2. Seriousness: Serious to Humorous
  3. Creativity: Ordinary to Creative
  4. Politeness: Rude to Polite
  5. Safety: Violent to Harmless
  6. Friendliness: Unfriendly to Friendly
- Implement a user-friendly interface for rating.
  7. Difficulty level: Very easy to very hard

### **9.2 Binary Properties**

- **Attributes**:
  - Contains PII
  - Is Spam
  - Not Appropriate
  - Hate Speech
  - Sexual Content
  - Not Appropriate for Children
  - Contains Bias
  - Contains Sarcasm
- Provide checkboxes or toggles for users to mark applicable properties.

### **9.3 Textual Properties**

- **Attributes**:
  - Topic Tags (list of tags)

### **9.4 Task Focus**

- Each annotator focuses on one evaluation task at a time.
- Allow users to select the evaluation task they wish to perform.

---

## **10. Extended Conversation Feature**

### **10.1 User Interaction**

- Users can flag a response to initiate an extended conversation.
- Allow users to add their own responses, supporting open-ended exchanges.

### **10.2 Synthetic Response Generation**

- Use the entire conversation to generate a new synthetic response.
- The new response is evaluated separately in the response evaluation task.

### **10.3 Conversation Management**

- Store the conversation history (possible by tracing parent_ids of prompts).
- Enable users to navigate and review previous conversation turns.

---

## **11. User Interface Enhancements**

### **11.1 Navigation Bar**

- **Components**:
  - Project name/logo linking to the homepage.
  - Task-specific buttons (e.g., "Rank & Revise," "Evaluate").
  - Profile menu with options to view and edit settings.
  - Login/Register or Logout options.

### **11.2 Front Page**

- **Logged-In Users**:
  - Display project status and personal statistics.
  - Leaderboards for users and languages per task.
  - Action buttons to enter tasks.
- **Logged-Out Users**:
  - Overview of the project.
  - Instructions on how to participate.
  - Registration and login prompts.

### **11.3 General Layout**

- **Responsive Design**:
  - Ensure the interface adapts to various screen sizes.
  - Mobile-friendly layouts using TailwindCSS utilities.
- **Navigation**:
  - Clear and intuitive navigation between tasks and sections.

### **11.4 Task Interfaces**

- **Prompt Evaluation**:
  - Display original and synthetic prompts.
  - Selection mechanism for choosing preferred prompts.
  - Text area for prompt improvement.
- **Response Evaluation**:
  - Display prompt and responses.
  - Drag-and-drop ranking interface.
  - Option to rewrite the best response.
- **Evaluation Tasks**:
  - Clear presentation of criteria.
  - Interactive elements for ratings and property selection.

### **11.5 Language Selection**

- **Profile Settings**:
  - Options to set working and interface languages.
- **Interface Application**:
  - Immediate application of language preferences across the site.

---

## **12. Administrator Interface**

### **12.1 User Management**

- View a list of all users with search and filter options.
- Ban or unban users:
  - Change user status and prevent access if banned.
- View user contributions and activity logs.

### **12.2 Data Export Functionality**

- Export data in JSON format.
- Options to select data types (e.g., prompts, responses, evaluations).
- Ensure sensitive information is excluded from exports.

### **12.3 Dashboard**

- Overview of system statistics:
  - Total number of users, prompts, responses, evaluations.
- Monitoring tools for system performance.

---

## **13. Performance and Scalability Enhancements**

### **13.1 Database Optimization**

- Create indexes on frequently queried columns (e.g., user ID, language).
- Optimize queries using SQLAlchemy's query optimization features.

### **13.2 Caching Mechanisms**

- Implement caching for static content and frequently accessed data.
- Use Flask-Caching or similar libraries.

### **13.3 Asynchronous Processing**

- Use asynchronous tasks for API interactions with together.ai.
  - Integrate Celery with a message broker like Redis.
- Provide user feedback for ongoing processes.

### **13.4 Concurrent User Handling**

- Configure the application to handle multiple concurrent users.
- Use a production server (e.g., Gunicorn) with multiple worker processes.

---

## **14. Security Measures**

### **14.1 Authentication and Authorization**

- Use secure password hashing (e.g., bcrypt).
- Implement session management with protection against session hijacking.

### **14.2 Web Vulnerabilities Protection**

- **XSS Protection**:
  - Sanitize all user inputs.
  - Use template engines that auto-escape outputs.
- **CSRF Protection**:
  - Implement CSRF tokens for form submissions.
- **Input Validation**:
  - Validate and sanitize data on both client and server sides.

### **14.3 Data Transmission and Storage**

- Enforce HTTPS for all data transmission.
- Secure sensitive data storage:
  - Avoid storing sensitive information in plain text.

### **14.4 Regular Security Audits**

- Perform regular code reviews focusing on security.
- Keep dependencies up-to-date to patch known vulnerabilities.

---

## **15. Deployment and Maintenance**

### **15.1 Continuous Integration and Deployment**

- Set up CI/CD pipelines using tools like GitHub Actions or Travis CI.
- Automate testing and deployment to Heroku.

### **15.2 Logging and Monitoring**

- Implement logging for errors, user activities, and system events.
- Use monitoring tools to track application performance.

### **15.3 Backups and Data Management**

- Schedule regular backups of the database.
- Plan for data restoration procedures in case of data loss.

### **15.4 Documentation**

- Maintain comprehensive documentation for:
  - Codebase and development practices.
  - Deployment procedures.
  - User guides and administrative manuals.

---

## **16. Future Considerations**

### **16.1 Adding More Interface Languages**

- Design the system to support easy addition of new interface languages.
- Use translation files and possibly community contributions for translations.

### **16.2 Scalability**

- Plan for scaling the application to handle increased user load.
- Consider containerization (e.g., Docker) for easier deployment and scaling.

### **16.3 Integration with Other AI Models or Services**

- Abstract the AI model interaction layer to support multiple models.
- Explore integrating with other services for enhanced features.

---

By following this detailed specification and implementation roadmap, the development team can efficiently build a robust, secure, and user-friendly web application for prompt and response evaluation. The prioritized feature implementation ensures that foundational aspects are established before layering on additional functionalities.