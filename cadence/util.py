from dataclasses import dataclass
from typing import Callable


@dataclass
class OpenRequestInfo:
    # BiConsumer<T, Exception>
    completion_handle: Callable = None
    user_context: object = None

