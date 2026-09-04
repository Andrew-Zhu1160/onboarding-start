<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

An SPI slave on `ui_in` (SCLK, COPI, nCS) accepts write-only transactions: 1-bit R/W, 7-bit address, 8-bit data. Addresses 0–4 configure output levels, per-pin PWM enables, and duty cycle. Reads and out-of-range addresses are ignored. A PWM block (~3 kHz from the system clock) gates selected bits of the 16-bit output (`uo_out` / `uio_out`).

## How to test

Drive SPI writes from a host or cocotb: set output data (addr 0/1), enable PWM on pins (addr 2/3), set duty (addr 4). Check steady levels with PWM off, then measure frequency (~3 kHz) and duty on enabled outputs. Invalid addresses and read attempts should leave registers unchanged.

## External hardware

None required. Optional LEDs or a scope/logic analyzer on the output pins to observe PWM.
