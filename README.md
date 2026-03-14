# Hotel Management System

A small but complete Hotel Management System application built using Flask, HTML, Bootstrap, and jQuery, adhering perfectly to the provided project guidelines.

## Features
- **Project Structure**: Clean layout separating static files, templates, and backend logic.
- **Frontend Design**: Built with semantic HTML5 tags, Bootstrap 5 components (grid, cards, navbar, forms), and minimal custom CSS for branding.
- **Frontend Behavior**: Uses jQuery to handle client-side form validation (e.g., check-out date verification) and simple UI effects (modal/alert slide downs).
- **Backend Setup**: Powered by Flask, utilizing Jinja2 templates (`{% for %}`, `{{ variable }}`).
- **Database**: SQLite integrated using Flask-SQLAlchemy to handle Rooms and Bookings entities.

## Future Screens (To Add Screenshots)
*Add your screenshots here after running the project locally!*
> Example: `![Home Page](./docs/home.jpg)`

## Local Development Setup

1. **Clone this repository** (or download the directory)
2. **Create and Activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the Application**:
   ```bash
   python app.py
   ```
   *Note: The SQLite database (`database.db`) will be automatically generated with some dummy room data on the first run.*
5. **Visit the Site**:
   Open a browser and navigate to `http://127.0.0.1:5000/`.

## Author & Git Workflow
Developed with structured Git commits using distinct `feature/backend-setup` and `feature/frontend-setup` branches as requested, which were subsequently merged into `main`.
