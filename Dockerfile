FROM pytorch/pytorch:2.3.1-cuda11.8-cudnn8-runtime

# Update package lists and install necessary packages
RUN apt-get update \
    && apt-get install -y ffmpeg libsm6 libxext6

# Assuming you have a setup.py or requirements.txt in your project directory
COPY . /app
WORKDIR /app

# Install your Python package (assuming it has a setup.py)
RUN pip3 install --no-cache-dir -e .

# Download models used by convert
RUN python -c 'from marker.models import load_all_models; load_all_models()'

# Expose the desired port
EXPOSE 8000

# Run the server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0" ,"--port", "8000", "--workers", "4"]
