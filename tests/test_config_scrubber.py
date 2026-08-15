import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from security.config_scrubber import scrub_config, count_redactions

class TestScrubEnablePassword(unittest.TestCase):
    def test_enable_password_type_0(self):
        raw = 'enable password cisco123'
        result = scrub_config(raw)
        self.assertIn('<REDACTED>', result)
        self.assertNotIn('cisco123', result)
    
    def test_enable_secret_type_5(self):
        raw = 'enable secret 5 $1$abc$xyz'
        result = scrub_config(raw)
        self.assertIn('<REDACTED>', result)
        self.assertNotIn('$1$abc$xyz', result)

class TestScrubUsername(unittest.TestCase):
    def test_username_password(self):
        raw = 'username admin password 0 cisco123'
        result = scrub_config(raw)
        self.assertIn('<REDACTED>', result)
        self.assertNotIn('cisco123', result)
    
    def test_username_secret(self):
        raw = 'username admin secret 5 $1$hash'
        result = scrub_config(raw)
        self.assertIn('<REDACTED>', result)

class TestScrubSnmp(unittest.TestCase):
    def test_snmp_community_ro(self):
        raw = 'snmp-server community public RO'
        result = scrub_config(raw)
        self.assertEqual(result, 'snmp-server community <REDACTED> RO')

    def test_snmp_community_rw(self):
        raw = 'snmp-server community private RW'
        result = scrub_config(raw)
        self.assertNotIn('private', result)

class TestScrubCrypto(unittest.TestCase):
    def test_isakmp_key(self):
        raw = 'crypto isakmp key mysecretkey address 10.0.0.1'
        result = scrub_config(raw)
        self.assertNotIn('mysecretkey', result)
        self.assertIn('10.0.0.1', result)  # address preserved

class TestScrubOspfAuth(unittest.TestCase):
    def test_ospf_auth_key(self):
        raw = ' ip ospf authentication-key mypass'
        result = scrub_config(raw)
        self.assertNotIn('mypass', result)
    
    def test_ospf_md5_key(self):
        raw = ' ip ospf message-digest-key 1 md5 7 myencpass'
        result = scrub_config(raw)
        self.assertNotIn('myencpass', result)

class TestScrubTacacsRadius(unittest.TestCase):
    def test_tacacs_key(self):
        raw = 'tacacs-server key 7 tacacssecret'
        result = scrub_config(raw)
        self.assertNotIn('tacacssecret', result)
    
    def test_radius_key(self):
        raw = 'radius-server key radiussecret'
        result = scrub_config(raw)
        self.assertNotIn('radiussecret', result)

class TestScrubFullConfig(unittest.TestCase):
    def test_full_config_multiple_redactions(self):
        raw = """!
hostname R1
!
enable secret 5 $1$hash123
username admin secret 0 adminpass
!
interface GigabitEthernet0/0
 ip address 192.168.1.1 255.255.255.0
!
snmp-server community public RO
snmp-server community private RW
!
crypto isakmp key mypsk address 10.0.0.2
!
end"""
        result = scrub_config(raw)
        self.assertNotIn('$1$hash123', result)
        self.assertNotIn('adminpass', result)
        self.assertNotIn('public', result)
        self.assertNotIn('private', result)
        self.assertNotIn('mypsk', result)
        self.assertIn('192.168.1.1', result)  # IP preserved
        self.assertIn('hostname R1', result)   # Non-sensitive preserved
        redactions = count_redactions(raw, result)
        self.assertEqual(redactions, 5)  # 5 credentials scrubbed

    def test_no_credentials_unchanged(self):
        raw = """!
hostname R1
interface Gi0/0
 ip address 10.0.0.1 255.255.255.0
!
end"""
        result = scrub_config(raw)
        self.assertEqual(result, raw)  # Nothing changed
