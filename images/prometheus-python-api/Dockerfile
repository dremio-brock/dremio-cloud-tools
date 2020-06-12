FROM python:3.7.7-slim

RUN mkdir -p /reqs && mkdir -p /reqs && python -m pip install --upgrade pip
COPY requirements.txt /reqs/requirements.txt
RUN pip install --no-cache-dir -r /reqs/requirements.txt
COPY ./app /app
WORKDIR /app

ENTRYPOINT ["python", "main.py"]
