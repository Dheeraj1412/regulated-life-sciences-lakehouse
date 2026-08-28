FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "python src/generate_synthetic_data.py && python src/bronze_ingestion.py && python src/silver_validation.py && python src/gold_modeling.py && python src/audit_summary.py && python src/build_dashboard.py && python -m pytest tests/ -v"]
