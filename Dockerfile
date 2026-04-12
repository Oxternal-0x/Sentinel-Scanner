# Use a lightweight Python base
FROM python:3.10-slim

# Install system dependencies for Solidity compiler (solc)
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install the specific Solidity compiler version
RUN pip install --no-cache-dir py-solc-x && python3 -c "import solcx; solcx.install_solc('0.8.20')"

# Copy the rest of the code
COPY . .

# Default command to run the scanner
CMD ["python", "main.py"]
