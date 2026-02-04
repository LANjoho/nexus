from enum import Enum


class RoomStatus(Enum):
    """
    Represents the current state of a clinical room.
    These values should NEVER be changed casually,
    because they are stored in the database.
    """
    
    AVAILABLE = "available"
    WAITING = "waiting"
    #OCCUPIED = "occupied"
    SEEING_PROVIDER = "seeing_provider"
    NEEDS_CLEANING = "needs_cleaning"
    CLEANING = "cleaning"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"
    
    def __str__(self):
        return self.value
    
    
class UpdateSource(Enum):
    """
    Represents where a room status update originated.
    This allows us to distinguish between nurse input 
    and future automated systems
    """
    
    MANUAL = "manual"
    SENSOR = "sensor"
    API = "api"
    
    def __str__(self):
        return self.value