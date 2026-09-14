# ONLINE 1 — Stack Buffer Overflow Exploitation

Kept as a record of the CSE405 Online 1 lab. The task was to exploit a
classic stack-based buffer overflow in a 32-bit C program: overflow a
fixed-size buffer, overwrite the saved return address, and redirect
execution into injected shellcode that spawns a shell (`/bin/sh`).

## What the lab had

`target.c` reads a file called `badfile` into an oversized stack buffer and
passes it to `process()`, which does an unbounded `strcpy` into
`char buffer[100 + STUDENT_ID]`. That unchecked copy is the vulnerability.
The problem statement is in `C1.pdf`.

## What I did

- Analysed the binary under GDB to find the overflow offset and a usable
  return address on the stack, disabling ASLR / shell startup noise for
  stable addresses. Working notes are in `cmd-gdb.txt`.
- Wrote shellcode (`shellcode.asm`) and assembled it with `run.sh`
  (`nasm` → `ld` → `objcopy` to raw bytes).
- Built the exploit payload in `exploit.py`: padding up to the
  return address (offset 118), the overwritten return address, then the
  `/bin/sh` shellcode. Running it writes the crafted `badfile`.

## Files

| File | Purpose |
|------|---------|
| `target.c` | Vulnerable program (the target) |
| `exploit.py` | Builds the malicious `badfile` payload |
| `shellcode.asm` | Hand-written shellcode source |
| `run.sh` | Assembles the shellcode to raw bytes |
| `cmd-gdb.txt` | GDB / analysis notes |
| `C1.pdf` | Original problem statement |

## Removed (regenerable — not kept in the repo)

- `a.out` — compiled binary; rebuild from `target.c` (32-bit, protections
  disabled as the exercise requires).
- `badfile` — the crafted payload; regenerate with `python3 exploit.py`.
