FROM python:3.10-slim
WORKDIR /app
COPY . /app
EXPOSE $DECODEX_UI_PORT
RUN pip3 install --no-cache-dir -r requirements.txt
ENTRYPOINT chainlit run main.py --headless --port $DECODEX_UI_PORT