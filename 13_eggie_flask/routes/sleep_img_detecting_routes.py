from flask import Blueprint, request, jsonify
import csv
import io
from flask import Response
from firebase_utils import init_firestore
from datetime import datetime
from zoneinfo import ZoneInfo

sleep_img_detecting_bp = Blueprint('sleep_img_dectecting', __name__)
db = init_firestore()


# --------------- POST ----------------------

 # 단일 로그 추가
#  curl -X POST http://localhost:5050/sleep-img-detecting/1 \
#    -H "Content-Type: application/json" \
#    -d '{
#          "is_sleeping": true,
#          "created_at": "2025-05-28T15:10:00"
#        }'
 #
 # 여러 로그 추가
 # curl -X POST http://localhost:5050/sleep-img-detecting/1 \
 #   -H "Content-Type: application/json" \
 #   -d '[
 #         {
 #           "is_sleeping": true,
 #           "created_at": "2025-05-28T08:00:00"
 #         },
 #         {
 #           "is_sleeping": false,
 #           "created_at": "2025-05-28T09:00:00"
 #         }
 #       ]'
@sleep_img_detecting_bp.route('/sleep-img-detecting/<int:baby_id>', methods=['POST'])
def add_sleep_log(baby_id):
    data = request.get_json()

    if isinstance(data, dict):
        data = [data]  # Wrap single dict in a list

    if not isinstance(data, list):
        return jsonify({"error": "Invalid data format: must be an object or list of objects"}), 400

    logs_to_add = []
    for entry in data:
        if 'is_sleeping' not in entry or 'created_at' not in entry:
            return jsonify({"error": "Missing required fields in one of the entries"}), 400
        try:
            timestamp = datetime.fromisoformat(entry["created_at"])
        except Exception:
            return jsonify({"error": "Invalid 'created_at' format. Use ISO 8601 format"}), 400
        
        logs_to_add.append({
            "baby_id": baby_id,
            "is_sleeping": entry["is_sleeping"],
            "created_at": timestamp
        })

    for log in logs_to_add:
        db.collection("sleep_img_detecting").add(log)

    return jsonify({"message": f"{len(logs_to_add)} log(s) added successfully"}), 201



# --------------- GET ----------------------

 # curl http://localhost:5050/sleep-img-detecting
@sleep_img_detecting_bp.route('/sleep-img-detecting', methods=['GET'])
def get_all_sleep_logs():
    docs = db.collection('sleep_img_detecting').order_by('created_at').stream()
    logs = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        d["created_at"] = d["created_at"].isoformat()
        logs.append(d)
    # CSV 응답 여부 체크
    if request.args.get("format") == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=logs[0].keys())
        writer.writeheader()
        writer.writerows(logs)
        csv_data = output.getvalue()
        output.close()
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={"Content-Disposition": f"attachment;filename=sleep_img_detecting_all.csv"}
        )
    return jsonify(logs)

 # curl http://localhost:5050/sleep-img-detecting/1
@sleep_img_detecting_bp.route('/sleep-img-detecting/<int:baby_id>', methods=['GET'])
def get_sleep_logs_by_baby(baby_id):
    docs = db.collection('sleep_img_detecting') \
             .where('baby_id', '==', baby_id) \
             .order_by('created_at') \
             .stream()
    logs = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        d["created_at"] = d["created_at"].isoformat()
        logs.append(d)
    # CSV 응답 여부 체크
    if request.args.get("format") == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=logs[0].keys())
        writer.writeheader()
        writer.writerows(logs)
        csv_data = output.getvalue()
        output.close()
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={"Content-Disposition": f"attachment;filename=sleep_img_detecting_baby_{baby_id}.csv"}
        )
    return jsonify(logs)

 # curl "http://localhost:5050/sleep-img-detecting/1/range?start=2025-05-28T00:00:00&end=2025-05-29T00:00:00"
@sleep_img_detecting_bp.route('/sleep-img-detecting/<int:baby_id>/range', methods=['GET'])
def get_sleep_logs_by_baby_by_date(baby_id):
    start_str = request.args.get('start')
    end_str = request.args.get('end')

    query = db.collection('sleep_img_detecting').where('baby_id', '==', baby_id)

    if start_str and end_str:
        try:
            start_dt = datetime.fromisoformat(start_str)
            end_dt = datetime.fromisoformat(end_str)
            query = query.where('created_at', '>=', start_dt).where('created_at', '<=', end_dt)
        except Exception as e:
            return jsonify({'error': f'Invalid date format: {e}'}), 400

    docs = query.order_by('created_at').stream()
    logs = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        d["created_at"] = d["created_at"].isoformat()
        logs.append(d)
    # CSV 응답 여부 체크
    if request.args.get("format") == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=logs[0].keys())
        writer.writeheader()
        writer.writerows(logs)
        csv_data = output.getvalue()
        output.close()
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={"Content-Disposition": f"attachment;filename=sleep_img_detecting_range_{baby_id}_{start_str}_to_{end_str}.csv"}
        )
    return jsonify(logs)