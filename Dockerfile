FROM python:3.8
ADD . /app

WORKDIR /app

# Install dependencies
RUN apt-get update 
RUN apt-get install npm -y
RUN ./install.sh

# EXPOSE 9870
# CMD ["python", "./start_server.py"]
