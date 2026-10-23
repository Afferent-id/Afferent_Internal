"""
Calibrated Stacker Meta-Learner (XGBoost) Scanner Service for AFFERENT.
Evaluates hostnames at line-rate (< 1ms on CPU) combining TF-IDF and structural/reputation features.
"""

import json
import logging
import math
import os
import re
import sys
import threading
from pathlib import Path
from typing import Dict, Any, Optional

import numpy as np

# Ensure backend directory is in sys.path
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_attempted = False
_stacker_model = None
_base_tfidf = None
_extractor = None
_manifest = {}

POLICY_REVISION = "stacker-xgboost-v1"


def generated_hostname(domain: str) -> bool:
    """Detect hexadecimal / UUID generated hostnames that fall outside calibrated domain distribution."""
    return any(re.search(r"[0-9a-f]{24,}", label) for label in domain.split(".")[:-2])


def warmup():
    global _attempted, _stacker_model, _base_tfidf, _extractor, _manifest
    with _lock:
        if _attempted:
            return
        _attempted = True
        
        base_dir = Path(__file__).resolve().parent.parent
        stacker_dir = Path(os.environ.get("ML_STACKER_MODEL_DIR", str(base_dir / "models" / "stacker_v1")))
        base_model_dir = Path(os.environ.get("ML_DOMAIN_MODEL_DIR", str(base_dir / "models" / "domain_v3")))
        tranco_path = Path(os.environ.get("TRANCO_CSV_PATH", str(base_dir.parent / "dataset" / "raw" / "tranco" / "tranco_Y8YYG.csv")))
        
        try:
            import joblib
            try:
                from services.domain_features import DomainFeatureExtractor
            except ModuleNotFoundError:
                from backend.services.domain_features import DomainFeatureExtractor
            
            # Load manifest
            manifest_file = stacker_dir / "manifest.json"
            if manifest_file.exists():
                _manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            
            # Load stacker artifact
            stacker_file = stacker_dir / "stacker.joblib"
            if stacker_file.exists():
                artifact = joblib.load(stacker_file)
                _stacker_model = artifact["stacker"]
            
            # Load base TF-IDF model
            base_file = base_model_dir / "classifier.joblib"
            if base_file.exists():
                _base_tfidf = joblib.load(base_file)
                
            # Init feature extractor
            _extractor = DomainFeatureExtractor(str(tranco_path) if tranco_path.exists() else None)
            
            logger.info("Stacker XGBoost Scanner initialized successfully.")
        except Exception as exc:
            logger.error("Stacker ML unavailable: %s", type(exc).__name__, exc_info=True)


def model_version() -> Optional[str]:
    warmup()
    return f"stacker-xgb-v1:{POLICY_REVISION}" if _stacker_model is not None else None


def status() -> Dict[str, Any]:
    warmup()
    return {
        "available": _stacker_model is not None and _base_tfidf is not None,
        "inputScope": "domain",
        "modelVersion": model_version(),
        "policyRevision": POLICY_REVISION,
        "evaluationScope": "Stacker XGBoost ensemble with lexical and Tranco features",
        "enforcementEligible": bool(_manifest.get("enforcement_eligible")),
        "blockThreshold": _manifest.get("block_threshold"),
        "evaluation": _manifest.get("test_unique_domain_labels", {})
    }


def scan(domain: str) -> Dict[str, Any]:
    warmup()
    if _stacker_model is None or _base_tfidf is None or _extractor is None:
        # Fallback to standard domain_scanner if stacker is missing
        try:
            from services.domain_scanner import scan as fallback_scan
        except ModuleNotFoundError:
            from backend.services.domain_scanner import scan as fallback_scan
        return fallback_scan(domain)
        
    try:
        from services.proxy_service import normalize_domain
    except ModuleNotFoundError:
        from backend.services.proxy_service import normalize_domain
    try:
        domain = normalize_domain(domain)
    except Exception:
        return {"verdict": "unknown", "confidence": None, "status": "invalid_domain",
                "reason": "Hostname format tidak valid", "modelVersion": model_version()}
        
    if generated_hostname(domain):
        return {
            "verdict": "unknown",
            "confidence": None,
            "status": "ready",
            "reason": "Hostname layanan ber-ID/hash (DGA check deferred to SOC).",
            "modelVersion": model_version()
        }
        
    # 1. Base TF-IDF prediction
    pipeline = _base_tfidf["pipeline"]
    calibrator = _base_tfidf["calibrator"]
    margin = pipeline.decision_function([domain]).reshape(-1, 1)
    tfidf_prob = float(calibrator.predict_proba(margin)[0, 1])
    
    # 2. Extract structural & reputation features
    feats = _extractor.extract_features(domain)
    
    # 3. Construct 11-feature vector for XGBoost
    x = np.array([[
        tfidf_prob,
        feats["length"],
        feats["entropy"],
        feats["subdomain_count"],
        feats["hyphen_count"],
        feats["digit_ratio"],
        feats["vowel_ratio"],
        feats["is_ip"],
        feats["is_suspicious_tld"],
        feats["tranco_feature"],
        feats["is_tranco_top"]
    ]], dtype=np.float32)
    
    # 4. Predict probability with Stacker
    prob_malicious = float(_stacker_model.predict_proba(x)[0, 1])
    if not math.isfinite(prob_malicious) or not 0 <= prob_malicious <= 1:
        raise ValueError("Non-finite stacker prediction")
        
    threshold = _manifest.get("block_threshold", 0.99)
    is_eligible = _manifest.get("enforcement_eligible", False)
    
    # Decision policy
    if is_eligible and threshold is not None and prob_malicious >= threshold:
        verdict = "malicious"
        confidence = prob_malicious
        reason = f"Ensemble Stacker (XGBoost): P_mal={prob_malicious:.4f} >= {threshold:.4f} (Wilson 95% CI FPR <= 0.3%)"
    elif prob_malicious <= 0.15:
        verdict = "safe"
        confidence = 1.0 - prob_malicious
        reason = f"Ensemble Stacker (XGBoost): Domain benign (P_mal={prob_malicious:.4f})"
    else:
        verdict = "unknown"
        confidence = None
        reason = f"Ensemble Stacker (XGBoost): Review zone (P_mal={prob_malicious:.4f})"
        
    return {
        "verdict": verdict,
        "confidence": confidence,
        "status": "ready",
        "reason": reason,
        "modelVersion": model_version(),
        "prob_malicious": prob_malicious,
        "tranco_top": bool(feats["is_tranco_top"]),
        "entropy": feats["entropy"]
    }
