FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN python -m pip install --no-cache-dir .
ENTRYPOINT ["radio-pipeline-lab"]
CMD ["plan", "--config", "configs/demo.toml"]
