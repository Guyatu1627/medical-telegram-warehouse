import os
import sys
import subprocess
from dagster import op, job, ScheduleDefinition, Definitions

# Get absolute path to the project root
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def run_python_script(script_path: str):
    """Utility to run a python script in a subprocess."""
    # Ensure we use the same python executable (from venv)
    python_exe = sys.executable
    result = subprocess.run([python_exe, script_path], cwd=ROOT_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Script {script_path} failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
    return result.stdout

@op(description="Run the Telegram scraper to extract messages and images")
def scrape_telegram_data() -> None:
    # Runs the scraper. Will use mock data if Telegram credentials aren't set in .env
    run_python_script("src/scraper.py")

@op(description="Load raw JSON data from data lake to Postgres")
def load_raw_to_postgres(scrape_done: None) -> None:
    run_python_script("src/load_to_postgres.py")

@op(description="Run YOLO object detection on images and load results to Postgres")
def run_yolo_enrichment(scrape_done: None) -> None:
    run_python_script("src/yolo_detect.py")
    run_python_script("src/load_yolo_to_postgres.py")

@op(description="Run dbt transformations to build the star schema")
def run_dbt_transformations(load_done: None, yolo_done: None) -> None:
    dbt_dir = os.path.join(ROOT_DIR, "medical_warehouse")
    
    # Run dbt models
    result = subprocess.run(["dbt", "run"], cwd=dbt_dir, capture_output=True, text=True, shell=True if sys.platform == 'win32' else False)
    if result.returncode != 0:
        raise Exception(f"dbt run failed:\n{result.stdout}\n{result.stderr}")
        
    # Run dbt tests
    result = subprocess.run(["dbt", "test"], cwd=dbt_dir, capture_output=True, text=True, shell=True if sys.platform == 'win32' else False)
    if result.returncode != 0:
        raise Exception(f"dbt test failed:\n{result.stdout}\n{result.stderr}")

@job(description="Medical Telegram Data Pipeline")
def medical_etl_pipeline():
    # Define dependencies
    scrape_done = scrape_telegram_data()
    
    load_done = load_raw_to_postgres(scrape_done)
    yolo_done = run_yolo_enrichment(scrape_done)
    
    # Transformations run after raw data and YOLO enrichments are loaded
    run_dbt_transformations(load_done, yolo_done)

# Schedule to run daily at midnight
daily_schedule = ScheduleDefinition(
    job=medical_etl_pipeline,
    cron_schedule="0 0 * * *",
)

defs = Definitions(
    jobs=[medical_etl_pipeline],
    schedules=[daily_schedule],
)