import pytest

from tools import TradeCalculatorTool, safe_eval


def test_evaluates_arithmetic():
    assert safe_eval("5000 / (25 * 2)") == 100
    assert safe_eval("-3 + 4") == 1


def test_rejects_code_injection():
    with pytest.raises(ValueError):
        safe_eval("__import__('os').system('echo hacked')")


def test_tool_returns_error_message_instead_of_raising():
    assert TradeCalculatorTool()._run("open('/etc/passwd')") == "Error in calculation"
    assert TradeCalculatorTool()._run("1 / 0") == "Error in calculation"
