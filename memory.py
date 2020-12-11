import pymem

pymem.logger.setLevel(pymem.logging.ERROR)

class AmongUsMemory:
    meetingHud = [0x1BE0CB4, 0x5c, 0]
    meetingHudCachePtr = [0x8]
    meetingHudState = [0x84]
    gameState = [0x1BE1074, 0x5C, 0, 0x64]

    allPlayersPtr = [0x1BE0BB8, 0x5c, 0, 0x24]
    allPlayers = [0x08]
    playerCount = [0x0c]
    playerAddrPtr = 0x10
    exiledPlayerId = [0xff, 0x1BE0CB4, 0x5c, 0, 0x94, 0x08]

    gameCode: [0x1B5AB00, 0x5c, 0, 0x20, 0x28]

    offsets = [0, 0]
    isLocal = [0x54]
    localX = [0x60, 0x50]
    localY = [0x60, 0x54]
    remoteX = [0x60, 0x3C]
    remoteY = [0x60, 0x40]
    bufferLength = 56
    offsets = [0, 0]
    inVent = [0x31]

    def __init__(self):
        self.pm = pymem.Pymem('Among Us.exe')
        self.base_addr = pymem.process.module_from_name(self.pm.process_handle, "GameAssembly.dll").lpBaseOfDll

    def parse_all_players(self):
        gameState = self.readMemory(self.base_addr, self.gameState, self.pm.read_int)

        meetingHud = self.readMemory(self.base_addr, self.meetingHud, self.pm.read_uint)
        meetingHud_CachePtr = 0 if meetingHud == 0 else self.readMemory(meetingHud, self.meetingHudCachePtr, self.pm.read_uint)
        meetingHudState = 4 if meetingHud_CachePtr == 0 else self.readMemory(meetingHud, self.meetingHudState, self.pm.read_int, default=4)


        allPlayersPtr = self.readMemory(self.base_addr, self.allPlayersPtr, self.pm.read_uint) & 0xffffffff
        allPlayers = self.readMemory(allPlayersPtr, self.allPlayers, self.pm.read_uint)
        playerCount = self.readMemory(allPlayersPtr, self.playerCount, self.pm.read_int)
        playerAddrPtr = allPlayers + self.playerAddrPtr
        exiledPlayerId = self.readMemory(self.base_addr, self.exiledPlayerId, self.pm.read_int)
        players = []

    '''
        for i in range(min(playerCount, 10)):
            address, last = self.offsetAddress(playerAddrPtr, this.offsets.player.offsets);
            let playerData = readBuffer(this.amongUs.handle, address + last, this.offsets.player.bufferLength);
            let player = this.parsePlayer(address + last, playerData);
            playerAddrPtr += 4;
            players.push(player);

            if (player.name === '' || player.id === exiledPlayerId || player.isDead || player.disconnected) continue;

            if (player.isImpostor)
                impostors++;
            else
                crewmates++;
        }
    '''


    def readMemory(self, address, offsets, readfunc, default=0):
        if address == 0:
            return default
        addr, last = self.offsetAddress(address, offsets)
        if addr == 0:
            return default
        return readfunc(addr + last)

    def offsetAddress(self, address, offsets): 
        address = address & 0xffffffff

        for offset in offsets[:-1]:
            address = self.pm.read_uint(address + offset)
            if not address:
                 break

        last = offsets[-1] if offsets else 0
        return address, last

