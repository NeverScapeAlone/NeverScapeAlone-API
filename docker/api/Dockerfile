FROM python:3.10-slim

WORKDIR /prod
COPY . /prod/

EXPOSE 5500

RUN pip install -r requirements.txt
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "5500"] 