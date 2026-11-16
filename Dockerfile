FROM registry.redhat.io/ubi9/python-311-minimal:latest

# Create non-root application user
RUN useradd -m -u 1001 appuser

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER 1001

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://127.0.0.1:8501/_stcore/health || exit 1

# Run Streamlit server bound to localhost / container interface
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
