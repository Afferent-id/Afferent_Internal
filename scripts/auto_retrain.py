#!/usr/bin/env python3
"""
CLI Tool to manually trigger or schedule the AFFERENT Continuous Learning Engine.
Usage:
    python scripts/auto_retrain.py --now
    python scripts/auto_retrain.py --daemon --interval 3
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Setup paths
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "backend"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("afferent-retrain-cli")

from services.continuous_learning import get_engine, start_scheduler
from services import stacker_scanner


def main():
    parser = argparse.ArgumentParser(description="AFFERENT Continuous Learning & Model Retraining Engine")
    parser.add_argument("--now", action="store_true", help="Execute one continuous learning & retraining cycle immediately")
    parser.add_argument("--daemon", action="store_true", help="Run as long-running scheduler daemon")
    parser.add_argument("--interval", type=int, default=3, help="Scheduler interval in hours (default: 3)")
    args = parser.parse_args()

    engine = get_engine()

    if args.now or not args.daemon:
        print("\n" + "=" * 70)
        print("  AFFERENT · CONTINUOUS LEARNING & QUALITY GATE RETRAINING")
        print("=" * 70)
        print(f"[*] Starting cycle at {time.strftime('%Y-%m-%d %H:%M:%S')}...")
        res = engine.run_cycle()
        print("-" * 70)
        if res.get("promoted"):
            print(f"[+] SUCCESS: Candidate model PROMOTED & HOT-RELOADED!")
            print(f"    • New Revision     : {res.get('revision')}")
            print(f"    • Calibrated Thresh: {res.get('threshold'):.4f}")
            print(f"    • Training Samples : {res.get('training_samples')}")
            print(f"    • Cycle Duration   : {res.get('duration_seconds'):.2f}s")
            print("\n    • Golden Benign Verification (P_mal must be low):")
            for d, p in list(res.get("golden_eval", {}).items())[:8]:
                print(f"      - {d:<30}: P_mal = {p:.4f} (OK)")
        else:
            print(f"[!] CANDIDATE REJECTED by Golden Quality Gate!")
            print(f"    Reason: {res.get('reason')}")
            for v in res.get("violations", []):
                print(f"    - {v}")
        print("=" * 70 + "\n")

    if args.daemon:
        print(f"[*] Starting background daemon: Retraining every {args.interval} hours...")
        start_scheduler(interval_hours=args.interval)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Continuous learning daemon stopped.")


if __name__ == "__main__":
    main()
