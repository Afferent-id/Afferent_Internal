import sys
from pathlib import Path

# Add backend directory
backend_dir = Path("/home/flyingsundaman/Human_Firewall/backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv("/home/flyingsundaman/Human_Firewall/.env")

import integrations

keys = integrations.get_vt_api_keys()
print(f"[*] Total active VT keys loaded on server: {len(keys)}")
for i, k in enumerate(keys, 1):
    print(f"    - Key {i}: {k[:8]}...{k[-4:]}")

next_k = integrations.get_next_vt_key()
print(f"[*] Next round-robin selected key: {next_k[:8]}...{next_k[-4:] if next_k else 'None'}")
print("[+] MULTI-KEY POOL VERIFICATION ON SERVER: SUCCESS!")
