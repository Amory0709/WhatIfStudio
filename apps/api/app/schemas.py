from pydantic import BaseModel


class SwapResponse(BaseModel):
    job_id: str
    watermarked: bool = True
    bytes: int
