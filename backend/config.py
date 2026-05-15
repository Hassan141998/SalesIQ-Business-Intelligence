"""
config.py
==========
Environment-based configuration for SalesIQ backend.
Load via: app.config.from_object(config.DevelopmentConfig)
"""

import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class BaseConfig:
    SECRET_KEY           = os.getenv("SECRET_KEY", "salesiq-dev-secret-change-in-prod")
    UPLOAD_FOLDER        = os.path.join(BASE_DIR, "uploads")
    EXPORT_FOLDER        = os.path.join(BASE_DIR, "exports")
    MAX_CONTENT_LENGTH   = 50 * 1024 * 1024        # 50 MB
    ALLOWED_EXTENSIONS   = {"csv", "xlsx", "xls", "json", "tsv"}
    JSON_SORT_KEYS       = False


class DevelopmentConfig(BaseConfig):
    DEBUG   = True
    TESTING = False


class ProductionConfig(BaseConfig):
    DEBUG   = False
    TESTING = False
    # In production set SECRET_KEY via environment variable


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG   = True


config = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "testing":     TestingConfig,
    "default":     DevelopmentConfig,
}
