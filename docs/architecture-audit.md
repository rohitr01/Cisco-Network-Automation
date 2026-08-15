# Architecture Audit: Cisco Network Automation

## 1. Current Architecture
The project is divided into two distinct tools (v1 for backups, v2 for information collection and reporting). It utilizes a data pipeline that flows linearly: 
`devices.csv` -> SSH Data Collection (Netmiko) / Mock Data -> Pure Python Parsers -> Health Analysis -> JSON Output -> HTML Report Generation (Jinja2). 

Configuration (paths, timeouts, thresholds) is centralized in `config/settings.py`, and credentials are provided safely via environment variables or runtime prompts. The architecture cleanly separates parsing (`parsers.py`) and analysis (`health_check.py`) from I/O logic, making those components highly testable. 

## 2. Dependencies and Versions
From `requirements.txt`:
- `netmiko>=4.3.0` (SSH connection to network devices)
- `jinja2>=3.1.0` (HTML report templating)
- `rich>=13.7.0` (CLI output formatting)
- `python-dotenv>=1.0.0` (Environment variable loading)
- `paramiko>=3.4.0` (Underlying SSH protocol implementation for Netmiko)

## 3. Duplicated Code
Several core functionalities are duplicated across the v1 and v2 tools:
- **Inventory Loading**: `load_inventory` is identically defined in `backup/backup_tool.py:78` and `collector/info_collector.py:85`.
- **Logging Setup**: `_setup_logging` is identically defined in `backup/backup_tool.py:59` and `collector/info_collector.py:66`.
- **SSH Connection & Retry Logic**: The ConnectHandler instantiation and its associated retry loop (handling Timeouts and Auth errors) is duplicated across `_backup_one_real` (`backup/backup_tool.py:95`) and `_collect_real` (`collector/info_collector.py:99`).
- **CLI Arguments**: The `argparse` configuration for `--prompt` and `--dry-run` is duplicated in the `main()` functions of both tools.

## 4. Coupling Issues
- **`sys.path` Hacks**: Because the codebase is not packaged appropriately (missing `setup.py` / `pyproject.toml`), many files explicitly modify `sys.path` to allow imports from sibling directories:
  - `backup/backup_tool.py:44`
  - `collector/info_collector.py:36`
  - `reports/report_generator.py:17`
  - `show_health.py:6`
  - `tests/test_parsers.py:15`
  - `tests/test_integration.py:8`

## 5. Unsafe Design Patterns
- **Broad Exception Catching**: In the SSH retry loops, a bare `except Exception as exc:` is used (`backup/backup_tool.py:134`, `collector/info_collector.py:144`), which can mistakenly catch and swallow critical errors like `KeyboardInterrupt` or `SystemExit`.
- **Synchronous Delays**: The retry loop utilizes `time.sleep(RETRY_DELAY)` blocking the single main thread completely on failures.

## 6. Missing Abstractions
- **No Connection Layer**: SSH connection details are handled inside individual tool functions rather than in a unified `ConnectionManager` or `Device` class.
- **No Unified CLI**: The project lacks a single entry point (like `cli.py` via `click` or `argparse` subparsers). Users must invoke individual scripts manually.

## 7. Import Issues
- **Local/Inline Imports**: Libraries like `netmiko` and `rich` are imported locally inside functions (e.g., `backup_tool.py:101`). While this enables `--dry-run` to work without installing dependencies, it is an anti-pattern that obscures dependencies and hampers robust testing.

## 8. Test Coverage Gaps
- **Missing Mock Injection**: The integration tests do not use `unittest.mock.patch` to mock `ConnectHandler` during live device testing functions. Thus, real execution paths (and failure/retry logic) are effectively untested.
- **CLI Flow**: The `main()` functions parsing arguments and orchestrating execution lack testing.

## 9. Real-Device Limitations
- **Sequential Bottleneck**: Processing 100+ devices sequentially is unacceptably slow.
- **Output Size / Parsing Time**: Gathering massive BGP routing tables or MAC address tables over SSH without filtering can cause extreme delays or memory exhaustion.

## 10. What is Good and Should Be Preserved
- **Pure Functions**: The parsing (`parsers.py`) and analysis (`health_check.py`) logic are excellently isolated as pure functions, facilitating rock-solid unit tests.
- **Mocking System**: The `--dry-run` mode utilizing `mock_devices.py` is a fantastic feature for offline demos and CI/CD pipelines.
- **Security Posture**: Credentials are not hardcoded. The project forces standard and secure `.env` or explicit prompt practices.
- **Data Persistence Strategy**: Storing raw parsed JSON inside `data/` before rendering HTML decoupled data gathering from presentation seamlessly.

---

## Recommended Architecture
See implementation_plan.md for the final proposed structure.

## Critical Problems
1. Hardcoded `sys.path` inserts cause fragile imports across the project.
2. High code duplication between v1 and v2 orchestrators.
3. No connection abstraction layer.

## Files to Modify
- `backup/backup_tool.py` (Refactor to use shared core/network modules)
- `collector/info_collector.py` (Refactor to use shared core/network modules)
- `reports/report_generator.py` (Remove `sys.path` hack)
- `collector/parsers.py` (OSPF route parsing, interface protocol fix)
- `analysis/health_check.py` (OSPF 2WAY context-aware)

## Files That Should Remain Unchanged
- `mock/mock_devices.py` (Reliable test data)
- `templates/report.html.j2` (Effective presentation layer)
