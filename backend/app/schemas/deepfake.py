from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class DeepfakeResultOut(BaseModel):

    model_config = ConfigDict(protected_namespaces=())
    deepfake_probability: Optional[float] = None
    status: Optional[str] = None
    frames_analyzed: Optional[int] = None
    suspicious_frame_indices: Optional[List[int]] = None
    model_version: Optional[str] = None
