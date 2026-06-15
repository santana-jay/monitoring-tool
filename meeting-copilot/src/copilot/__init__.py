"""Background Meeting Co-pilot.

A cross-platform desktop app that quietly captures system/loopback audio,
transcribes it locally, keeps structured notes, and surfaces grounded,
cited, confidence-gated reply suggestions using the Anthropic Claude API.

The core (config, persistence, retrieval grounding, AI client, validation)
is importable without any UI / audio / ML dependencies installed, so it can
be unit-tested in isolation.
"""

__version__ = "0.1.0"
