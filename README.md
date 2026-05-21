# UCT-Micromouse

![uctmm](https://github.com/user-attachments/assets/bd4c2c84-7c43-4995-aef7-3a01c304f71e)

Once you've built your micro-mouse, test it using Jesse Arendse's code 'MicroMouseTemplate' from the Github page [https://github.com/JesseJabezArendse/MicroMouseTemplate](https://github.com/JesseJabezArendse/MicroMouseTemplate).

The main code repository is at [https://github.com/EEEUCT/Micromouse](https://github.com/EEEUCT/Micromouse).

You will need the code from both these repositories to develop the required software and program your micro-mouse.

## Note on Cloning
This repository uses a Git Submodule for the core microcontroller kernel (Jesse Arendse's 'MicroMouseTemplate' from the Github page [https://github.com/JesseJabezArendse/MicroMouseTemplate](https://github.com/JesseJabezArendse/MicroMouseTemplate)). To clone this repository with all required files, run:
```bash
git clone --recursive https://github.com/nicollsf/UCT-Micromouse.git
```
If you already cloned it without the `--recursive` flag, you can initialize the submodule by running:
```bash
git submodule update --init --recursive
```

[![Open in MATLAB Online](https://www.mathworks.com/images/responsive/global/open-in-matlab-online.svg)](https://matlab.mathworks.com/open/github/v1?repo=nicollsf/UCT-Micromouse)
