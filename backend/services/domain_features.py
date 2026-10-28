"""
Domain Feature Extraction Engine for AFFERENT.
Extracts fast structural, lexical, and reputation features for high-throughput
Squid CONNECT / SNI inspection (< 0.2ms per host on CPU).
"""

import math
import re
import os
from collections import Counter
from typing import Dict, Any, Optional

# Regex for IPv4 address host
IPV4_REGEX = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")

# Suspicious TLDs often abused in high-volume ephemeral phishing
SUSPICIOUS_TLDS = {
    "xyz", "top", "tk", "ml", "ga", "cf", "gq", "buzz", "club", "icu",
    "work", "rest", "cam", "fit", "live", "space", "monster", "fun", "site",
    "online", "link", "click", "download", "stream", "bid", "loan", "men", "date"
}

VOWELS = set("aeiou")


class DomainFeatureExtractor:
    def __init__(self, tranco_csv_path: Optional[str] = None):
        self.tranco_lookup: Dict[str, int] = {}
        if tranco_csv_path and os.path.exists(tranco_csv_path):
            self._load_tranco(tranco_csv_path)

    def _load_tranco(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                header = f.readline()
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) >= 2:
                        try:
                            rank = int(parts[0])
                            domain = parts[1].strip().lower()
                            self.tranco_lookup[domain] = rank
                        except ValueError:
                            continue
        except Exception:
            pass

    @staticmethod
    def calculate_entropy(text: str) -> float:
        """Shannon entropy of a string."""
        if not text:
            return 0.0
        length = len(text)
        counts = Counter(text)
        entropy = 0.0
        for count in counts.values():
            p = count / length
            entropy -= p * math.log2(p)
        return float(entropy)

    def get_tranco_rank(self, host: str) -> Optional[int]:
        """Lookup rank for host or registered domain."""
        host = host.lower().strip(".")
        if host in self.tranco_lookup:
            return self.tranco_lookup[host]
        # Check parent domains for subdomains (e.g. apispada.kemdiktisaintek.go.id -> kemdiktisaintek.go.id)
        parts = host.split(".")
        for i in range(1, len(parts)):
            sub = ".".join(parts[i:])
            if sub in self.tranco_lookup:
                return self.tranco_lookup[sub]
        return None

    def extract_features(self, host: str) -> Dict[str, Any]:
        """
        Extract numerical and boolean features from raw hostname.
        Execution budget: < 0.2ms.
        """
        clean_host = host.lower().strip().rstrip(".")
        length = len(clean_host)
        
        # Check IP (public raw IPs are suspicious, but private/LAN IPs are internal)
        is_ip = 0.0
        if IPV4_REGEX.match(clean_host):
            try:
                import ipaddress
                _ip = ipaddress.ip_address(clean_host)
                if not (_ip.is_private or _ip.is_loopback or _ip.is_link_local or (_ip.version == 4 and ipaddress.ip_network("100.64.0.0/10").overlaps(ipaddress.ip_network(f"{_ip}/32")))):
                    is_ip = 1.0
            except ValueError:
                is_ip = 1.0
        
        # Subdomains
        parts = clean_host.split(".")
        subdomain_count = max(0, len(parts) - 2)
        tld = parts[-1] if parts else ""
        is_suspicious_tld = 1.0 if tld in SUSPICIOUS_TLDS else 0.0
        
        # Lexical stats
        digit_count = sum(c.isdigit() for c in clean_host)
        digit_ratio = digit_count / max(1, length)
        
        alpha_count = sum(c.isalpha() for c in clean_host)
        vowel_count = sum(c in VOWELS for c in clean_host)
        vowel_ratio = vowel_count / max(1, alpha_count) if alpha_count > 0 else 0.0
        
        hyphen_count = clean_host.count("-")
        entropy = self.calculate_entropy(clean_host)
        
        # Tranco rank: Rank 1 -> 6.0, Rank 10k -> 2.0, Rank 1M -> ~0.0, unranked -> 0.0
        rank = self.get_tranco_rank(clean_host)
        if rank and rank > 0:
            tranco_feature = max(0.0, 6.0 - math.log10(rank))
            is_tranco_top = 1.0
        else:
            tranco_feature = 0.0
            is_tranco_top = 0.0

        return {
            "host": clean_host,
            "length": float(length),
            "entropy": float(entropy),
            "subdomain_count": float(subdomain_count),
            "hyphen_count": float(hyphen_count),
            "digit_ratio": float(digit_ratio),
            "vowel_ratio": float(vowel_ratio),
            "is_ip": is_ip,
            "is_suspicious_tld": is_suspicious_tld,
            "tranco_feature": float(tranco_feature),
            "is_tranco_top": is_tranco_top,
        }
