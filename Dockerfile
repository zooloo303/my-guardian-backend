# Use an official Python runtime as a parent image
FROM python:3.12-slim

WORKDIR /usr/src/my_guardian_backend

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y netcat-traditional

RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY entrypoint.sh /usr/src/my_guardian_backend/entrypoint.sh
RUN sed -i 's/\r$//g' /usr/src/my_guardian_backend/entrypoint.sh
RUN chmod +x /usr/src/my_guardian_backend/entrypoint.sh

COPY . .

ENTRYPOINT [ "/usr/src/my_guardian_backend/entrypoint.sh" ]