from src.analytics import completion_rate

def test_completion_rate():
    assert completion_rate(5, 10) == 50
