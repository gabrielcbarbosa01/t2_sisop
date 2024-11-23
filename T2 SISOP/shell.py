from operations import FileSystemOperations

class FileSystemShell:
    """Shell para interação com o sistema de arquivos."""
    def __init__(self):
        self.fs_ops = FileSystemOperations()

    def run(self):
        print("Bem-vindo ao shell do sistema de arquivos!")
        while True:
            command = input("fs> ").strip()
            if command == "exit":
                print("Encerrando o sistema...")
                break

            elif command == "init":
                self.fs_ops.initialize_filesystem()
            
            elif command.startswith("ls"):
                parts = command.split(" ", 1)
                if len(parts) == 1:  # Sem argumentos, listar o diretório raiz
                    self.fs_ops.list_directory("/")
                else:  # Com caminho, listar o diretório especificado
                    self.fs_ops.list_directory(parts[1])


            elif command == "load":
                try:
                    self.fs_ops.load_filesystem()
                except FileNotFoundError as e:
                    print(e)    

            elif command.startswith("mkdir"):
                try:
                    _, path = command.split(" ", 1) 
                    self.fs_ops.mkdir(path)
                except ValueError:
                    print("Uso: mkdir /caminho/diretorio")

            elif command == "fatinfo":
                self.fs_ops.fat_info()
            
            elif command.startswith("create"):
                try:
                    _, path = command.split(" ", 1)
                    self.fs_ops.create(path)
                except ValueError:
                    print("Uso: create /caminho/arquivo")

            elif command.startswith("unlink"):
                try:
                    _, path = command.split(" ", 1)
                    self.fs_ops.unlink(path)
                except ValueError:
                    print("Uso: unlink /caminho/arquivo_ou_diretorio")
                except FileNotFoundError as e:
                    print(e)
                except Exception as e:
                    print(f"Erro ao remover: {e}")

            else:
                print("Comando não reconhecido.")
