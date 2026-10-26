import logging
import uuid
from flask import Blueprint, jsonify, request
from security import current_identity, require_roles
from services import exam_service

exam_bp = Blueprint('exam',__name__)

@exam_bp.route('/api/exam',methods=['GET','POST'])
@require_roles('employee')
def assessment():
    identity = current_identity()
    if request.method=='GET':
        return jsonify({'exam':exam_service.current(identity)})
    body = request.get_json(silent=True)
    if not isinstance(body,dict):
        return jsonify({'error':'Send a JSON object.'}),400
    if body.get('action')=='check_campaign':
        try:
            exam_service.sync_campaigns(identity)
        except Exception as exc:
            logging.warning('Assessment campaign sync deferred: %s',type(exc).__name__)
            return jsonify({'error':'Campaign verification is temporarily unavailable. Please retry.'}),503
        return jsonify({'exam':exam_service.current(identity)})
    try:
        return jsonify(exam_service.act(identity,body.get('examId'),body.get('action'),body))
    except ValueError as exc:
        return jsonify({'error':str(exc)}),400

@exam_bp.route('/api/admin/training-inbox',methods=['GET','POST'])
@require_roles('phishing_admin')
def training_inbox():
    if request.method=='GET':
        return jsonify(exam_service.inbox())
    body = request.get_json(silent=True)
    if not isinstance(body,dict):
        return jsonify({'error':'Send a JSON object.'}),400
    try:
        return jsonify(exam_service.queue_training(current_identity(),body.get('examId'),body.get('reason'),str(uuid.uuid4()))),202
    except ValueError as exc:
        return jsonify({'error':str(exc)}),400
