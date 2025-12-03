# pycontainer
Использование:
    ``sudo python3 container.py [команда]``

Команды:
    ``shell``       Интерактивный shell (BusyBox)
    ``run``         Выполнить команду
    ``memory``      Тест ограничения памяти
    ``help ``       Показать справку

Требования:
    • BusyBox: apt install busybox-static
    • Root права для namespaces и cgroups

Технологии:
    ✓ Namespaces: PID, NET, MNT, UTS, IPC
    ✓ CGroups v2: Memory, CPU
    ✓ BusyBox: Минимальное окружение
    
