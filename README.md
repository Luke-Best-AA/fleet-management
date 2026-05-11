# Fleet Management

A web-based fleet management application for tracking vehicles, maintenance, mileage and driver assignments across multiple depot locations. Built for internal use within a roadside assistance organisation, it replaces manual spreadsheet-based tracking with a centralised system where drivers and administrators interact with the same data.

The application manages the full lifecycle of fleet vehicles — from registration and daily mileage tracking, through maintenance scheduling, to retirement and deletion request workflows with approval chains.

## Live Application

| | |
|---|---|
| **Live URL** | *To be added after production deployment* |
| **Demo admin login** | `admin` / `admin123!` |
| **Demo standard user login** | `driver1` / `driver123!` |

> Demo credentials are created by the seed script. Do not use these in production.

## Repository Contents

```
├── app/
│   ├── config.py                  # Application settings (env-driven)
│   ├── main.py                    # FastAPI app factory, middleware
│   ├── db/                        # Database engine, base model, session
│   ├── models/                    # SQLAlchemy ORM models
│   ├── schemas/                   # Pydantic validation schemas
│   ├── routes/
│   │   ├── web/                   # HTML page routes (auth, vehicles, admin, etc.)
│   │   └── api/                   # JSON API endpoints
│   ├── services/                  # Business logic layer
│   ├── security/                  # CSRF, password hashing, access control
│   ├── templates/                 # Jinja2 HTML templates
│   ├── static/                    # CSS, JS, vendor assets
│   ├── utils/                     # Template helpers, flash messages, form parsing
│   └── exceptions/                # Custom exception classes
├── tests/                         # Automated test suite (pytest)
├── diagrams/                      # PlantUML architecture and flow diagrams
├── _my_context/                   # Development reference files (gitignored)
├── docker-compose.yml             # Multi-container setup (app + Postgres + Redis)
├── Dockerfile                     # Application container image
├── seed.py                        # Database seed script with sample data
├── requirements.txt               # Python dependencies
└── README.md
```

## Features

### Core CRUD Operations
- **Vehicles** — browse, add, edit, delete, retire/unretire fleet vehicles
- **Maintenance records** — log maintenance with categories, costs, mileage and notes
- **Mileage records** — record odometer readings with admin override capability
- **Locations** — manage depot locations with addresses and region groupings
- **Users** — admin user management with role and location assignment

### Workflow Features
- Retirement request workflow with approval/rejection by admins
- Deletion request workflow for maintenance and mileage records
- Mileage recalculation when records are added, edited or deleted
- Vehicle recall (unretire) for previously retired vehicles

### Authentication and Authorisation
- User registration with role selection (standard/admin)
- Login with session-based authentication (Redis-backed)
- Session fingerprinting (IP + User-Agent binding)
- Account lockout after failed login attempts
- Role-based access control enforced at route level

### User Experience
- Dashboard with vehicle stats, pending requests and recent activity
- Client-side table filtering, sorting and search
- Dark mode with system preference detection
- Flash messages for success/error feedback
- Confirmation before destructive actions
- Responsive design for mobile and desktop
- Clean URL bar (navigation params stripped after use)

### Admin Features
- Audit log of all administrative actions
- Page visit analytics with charts (daily trend, hourly distribution)
- User management (create, edit, deactivate)
- Location and maintenance category management

## Technology Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.12 |
| **Web framework** | FastAPI with Starlette |
| **Templating** | Jinja2 |
| **Database** | PostgreSQL 16 |
| **ORM** | SQLAlchemy 2.x (mapped columns) |
| **Session store** | Redis 7 |
| **Validation** | Pydantic v2 |
| **Password hashing** | bcrypt via passlib |
| **Frontend** | Bootstrap 5, Bootstrap Icons, Chart.js |
| **Testing** | pytest, httpx (TestClient) |
| **Linting / formatting** | Ruff |
| **Security scanning** | Bandit, pip-audit |
| **Containerisation** | Docker, Docker Compose |
| **Deployment** | *To be confirmed* |

## Database Design

The application uses a relational PostgreSQL database with 10 tables. All tables use auto-incrementing integer primary keys and include `created_at`/`updated_at` timestamps.

### Tables

#### users
| Field | Type | Purpose |
|---|---|---|
| id | SERIAL PK | Unique identifier |
| username | VARCHAR(100) UNIQUE | Login credential |
| email | VARCHAR(255) UNIQUE | Contact email |
| password_hash | VARCHAR(255) | bcrypt-hashed password |
| role | VARCHAR(20) | `admin` or `standard` |
| employee_number | VARCHAR(50) UNIQUE | Organisation employee ID |
| first_name, last_name | VARCHAR(100) | Display name |
| location_id | INTEGER FK → locations | Assigned depot |
| is_active | BOOLEAN | Soft deactivation flag |
| last_password_change_at | TIMESTAMPTZ | Password age tracking |

#### vehicles
| Field | Type | Purpose |
|---|---|---|
| id | SERIAL PK | Unique identifier |
| registration_number | VARCHAR(20) UNIQUE | Vehicle reg plate |
| fleet_reference | VARCHAR(50) UNIQUE | Internal fleet code |
| vehicle_type | VARCHAR(50) | `roadside_van`, `flat_loader_lorry`, `patrol_van` |
| make, model | VARCHAR(100) | Vehicle manufacturer and model |
| year | INTEGER | Year of manufacture |
| status | VARCHAR(30) | `active`, `pending_retirement`, `retired` |
| current_mileage | INTEGER | Latest calculated mileage |
| location_id | INTEGER FK → locations | Assigned depot |
| primary_driver_user_id | INTEGER FK → users | Assigned driver |
| retirement_reason | TEXT | Reason if retired |

#### locations
| Field | Type | Purpose |
|---|---|---|
| id | SERIAL PK | Unique identifier |
| name | VARCHAR(150) UNIQUE | Depot name |
| code | VARCHAR(50) UNIQUE | Short code (e.g. LON) |
| region | VARCHAR(100) | Geographic region |
| address_line_1, address_line_2 | VARCHAR(200) | Street address |
| city | VARCHAR(100) | City |
| postcode | VARCHAR(20) | Postal code |
| is_active | BOOLEAN | Whether depot is operational |

#### maintenance_records
| Field | Type | Purpose |
|---|---|---|
| id | SERIAL PK | Unique identifier |
| vehicle_id | INTEGER FK → vehicles | Associated vehicle |
| category_id | INTEGER FK → maintenance_categories | Type of work |
| logged_by_user_id | INTEGER FK → users | Who recorded it |
| maintenance_date | DATE | When work was done |
| mileage_at_time | INTEGER | Odometer at time of work |
| notes | TEXT | Additional details |
| cost | NUMERIC(10,2) | Cost of work |

#### maintenance_categories
| Field | Type | Purpose |
|---|---|---|
| id | SERIAL PK | Unique identifier |
| name | VARCHAR(100) UNIQUE | Category name |
| description | TEXT | What this category covers |
| requires_notes | BOOLEAN | Whether notes are mandatory |

#### mileage_records
| Field | Type | Purpose |
|---|---|---|
| id | SERIAL PK | Unique identifier |
| vehicle_id | INTEGER FK → vehicles | Associated vehicle |
| recorded_by_user_id | INTEGER FK → users | Who recorded it |
| reading_value | INTEGER | Odometer reading |
| recorded_at | TIMESTAMPTZ | When recorded |
| is_admin_override | BOOLEAN | Whether admin bypassed validation |
| override_reason | TEXT | Required if admin override |

#### retirement_requests
| Field | Type | Purpose |
|---|---|---|
| id | SERIAL PK | Unique identifier |
| vehicle_id | INTEGER FK → vehicles | Vehicle to retire |
| requested_by_user_id | INTEGER FK → users | Who requested |
| reason | TEXT | Why retirement is needed |
| status | VARCHAR(20) | `pending`, `approved`, `rejected` |
| reviewed_by_user_id | INTEGER FK → users | Admin who reviewed |
| review_notes | TEXT | Admin response notes |

#### deletion_requests
| Field | Type | Purpose |
|---|---|---|
| id | SERIAL PK | Unique identifier |
| target_type | VARCHAR(30) | `maintenance_record` or `mileage_record` |
| target_id | INTEGER | Polymorphic reference to target record |
| requested_by_user_id | INTEGER FK → users | Who requested |
| reason | TEXT | Why deletion is needed |
| status | VARCHAR(20) | `pending`, `approved`, `rejected` |
| reviewed_by_user_id | INTEGER FK → users | Admin who reviewed |

#### audit_logs
| Field | Type | Purpose |
|---|---|---|
| id | SERIAL PK | Unique identifier |
| action | VARCHAR(50) | `create`, `update`, `delete`, `approve`, etc. |
| target_type | VARCHAR(50) | Entity type affected |
| target_id | INTEGER | ID of affected record |
| target_label | VARCHAR(255) | Human-readable label |
| details | TEXT | Additional context |
| user_id | INTEGER FK → users | Who performed the action |

#### page_visits
| Field | Type | Purpose |
|---|---|---|
| id | SERIAL PK | Unique identifier |
| user_id | INTEGER FK → users | Visitor |
| path | VARCHAR(500) | URL path visited |
| method | VARCHAR(10) | HTTP method |
| visited_at | TIMESTAMPTZ | When visited |

### Key Relationships

- **users** → locations (many-to-one): each user belongs to a depot
- **vehicles** → locations (many-to-one): each vehicle is assigned to a depot
- **vehicles** → users (many-to-one): each vehicle has a primary driver
- **maintenance_records** → vehicles, categories, users (many-to-one each)
- **mileage_records** → vehicles, users (many-to-one each)
- **retirement_requests** → vehicles, users (many-to-one, with separate reviewer)
- **deletion_requests** → users (polymorphic target_type + target_id)

## Entity Relationship Diagram

*To be added — see `diagrams/` folder for PlantUML source files.*

## Installation and Local Setup

### Prerequisites
- Python 3.12+
- PostgreSQL 16+
- Redis 7+
- Or: Docker and Docker Compose

### Option 1: Docker (recommended)

```bash
git clone <repo-url>
cd fleet-management
docker compose up --build
```

The application will be available at `http://localhost:8000`. The database is automatically created and can be seeded:

```bash
docker compose exec web python seed.py
```

### Option 2: Local development

```bash
git clone <repo-url>
cd fleet-management
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
# .venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

Create a `.env` file:

```
DATABASE_URL=postgresql://fleet_user:fleet_pass@localhost:5432/fleet_management
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
SECURE_COOKIES=false
```

Set up the database and seed data:

```bash
python seed.py
```

Run the application:

```bash
python run.py
```

The application will be available at `http://localhost:8000`.

## Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://localhost/fleet_management` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SECRET_KEY` | CSRF token HMAC signing key | `change-me-in-production` |
| `SESSION_LIFETIME_SECONDS` | Session TTL in seconds | `3600` |
| `MAX_LOGIN_ATTEMPTS` | Failed logins before lockout | `5` |
| `LOCKOUT_DURATION_SECONDS` | Lockout cooldown period | `900` |
| `SECURE_COOKIES` | Set cookie Secure flag (HTTPS only) | `true` |

> The `.env` file is excluded by `.gitignore`. Never commit real secrets.

## How to Run Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=app

# Run a specific test file
pytest tests/test_auth.py

# Run and stop on first failure
pytest -x
```

Tests use an in-memory SQLite database and require a running Redis instance for session tests.

## Test Coverage

The test suite contains **17 test files** covering:

| Area | Test File(s) | What is Tested |
|---|---|---|
| **Authentication** | `test_auth.py` | Login, registration, logout, session management, lockout |
| **Password security** | `test_auth.py` | Hashing, verification, salt uniqueness |
| **CSRF protection** | `test_auth.py` | Token generation, validation, expiry |
| **Vehicle CRUD** | `test_vehicle_service.py`, `test_vehicle_routes.py` | Create, read, update, delete vehicles |
| **Maintenance CRUD** | `test_maintenance_service.py`, `test_maintenance_routes.py` | Create, read, update, delete records |
| **Mileage CRUD** | `test_mileage_service.py`, `test_mileage_routes.py` | Record mileage, admin override validation |
| **User management** | `test_user_service.py` | Create users, role validation, duplicates |
| **Location management** | `test_location_service.py` | Location CRUD, uniqueness |
| **Retirement workflow** | `test_retirement_service.py`, `test_request_routes.py` | Request, approve, reject |
| **Deletion workflow** | `test_deletion_service.py`, `test_request_routes.py` | Request, approve, reject |
| **Business rules** | `test_business_rules.py` | Retired vehicle restrictions, mileage validation |
| **Schema validation** | `test_schemas.py` | Input validation, field constraints |
| **Admin routes** | `test_admin_routes.py` | Admin-only page access control |
| **API endpoints** | `test_api_routes.py` | JSON API responses |
| **Route access** | `test_routes.py` | Authentication redirects, 403 responses |

## Security Features

| OWASP Risk | Attack Example | Protection Implemented |
|---|---|---|
| **A01:2025 — Broken Access Control** | Standard user accessing `/admin/*` routes | Role checks enforced at route level; direct URL access blocked |
| **A02:2025 — Security Misconfiguration** | CSRF forged form submission | HMAC-signed CSRF tokens on all state-changing forms with time-based expiry |
| **A05:2025 — Injection** | SQL injection via search/login forms | SQLAlchemy ORM with parameterised queries; Pydantic input validation; Jinja2 auto-escaping prevents XSS |
| **A07:2025 — Authentication Failures** | Brute-force password guessing | bcrypt password hashing; account lockout after 5 failed attempts; 15-minute cooldown |
| **A09:2025 — Security Logging and Alerting Failures** | Undetected unauthorised activity | Audit log records all admin actions; page visit tracking for usage analytics |
| **A10:2025 — Mishandling of Exceptional Conditions** | Unhandled error leaking stack trace | Custom 404/500 error pages; field-level validation errors; graceful database constraint handling |
| **Session hijacking** | Stolen session cookie reuse | Redis-backed sessions; client fingerprinting (IP + User-Agent); HttpOnly + Secure + SameSite=Strict cookies; single session per user |
| **Session fixation** | Attacker sets session ID | Server-generated UUIDs only; previous sessions invalidated on login |

### Additional Security Controls

- Passwords are never stored in plaintext — bcrypt with unique salts per password
- Session cookies are HttpOnly (no JavaScript access), Secure (HTTPS only in production), and SameSite=Strict
- CSRF tokens expire after 1 hour
- Failed login attempts are tracked per-username in Redis with automatic expiry
- Stale session cookies are automatically cleared by middleware
- Soft-delete pattern prevents accidental permanent data loss

## Security Demonstration Evidence

*To be added — screenshots/videos demonstrating defence against:*

- SQL Injection attempts
- XSS attempts
- Broken Access Control (direct URL access)
- CSRF token validation
- Brute-force login lockout

## User Roles

| Capability | Standard User | Admin |
|---|---|---|
| View dashboard | Yes | Yes |
| View vehicles | Assigned vehicle only | All vehicles |
| Edit vehicles | No | Yes |
| Delete vehicles | No | Yes |
| Record mileage | Own assigned vehicle | Any vehicle (with override) |
| Log maintenance | Yes | Yes |
| Request retirement | Yes | Yes |
| Approve/reject requests | No | Yes |
| Request record deletion | Yes | Yes |
| Manage users | No | Yes |
| Manage locations | No | Yes |
| Manage maintenance categories | No | Yes |
| View audit log | No | Yes |
| View page visit analytics | No | Yes |

## Validation and Error Handling

### Input Validation (Pydantic Schemas)
- Required fields cannot be empty
- Email addresses validated with `EmailStr`
- Usernames must be 3–100 characters
- Passwords must be at least 8 characters with confirmation matching
- Registration numbers and fleet references must be unique
- Mileage readings must be non-negative integers
- Maintenance costs must be non-negative if provided
- Vehicle year must be ≥ 1900
- Employee numbers limited to 50 characters
- Role must be `admin` or `standard`

### Business Rule Validation (Service Layer)
- Retired vehicles cannot receive mileage or maintenance records
- Standard users can only record mileage ≥ current vehicle mileage
- Admin mileage overrides require a reason
- Only one pending retirement request per vehicle
- "Other" maintenance category requires notes
- Duplicate usernames and emails are rejected

### Error Handling
- Field-level error messages displayed next to invalid inputs
- General error messages shown at top of forms
- Flash messages for operation success/failure
- Custom 404 and 500 error pages
- Graceful handling of database constraint violations

## Usability Features

- Confirmation dialogs before deleting records
- Success/failure flash messages with auto-dismiss (5 seconds, pause on hover)
- Consistent navigation with role-based menu items
- Client-side table filtering with real-time search, select dropdowns, numeric ranges and date ranges
- Sortable table columns
- Mobile-responsive collapsible filter accordion
- Dark mode toggle with browser preference detection
- Clean URL bar — navigation params stripped after use
- Accessible form labels and focus indicators
- Date inputs with appropriate sizing
- Breadcrumb-style back navigation
- Usage analytics notice in footer for transparency

## SDLC Approach

| Stage | What was Done | Evidence |
|---|---|---|
| **Planning** | Requirements gathering, user stories, business rules | `_my_context/business-rules.txt` |
| **Design** | Database schema, architecture diagrams, use case diagrams | `diagrams/` folder (PlantUML), `_my_context/postgres.sql` |
| **Development** | Iterative feature development with Git branching | Git commit history, feature branches |
| **Testing** | Unit tests, service tests, route tests, security tests | `tests/` folder (17 test files, 112+ tests) |

## DevOps Approach

- **Git source control** — all development tracked in Git with meaningful commit messages
- **Branching strategy** — feature branches merged into `develop` (e.g. `feature/page-visit-tracking`, `feature/admin-registration`)
- **Containerisation** — Docker and Docker Compose for reproducible environments
- **Environment configuration** — settings driven by environment variables via `.env` file
- **Automated tests** — pytest suite runnable locally and in CI
- **Database seeding** — `seed.py` script for consistent test data
- **Session management** — Redis for scalable session storage (supports multiple app instances)

## CI/CD Pipeline

*To be configured — planned workflow:*

```
On each push to main:
1. Install dependencies
2. Run linting (ruff check .)
3. Run format check (ruff format --check .)
4. Run unit tests (pytest --cov=app)
5. Run security scan (bandit -r app/)
6. Run dependency audit (pip-audit)
7. Deploy to live environment
```

*GitHub Actions workflow file to be added at `.github/workflows/`.*

## Code Quality

- **Modular architecture** — separated into routes, services, models, schemas, security and utilities
- **Separation of concerns** — routes handle HTTP, services handle business logic, schemas handle validation
- **Consistent naming** — snake_case throughout, descriptive function and variable names
- **Custom exceptions** — `NotFoundError`, `ConflictError`, `AuthorisationError`, `AuthenticationError`, `LockedOutError`
- **Reusable template macros** — `form_field`, `csrf_field`, `submit_button` helpers
- **Client-side JS modules** — separate files for table sorting, filtering, form guards and app behaviour
- **No duplicated business logic** — validation rules defined once in schemas, enforced in services
- **Ruff linting and formatting** — enforced via `pyproject.toml` with rules for pycodestyle, pyflakes, isort, flake8-bugbear, flake8-bandit and pyupgrade
- **Bandit static security analysis** — scans application code for common security issues (CWE-mapped); zero findings on 4,236 lines
- **pip-audit dependency scanning** — checks installed packages against known vulnerability databases (PyPI, OSV)

## Deployment

*To be completed after production deployment.*

| Item | Details |
|---|---|
| **Hosting provider** | *TBC* |
| **Deployment method** | *TBC* |
| **Database** | PostgreSQL (managed) |
| **Session store** | Redis (managed) |
| **Environment variables** | Configured via hosting provider settings |

## Known Limitations

- No password reset / forgotten password functionality
- No email notifications for request approvals/rejections
- Page visit analytics do not track admin users (by design)
- No automated database migration tool (uses `create_all` — suitable for development, Alembic recommended for production)
- Test suite requires a running Redis instance for session tests
- No rate limiting on registration endpoint

## Future Improvements

- Add multi-factor authentication
- Add password reset via email
- Add rate limiting to login and registration routes
- Add Alembic for versioned database migrations
- Add dependency vulnerability scanning (`pip-audit`, `safety`)
- Add static analysis (`bandit`)
- Add GitHub Actions CI/CD pipeline
- Add staging and production environments
- Add automated database backup scheduling
- Add end-to-end tests with Playwright
- Add email notifications for request status changes
- Add vehicle document/image uploads
- Add scheduled maintenance reminders
- Add data export (CSV/PDF)

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Pydantic v2 Documentation](https://docs.pydantic.dev/latest/)
- [Bootstrap 5 Documentation](https://getbootstrap.com/docs/5.3/)
- [OWASP Top 10 (2025)](https://owasp.org/Top10/)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Redis Documentation](https://redis.io/docs/)
- [Chart.js Documentation](https://www.chartjs.org/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [pytest Documentation](https://docs.pytest.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [pip-audit Documentation](https://github.com/pypa/pip-audit)

## Licence

This project was developed for academic assessment and is not licensed for production use.