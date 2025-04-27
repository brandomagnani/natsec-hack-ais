# FastAPI Ship Data Backend

Simple FastAPI backend to serve ship data.

## Setup

1.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Running the Server

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## API Endpoints

-   `GET /`: Welcome message.
-   `GET /api/v1/ships/`: Returns mock ship data grouped by `ship_id`.
-   `GET /docs`: Interactive API documentation (Swagger UI).
-   `GET /redoc`: Alternative API documentation (ReDoc).
