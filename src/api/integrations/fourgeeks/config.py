import os
from pydantic import BaseModel

class FourGeeksConfig(BaseModel):
    username: str = os.getenv("4GEEKS_USERNAME")
    password: str = os.getenv("4GEEKS_PASSWORD") 