# pycontainer https://www.figma.com/slides/j3uauzeLz7CPe19rUpNYGr/namespaces-and-cgroups?node-id=23-51&t=2lbcrJPb4xypUXJ5-1

**Использование:**
```bash
sudo python3 container.py [команда]
```

**Команды:**
- ``shell`` — Интерактивный shell (BusyBox)  
- ``run``   — Выполнить команду  
- ``memory`` — Тест ограничения памяти  
- ``help``  — Показать справку  

**Требования:**
- BusyBox: `apt install busybox-static`  
- Root-права для работы с namespaces и cgroups  

**Технологии:**
- ✓ **Namespaces**: PID, NET, MNT, UTS, IPC  
- ✓ **CGroups v2**: Memory, CPU  
- ✓ **BusyBox**: Минимальное окружение  
