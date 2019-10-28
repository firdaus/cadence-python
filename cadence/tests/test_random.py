import random


def test_python_random_determinism():
    generator = random.Random()
    generator.seed("theseed", version=2)
    assert generator.randint(0, 100) == 72
    assert generator.randint(0, 100) == 90
    assert generator.randint(0, 100) == 41
    assert generator.randint(0, 100) == 16
    assert generator.randint(0, 100) == 11
