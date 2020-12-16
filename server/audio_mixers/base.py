import abc
from server.client_object import ClientObject
 
class AudioMixerBase(abc.ABC):

    @abc.abstractmethod
    def mix(self, destination_client: ClientObject, all_voice_data: dict):
        pass