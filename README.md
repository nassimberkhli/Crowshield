# CrowdShield

CrowdShield is a community-driven crowd safety prediction market. It allows users to predict crowd levels at events, with a portion of the fees automatically funding safety and prevention measures.

## Features

- **Prediction Markets**: Users can bet on whether crowd levels will be OVER or UNDER a specific threshold.
- **Prevention Fund**: A percentage of every pot is automatically sent to a transparent fund for safety measures.
- **Pari-mutuel Betting**: Odds are determined by the pool distribution.
- **Simple Interface**: Easy-to-use web interface for creating markets and placing bets.

## Installation

1.  Clone the repository.
2.  Create a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    pip install flask
    ```

## Usage

1.  Start the application:
    ```bash
    export PYTHONPATH=$PYTHONPATH:.
    python crowdshield/web/app.py
    ```
    OR
    ```bash
    python -m crowdshield.web.app
    ```
2.  Open your browser at `http://127.0.0.1:5000`.

## Testing

Run the test suite with pytest:

```bash
pip install pytest
pytest tests/
```

## Structure

- `crowdshield/core`: Pure Python business logic (Models, Engine).
- `crowdshield/web`: Flask web application (Routes, Templates, Static).
- `tests`: Unit and integration tests.
