"""Unit tests for UBSan and Uninitialized variable analyzer."""

from ripley.sanitizers import SanitizerAnalyzer


def test_parse_compiler_uninitialized_warnings():
    analyzer = SanitizerAnalyzer()
    raw_stderr = """
    tp.c:12:9: warning: 'resultado' is used uninitialized in this function [-Wuninitialized]
       12 |     int x = resultado + 5;
          |         ^~~~~~~~~~~~~
    tp.c:20:5: error: 'puntero' may be used uninitialized [-Wmaybe-uninitialized]
    """
    findings = analyzer.parse_compiler_uninitialized_warnings(raw_stderr)
    assert len(findings) == 2
    assert findings[0].category == "UNINITIALIZED_VAR"
    assert "resultado" in findings[0].message
    assert findings[0].line == 12
    assert "puntero" in findings[1].message


def test_parse_ubsan_runtime_errors():
    analyzer = SanitizerAnalyzer()
    raw_stderr = """
    tp.c:15:10: runtime error: signed integer overflow: 2147483647 + 1 cannot be represented in type 'int'
    tp.c:25:8: runtime error: division by zero
    """
    findings = analyzer.parse_ubsan_runtime_errors(raw_stderr)
    assert len(findings) == 2
    assert findings[0].category == "INTEGER_OVERFLOW"
    assert findings[0].line == 15
    assert findings[1].category == "DIVISION_BY_ZERO"
    assert findings[1].line == 25


def test_parse_conversion_warnings():
    analyzer = SanitizerAnalyzer()
    raw_stderr = """
    tp.c:30:15: warning: conversion to 'size_t' from 'int' may change the sign of the result [-Wsign-conversion]
    """
    findings = analyzer.parse_conversion_warnings(raw_stderr)
    assert len(findings) == 1
    assert findings[0].category == "SIGN_CONVERSION"
    assert findings[0].line == 30


def test_parse_alignment_errors():
    analyzer = SanitizerAnalyzer()
    raw_stderr = """
    tp.c:45:8: runtime error: member access within misaligned address 0x7ffd9a for type 'struct Nodo'
    """
    findings = analyzer.parse_ubsan_runtime_errors(raw_stderr)
    assert len(findings) == 1
    assert findings[0].category == "UNALIGNED_ACCESS"
    assert findings[0].line == 45

