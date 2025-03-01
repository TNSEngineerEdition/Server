import pickle

import overpy
import pytest


@pytest.fixture
def overpass_query_result() -> overpy.Result:
    with open("tests/assets/overpass_query_result.pickle", "rb") as file:
        return pickle.load(file)
