# --- Data class to measure runtimes --- #
from dataclasses import dataclass

@dataclass
class SegTimes:
    to_gpu_ms: float | None
    infer_ms:  float
    total_ms:  float