import pymem
from typing import List
from dataclasses import dataclass
import enum
import re
import yaml

pymem.logger.setLevel(pymem.logging.ERROR)

@dataclass
class Player:
    name: str
    player_id: int
    dead: bool
    disconnected: bool
    impostor: bool
    exiled: bool
    is_local: bool

class GameState(enum.Enum):
    MENU = 0
    LOBBY = 1
    DISCUSSION = 2
    TASKS = 3

@dataclass
class MemoryRead:
    players: List[Player]
    game_state: GameState
    game_code: str


class AmongUsMemory:
    def __init__(self):
        self.pm = pymem.Pymem()
        self.exile_causes_end = False
        self.offsets = self._load_offsets()

    def _load_offsets(self):
        with open("client/offsets/offsets.yml", mode='r') as f:
            return yaml.load(f, Loader=yaml.FullLoader)

    def read(self):
        return MemoryRead(players=self.get_all_players(),
                            game_state=self.get_game_state(),
                            game_code=self.get_game_code(),
                            )

    def open_process(self):
        try:
            self.pm.open_process_from_name("Among Us.exe")
            self.base_addr = pymem.process.module_from_name(self.pm.process_handle, "GameAssembly.dll").lpBaseOfDll
            return True
        except Exception:
            return False

    def get_game_state(self):
        meeting_hud_state = self._get_meeting_hud_state()
        game_state = self.read_memory(self.base_addr, self.offsets.gameState, self.pm.read_int)
        state = GameState.MENU
        if game_state == 0:
            state = GameState.MENU
            self.exile_causes_end = True
        if game_state == 1 or game_state == 3:
            state = GameState.LOBBY
            self.exile_causes_end = True
        else:
            if self.exile_causes_end:
                state = GameState.LOBBY
            elif meeting_hud_state < 4:
                state = GameState.DISCUSSION
            else:
                state = GameState.TASKS
        return state

    def _get_meeting_hud_state(self):
        meeting_hud = self.read_memory(self.base_addr, self.offsets.meetingHud, self.pm.read_uint)
        meetingHud_CachePtr = self._get_meeting_hude_cache_ptr(meeting_hud)
        if meetingHud_CachePtr == 0:
            return 4
        return self.read_memory(meeting_hud, self.offsets.meetingHudState, self.pm.read_int, default=4)

    def _get_meeting_hude_cache_ptr(self, meeting_hud):
        if meeting_hud == 0:
            return 0
        return self.read_memory(meeting_hud, self.offsets.meetingHudCachePtr, self.pm.read_uint)

    def get_game_code(self):
        new_code = self.read_string(self.read_memory(self.base_addr, self.offsets.gameCode, self.pm.read_int))
        if new_code:
            split = new_code.split('\r\n')
            if len(split) == 2:
                new_code = split[1]
            else:
                new_code = ''
            if not re.match("^[A-Z]{6}$", new_code):
                new_code = ''
        return new_code


    def _parse_player(self, addr, data, exiledPlayerId):

        return Player()

    def get_all_players(self):
        allPlayersPtr = self.read_memory(self.base_addr, self.offsets.allPlayersPtr, self.pm.read_uint) & 0xffffffff
        allPlayers = self.read_memory(allPlayersPtr, self.offsets.allPlayers, self.pm.read_uint)
        playerCount = self.read_memory(allPlayersPtr, self.offsets.playerCount, self.pm.read_int)
        playerAddrPtr = allPlayers + self.offsets.playerAddrPtr
        exiledPlayerId = self.read_memory(self.base_addr, self.offsets.exiledPlayerId, self.pm.read_int)
        players = []

        for _ in range(min(playerCount, 10)):
            address, last = self.offset_address(playerAddrPtr, self.offsets.player.offsets)
            playerData = self.pm.read_bytes(address + last, self.offsets.player.BufferLength)
            player = self._parse_player(address + last, playerData, exiledPlayerId)
            playerAddrPtr += 4
            players.append(player)
        return players

    def read_string(self, address):
        if address == 0:
            return ''
        length = self.pm.read_int(address + 0x8)
        buffer = self.pm.read_bytes(address + 0xC, length << 1)
        return buffer.encode('utf8')


    def read_memory(self, address, offsets, readfunc, default=0):
        if address == 0:
            return default
        addr, last = self.offset_address(address, offsets)
        if addr == 0:
            return default
        return readfunc(addr + last)

    def offset_address(self, address, offsets): 
        address = address & 0xffffffff

        for offset in offsets[:-1]:
            address = self.pm.read_uint(address + offset)
            if not address:
                 break

        last = offsets[-1] if offsets else 0
        return address, last

    #  https://docs.python.org/3/library/struct.html
    def _generate_struct_str_from_offsets(self):
        vals = ['=']
        for field in self.offsets.player.struct:
            if field.type == "SKIP":
                vals.append(str(field.skip))
                vals.append('x')
            elif field.type == "UINT":
                vals.append('I')
            elif field.type == "BYTE":
                vals.append('c')
        return ''.join(vals)

    def _player_object_from_struct(self, fields):
        pass