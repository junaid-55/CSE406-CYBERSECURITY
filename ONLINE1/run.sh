nasm -f elf32 shellcode.asm -o shellcode.o
ld -m elf_i386 shellcode.o -o shellcode
objcopy -O binary -j .text shellcode shellcode.bin
xxd shellcode.bin
rm shellcode shellcode.o 
