# Medical Telegram Warehouse

A robust data pipeline and analytical warehouse for collecting, processing, and analyzing medical telegram messages. Built with **FastAPI**, **dbt (data build tool)**, and **PostgreSQL**.

## Project Architecture & Structure

This repository follows a clean, decoupled architecture:
- **`api/`**: A FastAPI application for exposing endpoints to query message telemetry and warehouse health.
- **`medical_warehouse/`**: A dbt project for structuring, cleansing, and modeling data in the PostgreSQL warehouse.
- **`data/`**: Directory for storing seeds, raw data extracts, or SQLite dumps.
- **`src/`**: Shared Python utilities and processing modules.
- **`notebooks/`**: Jupyter notebooks for exploratory data analysis (EDA).
- **`scripts/`**: One-off utilities and run scripts.
- **`tests/`**: Unit and integration test suites.

```
medical-telegram-warehouse/
├── .vscode/               # Workspace specific settings
├── .github/workflows/     # CI/CD pipelines (unit tests)
├── data/                  # Data placeholder directory
├── medical_warehouse/     # dbt project configurations & models
├── src/                   # Python source directory
├── api/                   # FastAPI backend
├── notebooks/             # Jupyter notebooks for analysis
├── tests/                 # Test suites
└── scripts/               # Maintenance scripts
```

## Getting Started

### Prerequisites

Ensure you have the following installed locally:
- Python 3.10+
- Docker & Docker Compose
- Git

### Local Setup

1. **Clone the Repository**:
   ```bash
   git clone <repository_url>
   cd medical-telegram-warehouse
   ```

2. **Configure Environment Variables**:
   Copy the sample settings if you want to customize them:
   ```bash
   cp .env.example .env  # Or edit the existing .env file
   ```

3. **Start PostgreSQL Container**:
   Spin up the Postgres DB using docker-compose:
   ```bash
   docker-compose up -d db
   ```

4. **Install Dependencies**:
   Initialize a virtual environment and install requirements:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

5. **Run the FastAPI Application**:
   ```bash
   uvicorn api.main:app --reload --port 8000
   ```
   Access the interactive Swagger documentation at [http://localhost:8000/docs](http://localhost:8000/docs).

6. **Initialize and Test dbt**:
   Navigate to the dbt project and verify connection:
   ```bash
   cd medical_warehouse
   dbt debug
   dbt run
   ```

## Development & Testing

### Running Tests
To run unit and integration tests, use `pytest`:
```bash
pytest
```
