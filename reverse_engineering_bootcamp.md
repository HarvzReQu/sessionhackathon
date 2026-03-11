# Reverse Engineering - Information Security Bootcamp

## What Is Reverse Engineering?
Reverse Engineering (RE) is the process of taking a compiled program, file, or device and working backward to understand how it works, even when the original source code is not available.

In cybersecurity, reverse engineering is commonly used to:
- Analyze malware behavior
- Audit software for vulnerabilities
- Understand unknown protocols or file formats
- Recover program logic from binaries (for example in CTF challenges)
- Verify whether software actually does what it claims

## Typical Reverse Engineering Workflow
1. Static analysis: inspect code without executing it (strings, imports, disassembly, decompiler output).
2. Dynamic analysis: run and observe behavior (debugger, breakpoints, memory/register changes, API calls).
3. Behavior mapping: identify key routines such as input validation, encryption, and network activity.
4. Logic reconstruction: convert low-level instructions into understandable algorithm steps.

## Common Tools
- Ghidra, IDA Free, Binary Ninja (static analysis)
- x64dbg, WinDbg, gdb (dynamic analysis)
- strings, Detect It Easy (DIE), PE-bear (binary triage)

## Ethics and Legal Note
Only do reverse engineering in legal and authorized settings, such as:
- CTFs and training labs
- Software you own and have permission to analyze
- Environments where explicit authorization is granted

---

## Practice Problems

### Easy Problem 1: XOR Password Check
You reverse a function and find this check:

```c
unsigned char target[8] = {0x51, 0x5C, 0x5C, 0x47, 0x50, 0x52, 0x5E, 0x43};

for (int i = 0; i < 8; i++) {
    if ((input[i] ^ 0x13) != target[i]) return 0;
}
return 1;
```

Task:
- Recover the correct 8-character password.

### Easy Problem 2: Assembly Value Trace
A program prints the value of `eax` after this sequence:

```asm
mov eax, 0x2A
imul eax, eax, 3
sub eax, 0x15
xor eax, 0x5
```

Task:
- Determine the final decimal value printed.

### Hard Problem 1: Serial Key Generation
You decompiled this routine:

```c
int serial(char *name) {
    int sum = 0;
    for (int i = 0; name[i] != '\0'; i++) {
        sum += ((int)name[i]) * (i + 1);
    }
    return ((sum ^ 0x5A5A) + 1337) % 100000;
}
```

Task:
- Compute the serial for username: `ALICE`.
- Write a keygen script that computes serials for any username.

### Hard Problem 2: Patch the Check (Lab-Safe Context)
A function returns success only when:

```c
if (strcmp(user_input, "OpenSesame!") == 0) {
    puts("Access granted");
} else {
    puts("Denied");
}
```

In disassembly, the branch depends on `jne denied`.

Task:
- Locate where the conditional jump happens.
- Patch the binary so it always prints `Access granted` regardless of input.
- Explain exactly which byte(s) you changed and why.
