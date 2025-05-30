'''Enumeration of possible model states'''
from enum import Enum


class ModelStatus(str, Enum):
    
    INITIAL = "initial"
    BUILDING = "building"
    READY = "ready"
    FAILED = "failed"
    INVALID = "invalid"
    DELETED = "deleted"
    UNKNOWN = "unknown"


class Modelbase(object):
    def __init__(self, id=None, *args, **kwargs):
        self._model_status = ModelStatus.FAILED
        self._user_id = id 
    
    @property
    def model_status(self):
        return self._model_status
    
    @property
    def user_id(self):
        return self._user_id
    
    # Function to modify user_id
    def set_user_id(self, new_id):
        self._user_id = new_id
