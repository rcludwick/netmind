import re
from typing import Optional

class HamlibParser:
    """
    Parses Hamlib 'rigctld' TCP protocol commands into human-readable descriptions.
    """
    
    # Regex patterns for common Hamlib commands
    PATTERNS = [
        (r"^F\s+(\d+)", "SET FREQ"),
        (r"^f", "GET FREQ"),
        (r"^M\s+(\w+)\s+(\d+)", "SET MODE"),
        (r"^m", "GET MODE"),
        (r"^L\s+(\w+)\s+([\d\.]+)", "SET LEVEL"),
        (r"^l\s+(\w+)", "GET LEVEL"),
        (r"^T\s+([01])", "SET PTT"),
        (r"^t", "GET PTT"),
        (r"^\\dump_state", "DUMP STATE"),
        (r"^\\get_powerstat", "GET POWERSTAT"),
        (r"^\\chk_vfo", "CHECK VFO"),
        (r"^\\set_vfo\s+(\w+)", "SET VFO"),
        (r"^\\get_vfo", "GET VFO"),
        (r"^RPRT\s+0", "SUCCESS"),
        (r"^RPRT\s+-(\d+)", "ERROR")
    ]

    @classmethod
    def decode(cls, data: bytes) -> str:
        """
        Decodes bytes into a semantic description if it matches Hamlib syntax.
        Falls back to raw string representation.
        """
        try:
            text = data.decode("utf-8").strip()
        except UnicodeDecodeError:
            return f"<BINARY: {len(data)} bytes>"

        if not text:
            return "<EMPTY>"

        # Check against known patterns
        for pattern, label in cls.PATTERNS:
            match = re.match(pattern, text)
            if match:
                args = " ".join(match.groups())
                return f"{label}: {args}" if args else label
        
        # Heuristic: If it looks like a frequency (just numbers), label it
        if text.isdigit() and len(text) > 6:
            return f"DATA: {text} Hz"

        return f"RAW: {text}"