#!/usr/bin/env python3
"""
Минималистичная контейнеризация на Python
Использует: Namespaces + Cgroups + BusyBox
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ContainerConfig:
    """Конфигурация контейнера"""
    name: str
    memory_mb: int = 50
    cpu_percent: int = 25
    command: str = "/bin/sh"


class CGroupManager:
    """Управление cgroups v2"""
    
    def __init__(self, name: str):
        self.name = name
        self.path = Path(f"/sys/fs/cgroup/{name}")
    
    def create(self, memory_mb: int, cpu_percent: int):
        """Создать cgroup с лимитами ресурсов"""
        self.path.mkdir(exist_ok=True)
        
        (self.path / "memory.max").write_text(str(memory_mb * 1024 * 1024))
        (self.path / "cpu.max").write_text(f"{cpu_percent * 1000} 100000")
        
        print(f"✓ CGroup: {memory_mb}MB RAM, {cpu_percent}% CPU")
    
    def add_process(self, pid: int):
        """Добавить процесс в cgroup"""
        (self.path / "cgroup.procs").write_text(str(pid))
    
    def cleanup(self):
        """Удалить cgroup"""
        try:
            self.path.rmdir()
        except OSError:
            pass


class RootFSManager:
    """Управление корневой файловой системой"""
    
    def __init__(self, name: str):
        self.name = name
        self.rootfs = None
    
    def create(self) -> Path:
        """Создать минимальную rootfs с busybox"""
        self.rootfs = Path(tempfile.mkdtemp(prefix=f"container_{self.name}_"))
        
        # Базовые директории
        for d in ['bin', 'lib', 'lib64', 'proc', 'tmp', 'dev', 'etc']:
            (self.rootfs / d).mkdir(parents=True, exist_ok=True)
        
        # Установка busybox
        if not self._setup_busybox():
            raise RuntimeError("BusyBox недоступен. Установите: apt install busybox-static")
        
        # Копирование bash (опционально)
        self._copy_bash()
        
        print(f"✓ RootFS: {self.rootfs}")
        return self.rootfs
    
    def _setup_busybox(self) -> bool:
        """Установить busybox и создать симлинки"""
        busybox_paths = ['/usr/bin/busybox', '/bin/busybox', '/usr/bin/busybox-static']
        busybox_src = None
        
        for path in busybox_paths:
            if os.path.exists(path):
                busybox_src = path
                break
        
        if not busybox_src:
            return False
        
        # Копируем busybox
        busybox_dst = self.rootfs / 'bin/busybox'
        shutil.copy2(busybox_src, busybox_dst)
        busybox_dst.chmod(0o755)
        
        # Создаём симлинки для основных команд
        commands = ['sh', 'ls', 'cat', 'echo', 'ps', 'sleep', 'mkdir', 'rm', 'cp', 'mv']
        for cmd in commands:
            link = self.rootfs / 'bin' / cmd
            if not link.exists():
                link.symlink_to('busybox')
        
        return True
    
    def _copy_bash(self):
        """Копировать bash с зависимостями"""
        bash_path = '/usr/bin/bash'
        if not os.path.exists(bash_path):
            return
        
        # Копируем bash
        bash_dst = self.rootfs / 'bin/bash'
        shutil.copy2(bash_path, bash_dst)
        bash_dst.chmod(0o755)
        
        # Копируем библиотеки
        try:
            result = subprocess.run(
                ['ldd', bash_path],
                capture_output=True,
                text=True,
                check=False
            )
            
            for line in result.stdout.splitlines():
                lib_path = None
                
                if '=>' in line:
                    # Формат: libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x...)
                    parts = line.split('=>')[1].strip().split()
                    if parts and os.path.exists(parts[0]):
                        lib_path = parts[0]
                elif line.strip().startswith('/'):
                    # Формат: /lib64/ld-linux-x86-64.so.2 (0x...)
                    lib_path = line.strip().split()[0]
                
                if lib_path and os.path.exists(lib_path):
                    dst = self.rootfs / lib_path.lstrip('/')
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if not dst.exists():
                        shutil.copy2(lib_path, dst)
        
        except subprocess.CalledProcessError:
            pass
    
    def cleanup(self):
        """Удалить rootfs"""
        if self.rootfs and self.rootfs.exists():
            shutil.rmtree(self.rootfs)


class Container:
    """Контейнер с изоляцией через namespaces и ограничениями через cgroups"""
    
    def __init__(self, config: ContainerConfig):
        self.config = config
        self.cgroup = CGroupManager(config.name)
        self.rootfs_mgr = RootFSManager(config.name)
    
    def run(self) -> int:
        """Запустить контейнер"""
        print(f"\n{'='*60}")
        print(f"Контейнер: {self.config.name}")
        print('='*60)
        
        try:
            # Подготовка
            self.cgroup.create(self.config.memory_mb, self.config.cpu_percent)
            rootfs = self.rootfs_mgr.create()
            
            print(f"🚀 Команда: {self.config.command}\n")
            
            # Добавляем текущий процесс в cgroup
            self.cgroup.add_process(os.getpid())
            
            # Запуск с полной изоляцией
            cmd = [
                'unshare',
                '--fork',
                '--pid',
                '--net',
                '--mount',
                '--uts',
                '--ipc',
                '--mount-proc',
                'chroot',
                str(rootfs),
                self.config.command
            ]
            
            result = subprocess.run(cmd)
            return result.returncode
        
        except KeyboardInterrupt:
            print("\n⚠ Остановлено")
            return 130
        except Exception as e:
            print(f"\n✗ Ошибка: {e}")
            return 1
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Очистка ресурсов"""
        print(f"\n{'='*60}")
        print("Очистка")
        print('='*60)
        self.cgroup.cleanup()
        self.rootfs_mgr.cleanup()
        print("✓ Готово\n")


def demo_interactive():
    """Интерактивный shell"""
    config = ContainerConfig(
        name="demo",
        memory_mb=50,
        cpu_percent=25,
        command="/bin/sh"
    )
    Container(config).run()


def demo_command():
    """Выполнение команды"""
    config = ContainerConfig(
        name="cmd_demo",
        memory_mb=30,
        cpu_percent=20,
        command='/bin/sh -c "echo Hello from container! && ls -la / && sleep 1"'
    )
    Container(config).run()


def demo_memory_limit():
    """Тест лимита памяти"""
    print("\n" + "="*60)
    print("ТЕСТ: Ограничение памяти (OOM Killer)")
    print("="*60)
    print("Попытка выделить 100MB при лимите 20MB\n")
    
    memory_hog = '''
data = []
for i in range(100):
    data.append(" " * (1024 * 1024))
    print(f"Allocated {i+1}MB")
'''
    
    # Проверяем наличие python в rootfs
    if not shutil.which('python3'):
        print("⚠ Python3 не найден, используем busybox для теста")
        config = ContainerConfig(
            name="mem_test",
            memory_mb=20,
            cpu_percent=50,
            command='/bin/sh -c "echo Testing memory limit... && sleep 1"'
        )
    else:
        config = ContainerConfig(
            name="mem_test",
            memory_mb=20,
            cpu_percent=50,
            command=f'/usr/bin/python3 -c \'{memory_hog}\''
        )
    
    exit_code = Container(config).run()
    
    if exit_code == 137:
        print("✓ OOM Killer сработал - лимит работает!")


def print_help():
    """Справка"""
    print("""
Использование:
    sudo python3 container.py [команда]

Команды:
    shell       Интерактивный shell (BusyBox)
    run         Выполнить команду
    memory      Тест ограничения памяти
    help        Показать справку

Примеры:
    sudo python3 container.py shell
    sudo python3 container.py run
    sudo python3 container.py memory

Требования:
    • BusyBox: apt install busybox-static
    • Root права для namespaces и cgroups

Технологии:
    ✓ Namespaces: PID, NET, MNT, UTS, IPC
    ✓ CGroups v2: Memory, CPU
    ✓ BusyBox: Минимальное окружение
    """)


def main():
    if os.geteuid() != 0:
        print("✗ Требуются root права")
        print("Запустите: sudo python3 container.py")
        sys.exit(1)
    
    commands = {
        "shell": demo_interactive,
        "run": demo_command,
        "memory": demo_memory_limit,
        "help": print_help,
    }
    
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    
    if cmd in commands:
        commands[cmd]()
    else:
        print(f"✗ Неизвестная команда: {cmd}\n")
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
