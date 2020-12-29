import pymem
from typing import List
from dataclasses import dataclass
import enum
import re
import struct
import numpy as np

pymem.logger.setLevel(pymem.logging.CRITICAL)

@dataclass
class Player:
    playerId: int
    name: str
    dead: bool
    disconnected: bool
    impostor: bool
    isLocal: bool
    inVent: bool
    pos: np.ndarray

class GameState(enum.Enum):
    MENU = 0
    LOBBY = 1
    DISCUSSION = 2
    MEANDERING = 3

@dataclass
class MemoryRead:
    players: List[Player]
    local_player: Player
    game_state: GameState
    game_code: str


class AmongUsMemory:
    def __init__(self):
        self.pm = None
        self.offsets = None
        self.struct_format = None

    def set_offsets(self, offsets):
        self.offsets = offsets
        self.struct_format = self._struct_format_from_offsets()

    def has_offsets(self) -> bool:
        return self.offsets is not None and self.struct_format is not None

    def read(self):
        if not self.pm:
            return None

        players, local_player = self.get_all_players()
        return MemoryRead(players=players,
                            local_player=local_player,
                            game_state=self.get_game_state(),
                            game_code=self.get_game_code(),
                            )

    def open_process(self):
        try:
            self.pm = pymem.Pymem("Among Us.exe")
            self.base_addr = pymem.process.module_from_name(self.pm.process_handle, "GameAssembly.dll").lpBaseOfDll
            return True
        except:
            return False

    def get_game_state(self):
        meeting_hud_state = self._get_meeting_hud_state()
        game_state = self.read_memory(self.base_addr, self.offsets['gameState'], self.pm.read_int)
        state = GameState.MENU
        if game_state == 0:
            state = GameState.MENU
        if game_state == 1 or game_state == 3:
            state = GameState.LOBBY
        else:
            if meeting_hud_state < 4:
                state = GameState.DISCUSSION
            else:
                state = GameState.MEANDERING
        return state

    def _get_meeting_hud_state(self):
        meeting_hud = self.read_memory(self.base_addr, self.offsets['meetingHud'], self.pm.read_uint)
        meetingHud_CachePtr = self._get_meeting_hude_cache_ptr(meeting_hud)
        if meetingHud_CachePtr == 0:
            return 4
        return self.read_memory(meeting_hud, self.offsets['meetingHudState'], self.pm.read_int, default=4)

    def _get_meeting_hude_cache_ptr(self, meeting_hud):
        if meeting_hud == 0:
            return 0
        return self.read_memory(meeting_hud, self.offsets['meetingHudCachePtr'], self.pm.read_uint)

    def get_game_code(self):
        new_code = self.read_string(self.read_memory(self.base_addr, self.offsets['gameCode'], self.pm.read_int))
        if new_code:
            split = new_code.split('\r\n')
            if len(split) == 2:
                new_code = split[1]
            else:
                new_code = ''
            if not re.match("^[A-Z]{6}$", new_code):
                new_code = ''
        return new_code

    def get_all_players(self):
        allPlayersPtr = self.read_memory(self.base_addr, self.offsets['allPlayersPtr'], self.pm.read_ulonglong) & 0xffffffff
        allPlayers = self.read_memory(allPlayersPtr, self.offsets['allPlayers'], self.pm.read_ulonglong)
        playerCount = self.read_memory(allPlayersPtr, self.offsets['playerCount'], self.pm.read_int)
        playerAddrPtr = allPlayers + self.offsets['playerAddrPtr']
        players = []
        local_player = None

        for _ in range(min(playerCount, 10)):
            address, last = self.offset_address(playerAddrPtr, self.offsets['player']['offsets'])
            playerData = self.pm.read_bytes(address + last, self.offsets['player']['bufferLength'])
            player = self._parse_player(playerData)
            playerAddrPtr += 4
            if player.isLocal:
                local_player = player
            else:
                players.append(player)
        return players, local_player

    def _parse_player(self, data):
        values = self._named_fields_from_struct(struct.unpack(self.struct_format, data))
        object_ptr = values['objectPtr']

        is_local = self.read_memory(object_ptr, self.offsets['player']['isLocal'], self.pm.read_int)

        position_offsets = self._get_position_offsets(is_local)

        x_pos = self.read_memory(object_ptr, position_offsets[0], self.pm.read_float)
        y_pos = self.read_memory(object_ptr, position_offsets[1], self.pm.read_float)
        in_vent = self.read_memory(object_ptr, self.offsets['player']['inVent'], self.pm.read_uchar) != 0

        return Player(
            name=self.read_string(values['name']),
            playerId=values['id'],
            disconnected=values['disconnected'],
            impostor=values['impostor'],
            dead=values['dead'],
            inVent=in_vent,
            isLocal=is_local,
            pos=np.array((x_pos, y_pos), dtype=np.float),
        )

    def _get_position_offsets(self, is_local):
        if is_local:
            return (self.offsets['player']['localX'], self.offsets['player']['localY'])
        return (self.offsets['player']['remoteX'], self.offsets['player']['remoteY'])

    #  https://docs.python.org/3/library/struct.html
    def _struct_format_from_offsets(self):
        vals = ['=']
        for field in self.offsets['player']['struct']:
            if field['type'] == "SKIP":
                vals.append(str(field['skip']))
                vals.append('x')
            elif field['type'] == "UINT":
                vals.append('I')
            elif field['type'] == "BYTE":
                vals.append('?')
        return ''.join(vals)

    def _named_fields_from_struct(self, fields):
        return {k: v for k, v in zip((x['name'] for x in self.offsets['player']['struct'] if x['name'] != 'unused'), fields)}

    def read_string(self, address):
        if address == 0:
            return ''
        length = self.pm.read_int(address + 0x8)
        buffer = self.pm.read_bytes(address + 0xC, length << 1)
        return buffer.decode('utf16')

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