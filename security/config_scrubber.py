from __future__ import annotations
import re

# Patterns that contain sensitive credentials in Cisco IOS/IOS-XE configs
_SENSITIVE_PATTERNS: list[tuple[re.Pattern, str]] = [
    # enable password / enable secret
    (re.compile(r'^(enable\s+(?:password|secret)\s+(?:\d\s+)?)\S+', re.MULTILINE | re.IGNORECASE),
     r'\1<REDACTED>'),
    # username ... password / secret
    (re.compile(r'^(username\s+\S+\s+(?:password|secret)\s+(?:\d\s+)?)\S+', re.MULTILINE | re.IGNORECASE),
     r'\1<REDACTED>'),
    # snmp-server community
    (re.compile(r'^(snmp-server\s+community\s+)\S+(.*)', re.MULTILINE | re.IGNORECASE),
     r'\1<REDACTED>\2'),
    # crypto isakmp key
    (re.compile(r'^(crypto\s+isakmp\s+key\s+(?:\d\s+)?)\S+(.*)', re.MULTILINE | re.IGNORECASE),
     r'\1<REDACTED>\2'),
    # ip ospf authentication-key / message-digest-key
    (re.compile(r'^(\s*ip\s+ospf\s+(?:authentication-key|message-digest-key\s+\d+\s+md5(?:\s+\d)?)\s+)\S+', re.MULTILINE | re.IGNORECASE),
     r'\1<REDACTED>'),
    # key-string (used in key chains)
    (re.compile(r'^(\s*key-string\s+)\S+', re.MULTILINE | re.IGNORECASE),
     r'\1<REDACTED>'),
    # tacacs-server key / radius-server key  
    (re.compile(r'^((?:tacacs|radius)-server\s+key\s+(?:\d\s+)?)\S+', re.MULTILINE | re.IGNORECASE),
     r'\1<REDACTED>'),
    # wpa-psk ascii / hex
    (re.compile(r'^(\s*wpa-psk\s+(?:ascii|hex)\s+(?:\d\s+)?)\S+', re.MULTILINE | re.IGNORECASE),
     r'\1<REDACTED>'),
]


def scrub_config(raw_config: str) -> str:
    """Sanitize a Cisco running-config by replacing credential values with <REDACTED>.
    
    The original configuration string is never modified — a new sanitized copy is returned.
    """
    sanitized = raw_config
    for pattern, replacement in _SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


def count_redactions(original: str, sanitized: str) -> int:
    """Return the number of <REDACTED> markers added by scrubbing."""
    return sanitized.count('<REDACTED>') - original.count('<REDACTED>')
