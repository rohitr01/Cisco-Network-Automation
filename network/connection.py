"""
network/connection.py
─────────────────────
A reusable SSH connection class wrapping Netmiko.
"""

import time
import logging
from typing import Dict

# ── Add project root to sys.path so sibling packages resolve ───────────────
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from network.exceptions import (
    DeviceUnreachableError,
    DeviceAuthenticationError,
    CommandExecutionError,
)

logger = logging.getLogger(__name__)

class DeviceConnector:
    """
    SSH connection to a Cisco device via Netmiko.
    Supports retry logic, auth failure detection, and clean disconnect.
    """

    def __init__(self, hostname: str, ip: str, device_type: str, credentials: dict,
                 timeout: int = 30, auth_timeout: int = 20, max_retries: int = 3, retry_delay: int = 5):
        """
        Initialize the DeviceConnector.
        
        Args:
            hostname (str): Name of the device.
            ip (str): IP address of the device.
            device_type (str): Platform type (e.g., 'cisco_ios').
            credentials (dict): Dictionary with 'username', 'password', and optionally 'secret'.
            timeout (int): SSH connection timeout.
            auth_timeout (int): SSH authentication timeout.
            max_retries (int): Maximum number of retry attempts for timeouts.
            retry_delay (int): Delay in seconds between retries.
        """
        self.hostname = hostname
        self.ip = ip
        self.device_type = device_type
        self.credentials = credentials
        self.timeout = timeout
        self.auth_timeout = auth_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._conn = None

    def connect(self) -> bool:
        """
        Establish SSH connection with retries.
        Auth failures: no retry (raise immediately).
        Timeouts: retry up to max_retries.
        """
        # Import netmiko lazily (only when connect() is called)
        from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

        conn_params = {
            "device_type": self.device_type,
            "host": self.ip,
            "username": self.credentials.get("username", ""),
            "password": self.credentials.get("password", ""),
            "secret": self.credentials.get("secret", ""),
            "timeout": self.timeout,
            "auth_timeout": self.auth_timeout,
            "fast_cli": False,
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info("[%s] SSH connection attempt %d/%d to %s", self.hostname, attempt, self.max_retries, self.ip)
                self._conn = ConnectHandler(**conn_params)
                self._conn.enable()
                logger.info("[%s] Connection successful.", self.hostname)
                return True

            except NetmikoAuthenticationException as exc:
                logger.error("[%s] Authentication failed for %s", self.hostname, self.ip)
                raise DeviceAuthenticationError(f"Auth failed for {self.hostname} ({self.ip})") from exc

            except NetmikoTimeoutException as exc:
                logger.warning("[%s] Timeout on attempt %d", self.hostname, attempt)
                if attempt < self.max_retries:
                    logger.info("[%s] Retrying in %ds ...", self.hostname, self.retry_delay)
                    time.sleep(self.retry_delay)
                else:
                    logger.error("[%s] Connection timed out after %d attempts", self.hostname, self.max_retries)
                    raise DeviceUnreachableError(f"Timeout for {self.hostname} ({self.ip})") from exc

        return False

    def execute(self, command: str) -> str:
        """Execute a single command and return raw output."""
        if not self._conn:
            raise CommandExecutionError(f"Cannot execute '{command}' - not connected to {self.hostname}")
            
        try:
            logger.info("[%s] Executing command: %s", self.hostname, command)
            return self._conn.send_command(command)
        except Exception as exc:
            logger.error("[%s] Failed to execute command '%s': %s", self.hostname, command, exc)
            raise CommandExecutionError(f"Failed to execute '{command}' on {self.hostname}") from exc

    def execute_all(self, commands: Dict[str, str]) -> Dict[str, str]:
        """Execute all commands, return {command_name: raw_output}."""
        results = {}
        for cmd_name, cmd_str in commands.items():
            results[cmd_name] = self.execute(cmd_str)
        return results

    def disconnect(self):
        """Gracefully disconnect."""
        if self._conn:
            logger.info("[%s] Disconnecting.", self.hostname)
            try:
                self._conn.disconnect()
            except Exception as exc:
                logger.warning("[%s] Error while disconnecting: %s", self.hostname, exc)
            finally:
                self._conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
