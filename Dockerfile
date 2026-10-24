FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HOME=/home/user
RUN useradd -m -u 1000 user
WORKDIR /home/user/app
COPY --chown=user requirements.txt .
RUN pip install -r requirements.txt
COPY --chown=user . .
USER user
EXPOSE 8501
CMD ["streamlit","run","app.py","--server.port=8501","--server.address=0.0.0.0","--server.headless=true","--browser.gatherUsageStats=false","--server.enableXsrfProtection=false","--server.enableCORS=false"]
