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

## Screenshots

_(This is where you can add screenshots of your application. See the "How to Add Screenshots to Your README" section below for instructions.)_

<!-- Example:
![Login Page](path/to/your/screenshot/login_page.png)
![Dashboard View](path/to/your/screenshot/dashboard.png)
-->

## Technologies Used

- **Backend**: Django, Python
- **Frontend**: HTML, CSS, JavaScript, Tailwind CSS
- **Database**: SQLite (default, configurable)
- **Asynchronous Tasks**: Celery (with a broker like Redis or RabbitMQ - please specify which one you are using if not the default for Celery) for AI processing.
- **AI**: _(Specify the AI model/library used, e.g., NLTK, spaCy, or a cloud-based service like OpenAI GPT. From your `ai_services/tasks.py` it seems you might be using an external API, possibly OpenAI. Please update this section with the specific service.)_

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
    _(Ensure you have a `requirements.txt` file for Python dependencies)_

    ```bash
    pip install -r requirements.txt
    npm install # For Tailwind CSS and other frontend dependencies
    ```

4.  **Configure environment variables**:
    Create a `.env` file in the root directory by copying `.env.example` (if you create one) or by adding the necessary configurations manually.
    Key variables include: `SECRET_KEY`, `DEBUG`, `DATABASE_URL`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and any AI service API keys.
    Example `.env` structure:

    ```env
    SECRET_KEY='your_super_secret_key_here'
    DEBUG=True
    DATABASE_URL='sqlite:///db.sqlite3' # Or your preferred database connection string

    EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST='smtp.example.com'
    EMAIL_PORT=587
    EMAIL_USE_TLS=True
    EMAIL_HOST_USER='your_email@example.com'
    EMAIL_HOST_PASSWORD='your_email_app_password'

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
    Ensure your message broker (e.g., Redis or RabbitMQ) is running and configured in `settings.py`.
    ```bash
    celery -A LifeLedger worker -l info
    ```

## Project Structure

LifeLedger/
├── LifeLedger/ # Django project configuration (settings, main urls, wsgi, asgi, celery)
├── accounts/ # Handles user registration, login, authentication
├── ai_services/ # Manages AI-powered features like mood analysis
├── journal/ # Core application for journal entries
├── user_profile/ # Manages user profiles
├── static/ # Project-wide static files (CSS, JS, images for frontend)
├── staticfiles_collected/ # For production, collected by collectstatic
├── templates/ # Base HTML templates for the project
├── venv/ # Python virtual environment (typically gitignored)
├── .env # Environment variables (gitignored)
├── .env.example # Example for environment variables
├── .gitignore # Specifies intentionally untracked files that Git should ignore
├── manage.py # Django's command-line utility
├── package.json # Lists frontend dependencies and scripts (npm)
├── package-lock.json # Records exact versions of frontend dependencies
├── postcss.config.js # Configuration for PostCSS (used by Tailwind)
├── README.md # This file
├── requirements.txt # Python dependencies (pip)
└── tailwind.config.js # Configuration for Tailwind CSS

## How to Add Screenshots to Your README

You can easily add images and screenshots to your README file to showcase your application. Here's how:

1.  **Take a Screenshot**: Capture an image of your application. You can use built-in OS tools (e.g., Snipping Tool on Windows, Shift+Command+4 on macOS) or other preferred software.

2.  **Place the Screenshot in Your Repository**:

    - Create a dedicated folder for images in your repository, for example, `docs/images/` or `screenshots/`. This helps keep your project organized.
    - Add your screenshot files (e.g., `login_page.png`, `dashboard_view.gif`) to this folder.

3.  **Commit and Push the Images**:
    Add the image folder and its contents to your Git repository, commit the changes, and push them to GitHub.

    ```bash
    git add docs/images/your_screenshot.png
    # or add the whole folder
    git add docs/images/
    git commit -m "Add application screenshots"
    git push
    ```

4.  **Embed the Image in Your README.md**:
    Use Markdown's image syntax to display the image. The syntax is:
    `![Alt text](path/to/image.png)`

    - **`Alt text`**: This is a descriptive text for the image, which is important for accessibility (e.g., for screen readers) and will be displayed if the image cannot be loaded.
    - **`path/to/image.png`**: This is the relative path to your image file _from the root of your repository_.

    **Example**:
    If you created a folder named `docs/images/` in the root of your `LifeLedger` repository and added `login_page.png` to it, the Markdown would be:

    ```markdown
    ![LifeLedger Login Page](docs/images/login_page.png)
    ```

    You can also use animated GIFs for short demos:

    ```markdown
    ![LifeLedger Feature Demo](docs/images/feature_demo.gif)
    ```

5.  **Using Absolute URLs (e.g., from GitHub Issues or external hosting)**:
    Alternatively, you can upload your image to a GitHub issue comment (then copy the generated image URL) or an image hosting service and use the absolute URL:

    ```markdown
    ![Alt text](https://absolute_url_to_your_image.png)
    ```

    However, keeping images within the repository is generally preferred for longevity and to ensure they are always available with your project code.

6.  **Preview**: After adding the Markdown syntax to your `README.md` file, commit and push the changes. GitHub will render the images directly in your repository's main page. You can also preview Markdown files locally using various editors (like VS Code) that have Markdown preview capabilities.

## Contributing

Contributions are welcome! Please follow these steps:

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## License

This project is licensed under the MIT License. (Consider adding a `LICENSE` file to your repository with the MIT License text if you haven't already).

## Contact

Sina Amare

- Email: sina.amare.dev@gmail.com
- GitHub: [Sina-Amare](https://github.com/Sina-Amare)

Project Link: [https://github.com/Sina-Amare/LifeLedger](https://github.com/Sina-Amare/LifeLedger)
