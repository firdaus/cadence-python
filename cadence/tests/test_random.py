import random
import uuid


def test_python_random_determinism():
    generator = random.Random()
    generator.seed("theseed", version=2)
    assert generator.randint(0, 100) == 72
    assert generator.randint(0, 100) == 90
    assert generator.randint(0, 100) == 41
    assert generator.randint(0, 100) == 16
    assert generator.randint(0, 100) == 11


def test_python_uuid3_determinism():
    assert uuid.uuid3(uuid.UUID("8d3149e9-71d3-4ad3-9216-bfbf0473b7c6"), "25") == uuid.UUID('db602869-db61-341b-9e01-81393de6c9b0')
