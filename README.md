# MedSync - Medication Management App

MedSync is a comprehensive medication management platform designed to help families and individuals track their medication inventory, schedule doses, and monitor adherence. 

## Features

- **Family Medication Management**: Create family groups with unique join codes to manage medications together.
- **Role-Based Access**: Support for 'Patient' and 'Caregiver' roles.
- **Stock Inventory System**: Track global medicine stock, receive expiry warnings, and automatically deduct quantities when doses are taken.
- **Smart AI Medicine Scanner**: Upload an image of a medicine label and let the AI (powered by OpenAI GPT-4o-mini) automatically extract details like GTIN, Name, Batch Number, Dosage, and Expiry Date.
- **Dosing Schedules & Adherence Logs**: Schedule when medications need to be taken and log adherence to ensure nothing is missed.
- **OTP Verification**: Secure email-based OTP verification for user signups.

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, SQLite (default)
- **Frontend**: HTML, CSS, JavaScript (served directly by FastAPI)
- **AI Integration**: OpenAI API

## Getting Started

### Prerequisites

- Python 3.10+
- An OpenAI API Key (for the AI Medicine Scanner)
- A Gmail account with an App Password (for OTP verification emails)

### Installation

1. **Clone the repository** (if you haven't already):
   ```bash
   git clone <your-repo-url>
   cd medsync2
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file in the root directory (you can use `.env.example` as a template if available) and add the following:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   GMAIL_ADDRESS=your_gmail_address_here
   GMAIL_APP_PASSWORD=your_gmail_app_password_here
   ```

### Running the App

To start the backend server and serve the frontend:

```bash
uvicorn app.main:app --reload
```

The application will be available at:
- **Frontend App**: [http://127.0.0.1:8000/frontend/app.html](http://127.0.0.1:8000/frontend/app.html)
- **Interactive API Docs (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Project Structure

- `app/` - Backend source code (FastAPI routers, database models, schemas).
  - `main.py` - Application entry point.
  - `models.py` - SQLAlchemy database models.
  - `schemas.py` - Pydantic models for API request/response validation.
  - `database.py` - Database configuration.
- `frontend/` - Static frontend files (HTML, CSS, JS).
  - `app.html` - The main interactive frontend interface.
- `scratch/` - Temporary utility and helper scripts.

## License

This project is licensed under the MIT License.
