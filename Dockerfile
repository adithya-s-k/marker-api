FROM nvcr.io/nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

# Update package lists and install necessary packages
RUN apt-get update \
    && apt-get install -y git python3 python3-pip libgl1 libglib2.0-0 curl \
    && ln -s /usr/bin/python3 /usr/bin/python \
    && curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | bash \
    && apt-get install -y git-lfs \
    && git lfs install \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch and related packages
RUN pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Assuming you have a setup.py or requirements.txt in your project directory
COPY . /app
WORKDIR /app

# Install your Python package (assuming it has a setup.py)
RUN pip3 install --no-cache-dir -e .

# Expose the desired port
EXPOSE 8000

# Run the server
CMD ["python", "server.py", "--host", "0.0.0.0" ,"--port", "8000"]
