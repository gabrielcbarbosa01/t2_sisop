import struct

# Configurações
FAT_FREE = 0x0000
FAT_EOF = 0x7FFF
FAT_RESERVED = 0x7FFE
FAT_ENTRIES = 2048

class FileAllocationTable:
    def __init__(self):
        self.fat = [FAT_FREE] * 2048  # FAT com 2048 entradas

    def initialize(self):
        """Inicializa a FAT com blocos reservados."""
        for i in range(4):  # Reservar os blocos da FAT
            self.fat[i] = FAT_RESERVED

    def find_free_block(self):
        """Encontra o índice do primeiro bloco livre na FAT."""
        for i, entry in enumerate(self.fat):
            if entry == FAT_FREE:  # Verifica se o bloco está livre
                return i
        return -1  # Retorna -1 se nenhum bloco livre estiver disponível

    def to_bytes(self):
        """Converte a FAT em bytes para persistência."""
        return struct.pack("2048H", *self.fat)

    def from_bytes(self, data):
        """Carrega a FAT a partir de bytes."""
        self.fat = list(struct.unpack("2048H", data))

