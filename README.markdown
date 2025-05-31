# LifeLedger

LifeLedger is a Django-based web application designed to help users document and reflect on their life experiences through a journaling platform. It integrates AI-powered mood analysis to provide deeper insights into users' emotional patterns and well-being.

## Features

- **User Authentication**: Secure sign-up, login, and logout functionality. Includes email verification and password reset options.
- **Profile Management**: Users can create and update their profiles, including personal information and profile pictures.
- **Journaling**: Create, read, update, and delete journal entries. Each entry can include a title, content, and associated mood.
- **AI-Powered Mood Analysis**: Utilizes AI to analyze the sentiment of journal entries and suggest a mood, which users can confirm or override.
- **Dashboard**: Provides an overview of recent journal entries and mood trends.
- **Responsive Design**: Ensures a seamless experience across various devices using Tailwind CSS.
- **Dark Mode**: Supports a dark theme for user preference.
- **AJAX Operations**: Enhances user experience with asynchronous updates for actions like deleting journal entries without full page reloads.

## Technologies Used

- **Backend**: Django, Python
- **Frontend**: HTML, CSS, JavaScript (including **AJAX** for dynamic content), Tailwind CSS
- **Database**: PostgreSQL
- **Asynchronous Tasks**: Celery (with **Redis** as the message broker) for AI processing and other background tasks.
- **AI**: _(Specify the AI model/library used, e.g., NLTK, spaCy, or a cloud-based service like OpenAI GPT. From your `ai_services/tasks.py`)_

## Setup and Installation

1.  **Clone the repository**:

    ```bash
    git clone [https://github.com/Sina-Amare/LifeLedger.git](https://github.com/Sina-Amare/LifeLedger.git)
    cd LifeLedger
    ```

2.  **Create and activate a virtual environment**:

    ```bash
    python -m venv venv
    # On Windows
    # venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    _(Ensure you have a `requirements.txt` file for Python dependencies, including `redis` and `celery`)_

    ```bash
    pip install -r requirements.txt
    npm install # For Tailwind CSS and other frontend dependencies
    ```

4.  **Configure environment variables**:
    Create a `.env` file in the root directory by copying `.env.example` (if you create one) or by adding the necessary configurations manually.
    Key variables include: `SECRET_KEY`, `DEBUG`, `DATABASE_URL`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `CELERY_BROKER_URL`, and any AI service API keys.
    Example `.env` structure:

    ```env
    SECRET_KEY='your_super_secret_key_here'
    DEBUG=True
    DATABASE_URL='postgresql://USER:PASSWORD@HOST:PORT/DB_NAME' # Example for PostgreSQL

    EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST='smtp.example.com'
    EMAIL_PORT=587
    EMAIL_USE_TLS=True
    EMAIL_HOST_USER='your_email@example.com'
    EMAIL_HOST_PASSWORD='your_email_app_password'

    # Celery with Redis Broker
    CELERY_BROKER_URL='redis://localhost:6379/0'
    CELERY_RESULT_BACKEND='redis://localhost:6379/0' # Optional: if you store Celery results

    # Example for OpenAI API Key (if used)
    # OPENAI_API_KEY='your_openai_api_key'
    ```

5.  **Apply migrations**:

    ```bash
    python manage.py migrate
    ```

6.  **Create a superuser** (for accessing the Django admin panel):

    ```bash
    python manage.py createsuperuser
    ```

7.  **Compile Tailwind CSS**:
    To build the CSS once:

    ```bash
    npm run build:css
    ```

    To watch for changes during development:

    ```bash
    npm run watch:css
    ```

    _(These commands assume you have `build:css` and `watch:css` scripts defined in your `package.json` similar to common Tailwind setups.)_

8.  **Run the development server**:

    ```bash
    python manage.py runserver
    ```

    The application will typically be available at `http://127.0.0.1:8000/`.

9.  **Run Celery worker** (for asynchronous AI tasks, in a separate terminal):
    Ensure your Redis server is running.
    ```bash
    celery -A LifeLedger worker -l info
    ```

## Contributing

Contributions are welcome! Please follow these steps:

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request
