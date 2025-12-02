# Stage 1: Build the React app
FROM node:18-alpine as build

WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the app
RUN npm run build

# Stage 2: Python Runtime
FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python backend code
COPY main.py .
COPY nse_client.py .

# Copy built frontend assets from Stage 1
COPY --from=build /app/dist ./dist

# Create a non-root user for security (good practice, often required in spaces)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
	PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# We need to copy files to the user's home directory so they have permissions if needed
# But usually we can run from /app if we adjust permissions.
# Simpler approach for spaces:
USER root
RUN chown -R user:user /app
USER user
WORKDIR /app

# Expose port 7860
EXPOSE 7860

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
