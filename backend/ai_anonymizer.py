"""
ai_anonymizer.py — Privacy & Anonymization Layer for AI Behavioral Module.

Tujuan:
- Mencegah pengiriman PII (Personally Identifiable Information) seperti email asli
  atau nama karyawan ke LLM eksternal (OpenRouter, Gemini, Groq).
- Mengganti email asli dengan Token Pseudonim Deterministik (misal: EMP-8F9A3C).
- Mengembalikan email asli ke respons JSON backend sebelum dikirim ke frontend client.
"""

import hashlib
import copy


def anonymize_email(email: str) -> str:
    """
    Hasilkan token pseudonim deterministik dari email.
    Contoh: 'dewi.lestari@netops-dummy.local' -> 'EMP-4E9D2A'
    """
    if not email:
        return "EMP-UNKNOWN"
    clean_email = email.strip().lower()
    digest = hashlib.sha256(clean_email.encode('utf-8')).hexdigest().upper()
    return f"EMP-{digest[:6]}"


def anonymize_user_summary_list(users: list[dict]) -> tuple[list[dict], dict[str, str]]:
    """
    Anonymize list user summary untuk batch classification.
    Return: (anonymized_users_list, mapping_dict)
    mapping_dict maps: { 'EMP-4E9D2A': 'dewi.lestari@netops-dummy.local' }
    """
    anonymized = []
    mapping = {}

    for user in users:
        anonymous_user, raw_email = anonymize_user_context(user)
        mapping[anonymous_user["email"]] = raw_email
        anonymized.append(anonymous_user)

    return anonymized, mapping


def anonymize_user_context(context: dict) -> tuple[dict, str]:
    """
    Anonymize konteks individual satu user.
    Return: (anonymized_context_dict, raw_email_str)
    """
    ctx_copy = copy.deepcopy(context)
    raw_email = ctx_copy.get("email", "")
    pseudo_id = anonymize_email(raw_email)

    ctx_copy["email"] = pseudo_id
    return ctx_copy, raw_email


def anonymize_org_context(org_context: dict) -> tuple[dict, dict[str, str]]:
    """
    Anonymize konteks organisasi (khususnya daftar chronic_risk_users).
    Return: (anonymized_org_context_dict, mapping_dict)
    """
    ctx_copy = copy.deepcopy(org_context)
    mapping = {}

    if "chronic_risk_users" in ctx_copy and isinstance(ctx_copy["chronic_risk_users"], list):
        ctx_copy["chronic_risk_users"], mapping = anonymize_user_summary_list(
            ctx_copy["chronic_risk_users"]
        )

    return ctx_copy, mapping


def deanonymize_response(result: dict, mapping: str | dict[str, str]) -> dict:
    """
    Restorasi email asli ke hasil JSON respons LLM sebelum dikembalikan ke client.
    """
    if not isinstance(result, dict):
        return result

    # Kasus 1: mapping berupa single string raw email (untuk user individual analysis)
    if isinstance(mapping, str):
        result["email"] = mapping
        return result

    # Kasus 2: mapping berupa dict { 'EMP-4E9D2A': 'real_email' }
    if isinstance(mapping, dict):
        for field in ("classifications", "chronic_risk_users"):
            if field not in result or not isinstance(result[field], list):
                continue
            for item in result[field]:
                pseudo = item.get("email", "")
                if pseudo in mapping:
                    item["email"] = mapping[pseudo]

    return result
