FROM python:3.10-slim

WORKDIR /prod
COPY . /prod/
COPY requirements.txt /prod/requirements.txt

EXPOSE 5500

RUN pip install -r requirements.txt
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "5500"] 