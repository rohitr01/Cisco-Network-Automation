import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Create a mock netmiko module so the lazy import works
mock_netmiko = MagicMock()
sys.modules['netmiko'] = mock_netmiko

from network.connection import DeviceConnector
from network.exceptions import DeviceUnreachableError, DeviceAuthenticationError, CommandExecutionError

class TestDeviceConnector(unittest.TestCase):
    def setUp(self):
        self.credentials = {'username': 'admin', 'password': 'password'}
        self.connector = DeviceConnector(
            hostname='test-router',
            ip='10.0.0.1',
            device_type='cisco_ios',
            credentials=self.credentials,
            max_retries=2,
            retry_delay=0
        )
        # Reset mocks
        mock_netmiko.reset_mock()
        mock_netmiko.ConnectHandler = MagicMock()
        mock_netmiko.NetmikoAuthenticationException = type('NetmikoAuthenticationException', (Exception,), {})
        mock_netmiko.NetmikoTimeoutException = type('NetmikoTimeoutException', (Exception,), {})

    def test_connect_success(self):
        mock_conn = MagicMock()
        mock_netmiko.ConnectHandler.return_value = mock_conn
        
        result = self.connector.connect()
        
        self.assertTrue(result)
        mock_netmiko.ConnectHandler.assert_called_once()
        mock_conn.enable.assert_called_once()

    def test_connect_auth_failure(self):
        mock_netmiko.ConnectHandler.side_effect = mock_netmiko.NetmikoAuthenticationException("Auth failed")
        
        with self.assertRaises(DeviceAuthenticationError):
            self.connector.connect()
            
        mock_netmiko.ConnectHandler.assert_called_once()

    def test_connect_timeout(self):
        mock_netmiko.ConnectHandler.side_effect = mock_netmiko.NetmikoTimeoutException("Timeout")
        
        with self.assertRaises(DeviceUnreachableError):
            self.connector.connect()
            
        self.assertEqual(mock_netmiko.ConnectHandler.call_count, 2)

    def test_connect_timeout_then_success(self):
        mock_conn = MagicMock()
        mock_netmiko.ConnectHandler.side_effect = [
            mock_netmiko.NetmikoTimeoutException("Timeout"),
            mock_conn
        ]
        
        result = self.connector.connect()
        
        self.assertTrue(result)
        self.assertEqual(mock_netmiko.ConnectHandler.call_count, 2)
        mock_conn.enable.assert_called_once()

    def test_execute_success(self):
        mock_conn = MagicMock()
        mock_conn.send_command.return_value = "Cisco IOS Software"
        self.connector._conn = mock_conn
        
        result = self.connector.execute("show version")
        
        self.assertEqual(result, "Cisco IOS Software")
        mock_conn.send_command.assert_called_once_with("show version")

    def test_execute_not_connected(self):
        with self.assertRaises(CommandExecutionError):
            self.connector.execute("show version")

    def test_disconnect(self):
        mock_conn = MagicMock()
        self.connector._conn = mock_conn
        
        self.connector.disconnect()
        
        mock_conn.disconnect.assert_called_once()
        self.assertIsNone(self.connector._conn)

    def test_context_manager(self):
        mock_conn = MagicMock()
        mock_netmiko.ConnectHandler.return_value = mock_conn
        
        with self.connector as conn:
            self.assertEqual(conn, self.connector)
            mock_netmiko.ConnectHandler.assert_called_once()
            
        mock_conn.disconnect.assert_called_once()

if __name__ == '__main__':
    unittest.main()
