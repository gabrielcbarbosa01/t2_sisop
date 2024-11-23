import os
import struct
from allocation_table import FileAllocationTable, FAT_FREE, FAT_EOF

# Configurações
BLOCK_SIZE = 1024
TOTAL_BLOCKS = 2048
FAT_BLOCKS = 4        # Quantidade de blocos reservados para a FAT
ROOT_BLOCKS = 1       # Bloco reservado para o diretório raiz
ROOT_ENTRIES = 32     # Máximo de entradas no diretório raiz
DIR_EMPTY = 0x00      # Entrada de diretório vazia
DIR_DIRECTORY = 0x02  # Diretório
DIR_FILE = 0x01       # Arquivo regular

FILESYSTEM = "filesystem.dat"


class DirectoryEntry:
    """Representa uma entrada de diretório."""
    def __init__(self, filename="", attributes=DIR_EMPTY, first_block=0, size=0):
        self.filename = filename.ljust(25)[:25]
        self.attributes = attributes
        self.first_block = first_block
        self.size = size

    def to_bytes(self):
        """Converte a entrada de diretório para bytes."""
        return struct.pack("25sBHI", self.filename.encode(), self.attributes, self.first_block, self.size)

    @staticmethod
    def from_bytes(data):
        """Cria uma entrada de diretório a partir de bytes."""
        filename, attributes, first_block, size = struct.unpack("25sBHI", data)
        return DirectoryEntry(filename.decode().strip(), attributes, first_block, size)


class FileSystemOperations:
    """Gerencia as operações do sistema de arquivos."""
    def __init__(self):
        self.fat = FileAllocationTable()
        self.root = [DirectoryEntry() for _ in range(ROOT_ENTRIES)]

    def initialize_filesystem(self):
        """Inicializa o sistema de arquivos."""
        with open(FILESYSTEM, "wb") as f:
            # Inicializa a FAT
            self.fat.initialize()
            f.write(self.fat.to_bytes())

            # Inicializa o diretório raiz
            root_bytes = [entry.to_bytes() for entry in self.root]
            f.write(b"".join(root_bytes))

            # Preenche os blocos de dados restantes com zeros
            f.write(b"\x00" * (BLOCK_SIZE * (TOTAL_BLOCKS - FAT_BLOCKS - ROOT_BLOCKS)))
        print("Sistema de arquivos inicializado.")

    def mkdir(self, path):
        """Cria um novo diretório no diretório raiz."""
        if not path.startswith("/"):
            print("Erro: Caminho inválido. Deve começar com '/'.")
            return

        dir_name = path.strip("/")
        if len(dir_name) > 25:
            print("Erro: Nome do diretório muito longo. Máximo de 25 caracteres.")
            return

        # Carregar o sistema de arquivos
        self.load_filesystem()

        # Verificar se o diretório já existe
        for entry in self.root:
            if entry.filename.strip() == dir_name:
                print(f"Erro: Diretório '{dir_name}' já existe.")
                return

        # Procurar uma entrada vazia no diretório raiz
        for i, entry in enumerate(self.root):
            if entry.attributes == DIR_EMPTY:
                # Encontrar um bloco livre na FAT
                free_block = self.fat.find_free_block()
                if free_block == -1:
                    print("Erro: Não há blocos livres disponíveis.")
                    return

                # Atualizar a FAT e criar a entrada do diretório
                self.fat.fat[free_block] = FAT_EOF
                self.root[i] = DirectoryEntry(
                    filename=dir_name,
                    attributes=DIR_DIRECTORY,
                    first_block=free_block,
                    size=0,
                )
                print(f"Diretório '{dir_name}' criado com sucesso.")
                break
        else:
            print("Erro: Diretório raiz cheio. Não é possível criar novos diretórios.")
            return

        # Persistir alterações no disco
        with open(FILESYSTEM, "r+b") as f:
            # Atualizar a FAT
            f.seek(0)
            f.write(self.fat.to_bytes())

            # Atualizar o diretório raiz
            root_bytes = [entry.to_bytes() for entry in self.root]
            f.seek(FAT_BLOCKS * BLOCK_SIZE)
            f.write(b"".join(root_bytes))

    def fat_info(self):
        """Exibe informações sobre a capacidade usada e livre na FAT."""
        used_blocks = sum(1 for entry in self.fat.fat if entry != FAT_FREE)
        free_blocks = len(self.fat.fat) - used_blocks
        total_blocks = len(self.fat.fat)

        used_percentage = (used_blocks / total_blocks) * 100
        free_percentage = (free_blocks / total_blocks) * 100

        print("Informações da FAT:")
        print(f" - Blocos Totais: {total_blocks}")
        print(f" - Blocos Usados: {used_blocks} ({used_percentage:.2f}%)")
        print(f" - Blocos Livres: {free_blocks} ({free_percentage:.2f}%)")

    def list_directory(self, path="/"):
        """Lista o conteúdo de um diretório."""
        self.load_filesystem()

        # Verifica se o caminho especificado é o diretório raiz
        if path == "/":
            current_directory = self.root
        else:
            # Navegar até o subdiretório especificado
            parts = path.strip("/").split("/")
            current_directory = self.root
            for part in parts:
                for entry in current_directory:
                    if entry.filename.strip() == part and entry.attributes == DIR_DIRECTORY:
                        current_directory = self._load_directory(entry.first_block)
                        break
                else:
                    print(f"Erro: Diretório '{path}' não encontrado.")
                    return

        # Listar o conteúdo do diretório atual
        print(f"Conteúdo do diretório '{path}':")
        for entry in current_directory:
            if entry.attributes != DIR_EMPTY:
                tipo = "Diretório" if entry.attributes == DIR_DIRECTORY else "Arquivo"
                print(f"{entry.filename.strip():<25} - {tipo} - {entry.size} bytes")

    def create(self, path):
        """Cria um novo arquivo no diretório raiz ou em um subdiretório."""
        if not path.startswith("/"):
            raise ValueError("Caminho inválido. Deve começar com '/'.")

        # Dividir o caminho em diretórios e o nome do arquivo
        parts = path.strip("/").split("/")
        file_name = parts[-1]  # O último elemento é o nome do arquivo
        if len(file_name) > 25:
            raise ValueError("Erro: Nome do arquivo muito longo. Máximo de 25 caracteres.")

        # Carregar o sistema de arquivos
        self.load_filesystem()

        # Navegar até o subdiretório, se necessário
        current_directory = self.root
        for part in parts[:-1]:  # Itera pelos diretórios no caminho
            for entry in current_directory:
                if entry.filename.strip() == part and entry.attributes == DIR_DIRECTORY:
                    current_directory = self._load_directory(entry.first_block)
                    break
            else:
                raise FileNotFoundError(f"Erro: Diretório '{part}' não encontrado.")

        # Verificar se o arquivo já existe
        for entry in current_directory:
            if entry.filename.strip() == file_name and entry.attributes != DIR_EMPTY:
                raise FileExistsError(f"Erro: Arquivo '{file_name}' já existe.")

        # Procurar uma entrada vazia no diretório atual
        for entry in current_directory:
            if entry.attributes == DIR_EMPTY:
                # Encontrar um bloco livre na FAT
                free_block = self.fat.find_free_block()
                if free_block == -1:
                    raise RuntimeError("Erro: Não há blocos livres disponíveis.")

                # Atualizar a FAT e criar a entrada do arquivo
                self.fat.fat[free_block] = FAT_EOF
                entry.filename = file_name.ljust(25)[:25]
                entry.attributes = DIR_FILE
                entry.first_block = free_block
                entry.size = 0
                break
        else:
            raise RuntimeError("Erro: Diretório cheio. Não é possível criar novos arquivos.")

        # Persistir alterações
        self.persist_changes()
        print(f"Arquivo '{file_name}' criado com sucesso.")


    def _load_directory(self, block_number):
        """Carrega um diretório a partir de um bloco."""
        with open(FILESYSTEM, "rb") as f:
            f.seek(block_number * BLOCK_SIZE)
            data = f.read(BLOCK_SIZE)
            return [DirectoryEntry.from_bytes(data[i * 32: (i + 1) * 32]) for i in range(ROOT_ENTRIES)]

    def _persist_directory(self, directory, block_number):
        """Persiste um diretório no disco."""
        with open(FILESYSTEM, "r+b") as f:
            f.seek(block_number * BLOCK_SIZE)
            directory_data = b"".join(entry.to_bytes() for entry in directory)
            f.write(directory_data)

    def load_filesystem(self):
        """Carrega a FAT e o diretório raiz do disco."""
        if not os.path.exists(FILESYSTEM):
            raise FileNotFoundError("Sistema de arquivos não encontrado. Execute o comando 'init' primeiro.")

        with open(FILESYSTEM, "rb") as f:
            # Carregar FAT
            fat_data = f.read(FAT_BLOCKS * BLOCK_SIZE)
            self.fat.from_bytes(fat_data)

            # Carregar diretório raiz
            root_data = f.read(ROOT_BLOCKS * BLOCK_SIZE)
            self.root = [DirectoryEntry.from_bytes(root_data[i * 32: (i + 1) * 32]) for i in range(ROOT_ENTRIES)]

        print("Sistema de arquivos carregado com sucesso.")

    def unlink(self, path):
        """Exclui um arquivo ou diretório."""
        # Parse o caminho
        directory_path, name = self.parse_path(path)

        # Localizar a entrada do diretório
        self.load_filesystem()
        directory = self.root if directory_path == "/" else self._load_directory(directory_path)
        dir_entry = self.find_dir_entry(directory, name)
        if not dir_entry:
            raise FileNotFoundError(f"Arquivo ou diretório '{name}' não encontrado.")

        # Validar condições
        if dir_entry.attributes == DIR_DIRECTORY:
            if not self.is_directory_empty(dir_entry):
                raise Exception(f"Diretório '{name}' não está vazio.")

        # Liberar blocos na FAT
        if dir_entry.first_block != 0:
            self.free_fat_blocks(dir_entry.first_block)

        # Remover a entrada do diretório
        self.remove_dir_entry(directory, name)

        # Persistir alterações
        self.persist_changes()
        print(f"'{path}' removido com sucesso.")


    def parse_path(self, path):
        """Divide o caminho em diretório pai e nome."""
        if not path.startswith("/"):
            raise ValueError("Caminho inválido. Deve começar com '/'.")

        parts = path.strip("/").split("/")
        if len(parts) == 1:
            return "/", parts[0]  # Diretório raiz e nome do arquivo/diretório
        return "/".join(parts[:-1]), parts[-1]  # Diretório pai e nome
    
    def find_dir_entry(self, directory, name):
        """Procura por uma entrada de diretório com o nome especificado."""
        for entry in directory:
            if entry.filename.strip() == name and entry.attributes != DIR_EMPTY:
                return entry
        return None
    
    def is_directory_empty(self, dir_entry):
        """Verifica se um diretório está vazio."""
        directory_block = self._load_directory(dir_entry.first_block)
        for entry in directory_block:
            if entry.attributes != DIR_EMPTY:
                return False
        return True
    
    def free_fat_blocks(self, first_block):
        """Libera os blocos na FAT começando pelo bloco especificado."""
        current_block = first_block
        while current_block != FAT_EOF:
            next_block = self.fat.fat[current_block]
            self.fat.fat[current_block] = FAT_FREE  # Marca o bloco como livre
            current_block = next_block

    def remove_dir_entry(self, directory, name):
        """Remove a entrada de diretório pelo nome."""
        for entry in directory:
            if entry.filename.strip() == name:
                entry.attributes = DIR_EMPTY  # Marca como vazio
                entry.first_block = 0
                entry.size = 0
                return
            
    def persist_changes(self):
        """Persiste a FAT e o diretório raiz no disco."""
        with open(FILESYSTEM, "r+b") as f:
            # Atualiza a FAT
            f.seek(0)
            f.write(self.fat.to_bytes())

            # Atualiza o diretório raiz
            root_bytes = [entry.to_bytes() for entry in self.root]
            f.seek(FAT_BLOCKS * BLOCK_SIZE)
            f.write(b"".join(root_bytes))






