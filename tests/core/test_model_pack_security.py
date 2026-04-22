import pickle

import pytest

from AOA.core.models import load_model_pack


class MaliciousPickle:
    def __reduce__(self):
        import os

        return (os.system, ("echo hacked",))


def test_load_model_pack_rejects_non_pkl_suffix(tmp_path):
    bad_path = tmp_path / "model.txt"
    bad_path.write_bytes(b"x")

    with pytest.raises(ValueError, match=".pkl"):
        load_model_pack(bad_path)


def test_load_model_pack_blocks_disallowed_modules(tmp_path):
    payload_path = tmp_path / "malicious.pkl"
    with open(payload_path, "wb") as handle:
        pickle.dump(MaliciousPickle(), handle)

    with pytest.raises(pickle.UnpicklingError, match="not allowed"):
        load_model_pack(payload_path)
