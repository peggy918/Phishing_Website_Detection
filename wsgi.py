"""網站進入點：flask --app wsgi run。啟動時在背景先載入模型，避免第一位使用者等待。"""
from app import create_app
from app.services.predictor import preload_in_background

app = create_app()
preload_in_background(app.config["SESSION_FACTORY"])
