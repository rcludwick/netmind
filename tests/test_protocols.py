from netmind.protocols import HamlibParser

def test_hamlib_parser_standard_commands():
    assert HamlibParser.decode(b"F 14074000") == "SET FREQ: 14074000"
    assert HamlibParser.decode(b"f") == "GET FREQ"
    assert HamlibParser.decode(b"M USB 2400") == "SET MODE: USB 2400"
    assert HamlibParser.decode(b"m") == "GET MODE"
    assert HamlibParser.decode(b"L AF 0.5") == "SET LEVEL: AF 0.5"
    assert HamlibParser.decode(b"l AF") == "GET LEVEL: AF"
    assert HamlibParser.decode(b"T 1") == "SET PTT: 1"
    assert HamlibParser.decode(b"t") == "GET PTT"

def test_hamlib_parser_extended_commands():
    assert HamlibParser.decode(b"\\dump_state") == "DUMP STATE"
    assert HamlibParser.decode(b"\\get_powerstat") == "GET POWERSTAT"
    assert HamlibParser.decode(b"\\chk_vfo") == "CHECK VFO"
    assert HamlibParser.decode(b"\\set_vfo VFOA") == "SET VFO: VFOA"
    assert HamlibParser.decode(b"\\get_vfo") == "GET VFO"

def test_hamlib_parser_responses():
    assert HamlibParser.decode(b"RPRT 0") == "SUCCESS"
    assert HamlibParser.decode(b"RPRT -5") == "ERROR: 5"

def test_hamlib_parser_fallbacks():
    assert HamlibParser.decode(b"14074000") == "DATA: 14074000 Hz"
    assert HamlibParser.decode(b"UNKNOWN COMMAND") == "RAW: UNKNOWN COMMAND"
    assert HamlibParser.decode(b"") == "<EMPTY>"
    assert HamlibParser.decode(bytes([0xff, 0xfe, 0xfd])) == "<BINARY: 3 bytes>"
