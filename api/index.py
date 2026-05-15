"""
api/index.py
=============
Vercel serverless entry point.
Vercel looks for api/index.py at the repo root automatically.

This file imports and exposes the Flask app so Vercel can serve it.
"""

import sys
import os

# Add backend/ to path so all imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Import the Flask app from backend/app.py
from app import app

# Vercel calls this as a WSGI app
# No changes needed — Flask IS a WSGI app
