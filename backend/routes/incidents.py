from flask import Blueprint, request, jsonify
import database
import uuid
from security import current_identity, require_roles

incidents_bp = Blueprint('incidents', __name__)

@incidents_bp.route('/api/incidents', methods=['POST'])
@require_roles('soc', allow_service=True)
def create_incident():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "body JSON wajib diisi"}), 400

    reported_url = data.get('reported_url', '')
    vt_verdict = data.get('vt_verdict', '')
    urlscan_verdict = data.get('urlscan_verdict', '')

    verdict = "clean"
    if vt_verdict == "malicious" or urlscan_verdict == "malicious":
        verdict = "malicious"
    elif vt_verdict == "suspicious" or urlscan_verdict == "suspicious":
        verdict = "suspicious"

    from services.threat_service import reconcile_report_source
    source_verdict = reconcile_report_source(reported_url, verdict)

    if source_verdict == "simulation_correctly_reported":
        source_type = "simulation"
    elif verdict in ("malicious", "suspicious"):
        source_type = "real_world_report"
    else:
        source_type = data.get('source_type') or "real_world_report"

    if source_type not in database.VALID_SOURCE_TYPES:
        return jsonify({
            "error": f"source_type wajib diisi dan harus salah satu dari "
                     f"{database.VALID_SOURCE_TYPES}",
            "received": source_type
        }), 400

    divisi = data.get('divisi') or 'User Report'

    ticket_id = f"INC-{uuid.uuid4().hex[:8].upper()}"

    severity = (data.get('severity') or '').lower()
    if severity not in database.VALID_SEVERITIES:
        severity = 'high' if verdict in ('malicious', 'suspicious') else 'low'

    try:
        database.create_incident(
            ticket_id=ticket_id,
            source_type=source_type,
            divisi=divisi,
            severity=severity,
            reported_url=reported_url,
            vt_verdict=vt_verdict,
            urlscan_verdict=urlscan_verdict,
            screenshot_url=data.get('screenshot_url'),
            checklist=data.get('checklist'),
            file_hash=data.get('file_hash'),
            original_filename=data.get('original_filename')
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "gagal membuat ticket", "detail": str(e)}), 500

    response_body = {"message": "Ticket incident berhasil dibuat",
                      "ticket_id": ticket_id, "source_type": source_type,
                      "severity": severity, "source_verdict": source_verdict}

    # Employee rewards belong to the authenticated /api/reports transaction,
    # never an administrator-supplied reporter identity or Telegram chat ID.

    return jsonify(response_body), 201


@incidents_bp.route('/api/incidents/<ticket_id>', methods=['PATCH'])
@require_roles('soc')
def update_incident(ticket_id):
    """Resolve, reopen, or (un)assign. Every change is recorded with who, when and why.

    Body: {"status": "open"|"closed", "note": "...", "assignee": "me"|""}.
    Resolving requires a note. "me" assigns to the caller; "" removes the assignee.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not ('status' in data or 'assignee' in data):
        return jsonify({"error": "Send a status and/or an assignee."}), 400
    identity = current_identity()
    from services import incident_service
    try:
        updated = incident_service.change(ticket_id, identity, status=data.get('status'),
            note=data.get('note'), assignee=data.get('assignee'), resolution=data.get('resolution'))
    except incident_service.IncidentConflict as e:
        return jsonify({'error': str(e), 'code': 'INCIDENT_CONFLICT'}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({'error': 'The policy could not be applied. The incident stays open; retry with the same decision.'}), 503

    if not updated:
        return jsonify({"error": f"Incident '{ticket_id}' was not found."}), 404

    return jsonify({"message": f"Incident {ticket_id} updated.", "incident": updated}), 200


@incidents_bp.route('/api/incidents/<ticket_id>/events', methods=['GET'])
@require_roles('soc')
def incident_events(ticket_id):
    return jsonify({"events": database.list_incident_events(ticket_id)}), 200


@incidents_bp.route('/api/incidents', methods=['GET'])
@require_roles('soc', 'phishing_admin')
def list_incidents():
    source_type = request.args.get('source_type')
    status = request.args.get('status')

    if source_type and source_type not in database.VALID_SOURCE_TYPES:
        return jsonify({
            "error": f"source_type tidak valid: {source_type}",
            "valid_options": database.VALID_SOURCE_TYPES
        }), 400

    incidents = database.list_incidents(source_type=source_type, status=status)
    return jsonify({"incidents": incidents, "count": len(incidents)}), 200

