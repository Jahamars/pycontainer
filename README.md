## Simple container using Linux namespaces and cgroups v2 in python.

### Usage
sudo python3 container.py [command]

text

### Commands
- `shell` - Interactive BusyBox shell
- `run` - Execute command
- `memory` - Memory limit test
- `help` - Show help

### Requirements
- BusyBox: `apt install busybox-static`
- Root privileges

### Features
- Namespaces: PID, NET, MNT, UTS, IPC
- CGroups v2: Memory, CPU
- BusyBox environment
