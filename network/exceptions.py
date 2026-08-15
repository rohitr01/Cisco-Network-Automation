"""
network/exceptions.py
─────────────────────
Custom exceptions for the network abstraction layer.
"""

class DeviceConnectionError(Exception):
    """Base exception for device connection failures."""

class DeviceUnreachableError(DeviceConnectionError):
    """Device could not be reached (timeout/network)."""

class DeviceAuthenticationError(DeviceConnectionError):
    """Authentication failed — will NOT retry."""

class CommandExecutionError(Exception):
    """A command failed to execute on the device."""
