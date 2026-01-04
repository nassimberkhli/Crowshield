import pytest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crowdshield.core.engine import CrowdShieldEngine
from crowdshield.web.app import app as flask_app

@pytest.fixture
def engine():
    return CrowdShieldEngine()

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client
