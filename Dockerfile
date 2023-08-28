FROM python:3.10-slim
WORKDIR /app
COPY . /app
RUN pip3 install --no-cache-dir -r requirements.txt
RUN decodex download ethereum
CMD ["chainlit", "run", "main.py","--headless"]