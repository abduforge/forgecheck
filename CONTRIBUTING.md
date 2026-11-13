# Contributing

Thanks for taking an interest in ForgeCheck.

## Development setup

ForgeCheck uses only the Python standard library at runtime.

```bash
python3 -m py_compile forgecheck.py
python3 -m unittest discover -s tests -v
```

## Project principles

- Keep checks local, read-only, and bounded by short timeouts.
- Do not add remote scanning, exploitation, or configuration-changing behavior.
- Keep optional system tools optional; ForgeCheck should still run if they are missing.
- Handle missing files, commands, and permissions without crashing.
- Add or update unit tests for parsing and report changes.
- Never include personal machine reports, IP addresses, credentials, or tokens in commits.

## Pull requests

Describe the change, the reason for it, and the tests you ran. Keep changes focused and document any new command-line behavior.
