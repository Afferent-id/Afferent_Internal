"""Transparent baseline heatmap; not a fabricated LLM/model prediction."""
from collections import Counter


def _risk_level(points, clicks):
    if points < 60 or clicks >= 4:
        return 'DANGER'
    if points >= 130 and clicks < 2:
        return 'SAFE'
    return 'VULNERABLE'


def _classify_user(user):
    points = int(user.get('points') or 0)
    clicks = int(user.get('click_count') or 0)
    risk = _risk_level(points, clicks)
    return {
        'email': user['email'],
        'divisi': user.get('divisi') or 'General',
        'risk_level': risk,
        'risk_score': max(0, min(100, round(100 - points / 2))),
        'primary_risk': 'Phishing awareness' if risk != 'SAFE' else 'Maintain awareness',
        'one_line_assessment': f'{points}/200 points; {clicks} simulation clicks; {user.get("viewed_training_count", 0)} training completed.',
        'education_tip': 'Periksa pengirim dan domain; jangan bagikan OTP; laporkan tautan meragukan.',
    }


def heatmap(users):
    classifications = [_classify_user(user) for user in users]
    counts = Counter(item['risk_level'] for item in classifications)
    division = Counter(item['divisi'] for item in classifications if item['risk_level'] == 'DANGER')
    return {
        'classifications': classifications,
        '_source': 'behavior_rules',
        '_warning': 'Heatmap baseline dari telemetry, bukan hasil LLM.',
        'org_risk_summary': {
            'safe_count': counts['SAFE'],
            'vulnerable_count': counts['VULNERABLE'],
            'danger_count': counts['DANGER'],
            'most_at_risk_division': division.most_common(1)[0][0] if division else '-',
            'overall_assessment': f'{len(users)} profil telemetry tersedia.',
        },
    }
