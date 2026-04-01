from dataclasses import dataclass


@dataclass(slots=True)
class RecordingController:
    calls: list[tuple[str, int, bool]]

    def open(self, url: str, new: int, autoraise: bool) -> bool:
        self.calls.append((url, new, autoraise))
        return True


@dataclass(slots=True)
class OpenCallRecorder:
    calls: list[tuple[str, int, bool]]

    def __call__(self, url: str, new: int, autoraise: bool) -> bool:
        self.calls.append((url, new, autoraise))
        return True


@dataclass(slots=True)
class ControllerFactory:
    controller: object
    requested: bool = False

    def __call__(self, _browser: str | None = None) -> object:
        self.requested = True
        return self.controller


class MacOSXOSAScript:
    def __init__(self) -> None:
        self.open_calls = 0
        self.last_open_request: tuple[str, int, bool] | None = None

    def open(self, url: str, new: int, autoraise: bool) -> bool:
        self.last_open_request = (url, new, autoraise)
        self.open_calls += 1
        return True
