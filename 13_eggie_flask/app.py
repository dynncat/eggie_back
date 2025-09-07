from flask import Flask
from flask_cors import CORS
from routes.user_route import user_bp
from routes.sleep_img_detecting_routes import sleep_img_detecting_bp
from routes.device_environment_logs_routes import device_env_bp
from routes.sleep_prediction_routes import sleep_prediction_bp
from routes.report_routes import report_bp
from routes.sleep_schedule import sleep_schedule_bp
from routes.sleep_log_bp import sleep_log_bp

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Register blueprints
app.register_blueprint(user_bp)
app.register_blueprint(sleep_img_detecting_bp)
app.register_blueprint(device_env_bp)
app.register_blueprint(sleep_prediction_bp)
app.register_blueprint(report_bp)
app.register_blueprint(sleep_schedule_bp)
app.register_blueprint(sleep_log_bp)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)
