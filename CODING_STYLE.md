# Coding Style Guidelines

This document outlines the coding standards and guidelines for the `battle-score` project. Adhering to these guidelines ensures code consistency, readability, and maintainability.

## General Configuration

The project uses `.editorconfig` to maintain consistent coding styles between different editors and IDEs.

- **Charset**: UTF-8
- **End of Line**: LF
- **Insert Final Newline**: Yes
- **Trim Trailing Whitespace**: Yes

## Naming Conventions & Language

### Language
- **Code**: English (variables, functions, classes, etc.).
- **Comments**: English.
    - Only add comments for complex code or business logic details.
    - Do not repeat what the code says.
- **Strings**: French (used as translation keys in gettext) for user-facing text.

### Naming Conventions
- **Python**:
    - Variables/Functions/Methods: `snake_case`
        - Names must be short and explicit.
        - Do not include types in names (e.g., avoid `str_name`, `list_items`).
    - Classes: `PascalCase`
    - Constants: `UPPER_CASE`
    - Filenames: `snake_case`
- **JavaScript/Vue**:
    - Variables/Functions: `camelCase`
    - Classes/Components: `PascalCase`
    - Constants: `UPPER_CASE`
    - Filenames: `PascalCase` for components, `camelCase` for utilities.

## Python

### Tools & Linters

We use the following tools to enforce code quality and style. These are listed in `reqs/dev.txt`.

- **Ruff**: As a code formatter (like black), linter (like flake8) and other things (isort, bandit).
- **Pyright**: Static type checker (usage is strongly recommended but not mandatory).

### Formatting Rules

- **Line Length**: The project currently allows for long lines (up to 150 characters as per `.isort.cfg`).
    - *Note*: `isort` is configured with `multi_line_output=5` (Hanging Grid Grouped).
- **Indentation**: 4 spaces.

## Imports

Imports are sorted by `ruff`. The configuration is in `ruff.toml`.
- **Order**: Standard library -> Third party -> Local application.
- **Style**: Hanging Grid Grouped.

## Django

### Models

- **Inheritance**: All models should inherit from `core.models.BaseModel` instead of `django.db.models.Model`.
    - `BaseModel` provides standard fields like `date_created` and `date_updated`.
    - It also includes helpers (`diff()` for tracking changes, `grab()` for fetching objects, ...).
- **Enums**: All enums should be defined in the model using `core.utils.enum`.
<!-- - **Sealing**: The project uses `django-seal`. Models can be sealed to prevent accidental queries. -->

### Settings
- **Organisation**:
    - All settings should be defined in `core/settings/base.py`.
    - All specific environments must inherit from `core/settings/base.py`.
    - Production specific settings should be defined in `core/settings/prod.py`.
    - Development specific settings should be defined in `core/settings/dev.py`.
    - Test specific settings should be defined in `core/settings/test.py`.
- **Environment variables**: Must use library `decouple` to define, load, initialize, and validate environment variables.

### Forms
- **Inheritance**: Prefer using ModelForm whenever possible to stick to model validators.

### Views
- **Inheritance**: Prefer using TemplateView andFormView whenever possible.

### Security
- **Authentication**: Use Django authentication.
- **Authorization**: Use Django permissions.
- **Cryptography**: Use Django cryptography.


## Testing

Guidelines for writing tests in the project:

- **Inheritance**: Always inherit from an internal test class located in `core/testing/testcase.py` (`TestCase` or `TransactionTestCase`).
- **Structure**: Always create 1 test class per View/Controller/Model and create one test method per use case.
- **Naming**: Test classes must always be named `Test<ClassName>` with `ClassName` being the name of the View/Controller/Model. Test methods must always be named `test_<use_case>` with `use_case` being the name of the use case.
- **Data Initialization**: Use `setUpTestData` (class method) instead of `setUp` to initialize data whenever possible. This improves test performance by creating data once per class.
- **Assertions**: Prefer internal control methods defined in `TestCase` class over standard assertions (e.g., `assertAttributesEqual`, `assertNumQueries`, `assertApiException`, `assert_model_differences`, `assertApiEqual`).
- **Side effects**: always control side effects in tests (`assertNumQueries` for db queries, `assert_model_differences` for created/deleted rows, `assert_nb_slacks` for slack messages, `assert_nb_emails` for emails, `assert_crm_equal` for CRM changes, ...).
- **Mockers**: always use mockers for external services (e.g., `pytest-mocker` for mocking external services).
- **Fixtures**: always use fixtures to initialize data (e.g., `pytest-factoryboy` for fixtures).

## Frontend (django forms & javascript & CSS)

### File Types
- **JavaScript**: `*.js`
- **TypeScript**: `*.ts` (preferred)
- **Styles**: `*.css` (Vanilla CSS + Tailwind CSS)

### Formatting
- **Indentation**:
    - JS/TS/CSS: 4 spaces.
    - HTML: 2 spaces.
    - Defined in `.editorconfig`.

### Frameworks
- **TailwindCSS**: Used for utility-first styling.

### Translations
- **Translation**: Use `gettext` for translations.

### Stack
- **HTMX**: Used for client-side interactions.
- **Websockets**: Used for real-time interactions (new/updated participant/match/score, ...).
- **Django Forms**: Use 1 View per form and respect project structure.

### UX
- **Responsive Design**: Use TailwindCSS for responsive design.
- **Accessibility**: Use ARIA roles and attributes.
- **Performance**: Use lazy loading for images and videos.
- **Graphic charts**: Use Chart.js for graphic charts.

## Git & Workflow

### Branching
- **Release Branch**: `main`.
- **Development**: Feature branches should be merged into the development branch (often `dev` or similar, though `main` is the release target in Makefile).

### Releases
- Releases are managed via `Makefile` targets (`make release`).
- Versioning is handled in `project.toml`.

### Commit Messages
- Write clear, concise commit messages.
- Use the imperative mood ("Add feature" not "Added feature").

## Project Structure

The project follows a standard Django app structure with dedicated API and Web layers.

### Directory Layout

- **Root**: Contains configuration files and app directories.
    - `Makefile`: Build and release management.
    - `manage.py`: Django management script.
    - `reqs/`: Python dependencies.
    - `docs/`: Documentation.
    - `static/`: Static files (CSS, JS, images, ...).
    - `templates/`: Django templates.
    - `core/`: Project main folder including django settings (in `settings/`) and urls root (in `urls.py`).
- **Apps** (e.g., `core`, `inventory`):
    - `models.py`: Database models (inherit from `core.models.BaseModel`).
    - `admin.py`: Django Admin configuration.
    - `controllers.py`: Business logic controllers.
    - `api/`: Django Rest Framework (DRF) specific code.
        - `serializers.py`: Data serialization.
        - `views.py`: API endpoints (ViewSets or Views).
        - `urls.py`: API routing.
        - `tests/`: API specific tests.
    - `web/`: Web pages (Django templates, views).
        - `forms.py`: Web forms.
        - `views.py`: Web views.
        - `urls.py`: Web routing.
        - `tests/`: Web specific tests.
        - `templates/`: App web templates.
    - `tests/`: Model and business logic tests.
        - `mixins.py`: App specific mixins for tests.
        - `test_*.py`: App specific tests.
    - `migrations/`: Database migrations.
    - `management/commands/`: Management commands.
    - `templates/`: Django templates.
    - `assets/`: App static assets (images, videos, etc...).
