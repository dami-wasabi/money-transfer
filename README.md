# Money Transfer Web Application

A beautiful Python Flask web application for sending money internationally with real-time fee and exchange rate calculations.

## Features

- Calculate sending fees (2%) on money transfers
- Convert USD to CFA with current exchange rates (1 USD = 655 CFA)
- Beautiful, modern UI with animations and transitions
- Responsive design that works on all devices
- Easy to deploy with Docker

## Project Structure

```
money-transfer-app/
├── app.py                 # Main Flask application
├── templates/
│   └── index.html         # HTML template with embedded JavaScript
├── static/                # For static assets (optional)
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose configuration
├── requirements.txt       # Python dependencies
└── README.md              # Project documentation
```

## Prerequisites

- Python 3.8+ (if running locally)
- Docker and Docker Compose (for containerized deployment)

## Running Locally

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/money_transfer-app.git
   cd money-transfer-app
   ```

2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python app.py
   ```

5. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

## Docker Deployment

### Using Docker

1. Build the Docker image:
   ```bash
   docker build -t money-transfer-app .
   ```

2. Run the container:
   ```bash
   docker run -p 5000:5000 money-transfer-app
   ```

3. Access the application at:
   ```
   http://localhost:5000
   ```

### Using Docker Compose

1. Start the application:
   ```bash
   docker-compose up -d
   ```

2. Access the application at:
   ```
   http://localhost:5000
   ```

3. Stop the application:
   ```bash
   docker-compose down
   ```

## Configuration

You can modify the following constants in `app.py`:

- `SENDING_FEES`: The percentage fee charged for sending money (default: 0.02 or 2%)
- `EXCHANGE_RATE`: The USD to CFA exchange rate (default: 655)

## Production Deployment

For production deployment, consider:

1. Setting `debug=False` in the `app.run()` function
2. Using a production WSGI server like Gunicorn
3. Setting up HTTPS with a reverse proxy like Nginx
4. Implementing proper error handling and logging

Example production setup using Gunicorn in Docker:

```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

