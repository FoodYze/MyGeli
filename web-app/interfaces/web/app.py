from flask import Flask
import os
from interfaces.web.controllers import init_app_routes
from config.settings import FLASK_SECRET_KEY

def create_app():
    app = Flask(__name__, static_folder='../../static', template_folder='../../templates')
    app.secret_key = FLASK_SECRET_KEY
    init_app_routes(app)
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)