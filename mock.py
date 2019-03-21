import uuid
class AudioFile:
    def __init__(self, *args):
        pass

    def __enter__(self):
        return "file"

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class Recognizer:
    def record(self, *args):
        return 'audio'

    def recognize_google(self, *args, **kwargs):
        return f'randomName{uuid.uuid4()}'


class RequestError(Exception):
    pass


class UnknownValueError(Exception):
    pass
