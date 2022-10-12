FROM python:3.10-slim

WORKDIR /dev
COPY . /dev/
COPY requirements.txt /dev/requirements.txt

EXPOSE 5501

RUN pip freeze > requirements.txt
RUN pip install -r requirements.txt
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "5501"] 