FROM python:3.10-slim
WORKDIR /app
COPY . /app
ENV DECODEX_UI_PORT=8000
EXPOSE $DECODEX_UI_PORT
RUN pip3 install --no-cache-dir -r requirements.txt
ENTRYPOINT chainlit run main.py --headless --port $DECODEX_UI_PORT