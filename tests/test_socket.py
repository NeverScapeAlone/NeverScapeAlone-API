import os
import sys
import pytest
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.app import app
from fastapi.testclient import TestClient


def test_app():
    client = TestClient(app=app)
    response = client.get("/")
    assert response.status_code == 200
