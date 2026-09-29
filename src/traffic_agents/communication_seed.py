from __future__ import annotations

import json
from hashlib import sha256


def derive_communication_rng_seed(
    *,
    simulation_seed: int,
    delay_steps: int,
    drop_probability: float,
) -> int:
    payload = {
        "simulation_seed": simulation_seed,
        "delay_steps": delay_steps,
        "drop_probability": drop_probability,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return int.from_bytes(sha256(encoded).digest()[:8], byteorder="big", signed=False)
