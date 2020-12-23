import abc
from server.client_object import ClientObject
from server.settings import ServerSettings
 
class AudioMixerBase(abc.ABC):

    @abc.abstractstaticmethod
    def mix(destination_client: ClientObject, all_voice_data: dict, settings: ServerSettings):
        pass