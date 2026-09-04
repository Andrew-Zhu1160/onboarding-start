# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray
async def meassure_pwm_frequency (dut):
    #established base point, messure from low
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        
        if(dut.uo_out.value == 0x00):
            break
        elif(cocotb.utils.get_sim_time(units="ns") - start_time > 5000000):
            return False
    #wati for first high edge of pwm
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        
        if(dut.uo_out.value == 0xFF):
            break
        elif(cocotb.utils.get_sim_time(units="ns") - start_time > 5000000):
            return False
    first_edge_time = cocotb.utils.get_sim_time(units="ns")
    #wait for it to go low
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        if(dut.uo_out.value == 0x00):
            break
        elif(cocotb.utils.get_sim_time(units="ns") - start_time > 5000000):
            return False
    start_time = cocotb.utils.get_sim_time(units="ns")

    #wait for second high edge
    while True:
        await ClockCycles(dut.clk, 1)
        if(dut.uo_out.value == 0xFF):
            break
        elif(cocotb.utils.get_sim_time(units="ns") - start_time > 5000000):
            return False
    second_edge_time = cocotb.utils.get_sim_time(units="ns")
    #calcultae frequency should fall in 3kHz with +-1%
    frequency = 1000000000 / (second_edge_time - first_edge_time)
    if(frequency < 2974.8 or frequency >3034.9):
        return False

    #test passed
    return True

async def measure_pwm_duty(dut, duty_cycle):
    """Measure PWM duty. duty_cycle is the raw register value 0x00..0xFF."""
    if duty_cycle < 0 or duty_cycle > 0xFF:
        raise ValueError("Duty cycle must be between 0x00 and 0xFF")

    if duty_cycle == 0x00:
        # Always-off: uo_out should stay 0x00
        start_time = cocotb.utils.get_sim_time(units="ns")
        while True:
            await ClockCycles(dut.clk, 1)
            if dut.uo_out.value == 0xFF:
                return False
            elif cocotb.utils.get_sim_time(units="ns") - start_time > 5000000:
                break
        return True
    elif duty_cycle == 0xFF:
        # Always-on (HW special-cases 0xFF): uo_out should stay 0xFF
        start_time = cocotb.utils.get_sim_time(units="ns")
        while True:
            await ClockCycles(dut.clk, 1)
            if dut.uo_out.value == 0x00:
                return False
            elif cocotb.utils.get_sim_time(units="ns") - start_time > 5000000:
                break
        return True

    # Program duty register directly (0x01..0xFE)
    await send_spi_transaction(dut, 1, 0x04, duty_cycle)
    await ClockCycles(dut.clk, 100)

    # Wait until low
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        if dut.uo_out.value == 0x00:
            break
        elif cocotb.utils.get_sim_time(units="ns") - start_time > 5000000:
            return False

    # Rising edge
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        if dut.uo_out.value == 0xFF:
            break
        elif cocotb.utils.get_sim_time(units="ns") - start_time > 5000000:
            return False
    rising_edge_time = cocotb.utils.get_sim_time(units="ns")

    # Falling edge
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        if dut.uo_out.value == 0x00:
            break
        elif cocotb.utils.get_sim_time(units="ns") - start_time > 5000000:
            return False
    falling_edge_time = cocotb.utils.get_sim_time(units="ns")

    # Period = (12+1)*256 clocks at 100 ns; high for `duty_cycle` of 256 ticks
    period = 3328 * 100
    measured_fraction = (falling_edge_time - rising_edge_time) / period
    expected_fraction = duty_cycle / 256.0
    if (
        measured_fraction < expected_fraction * 0.99
        or measured_fraction > expected_fraction * 1.01
    ):
        return False
    return True
    

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

@cocotb.test()
async def test_pwm_freq(dut):
    # Write your test here
    dut._log.info("PWM Frequency test starting")

    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut,1,0x00,0xFF) #set 0-7  to 1

    ui_in_val = await send_spi_transaction(dut,1,0x02,0xFF) #enable 0-7 pin with pwm
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x33)  # test with 20% duty cycle

    await ClockCycles(dut.clk, 5)
    test_passed = await meassure_pwm_frequency(dut)
    assert test_passed, "PWM Frequency test failed"


    




    dut._log.info("PWM Frequency test completed successfully")


@cocotb.test()
async def test_pwm_duty(dut):
    # Write your test here

    dut._log.info("PWM Duty Cycle test starting")

    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    #enable pwm on tested 0-7 pins
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)
    #set 0-7 vall all 1
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xFF)
    

    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x80)  # ~50% (128/256)
    test_passed = await measure_pwm_duty(dut, 0x80)
    assert test_passed, "PWM Duty Cycle test failed"

    await ClockCycles(dut.clk, 1000)

    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCC)  # ~80% (204/256)
    test_passed = await measure_pwm_duty(dut, 0xCC)
    assert test_passed, "PWM Duty Cycle test failed"

    # 0x00: data stays all-1s so low output proves PWM gating, not empty data
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xFF)
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)
    test_passed = await measure_pwm_duty(dut, 0x00)
    assert test_passed, "PWM Duty Cycle test failed"

    # 0xFF: HW forces always-on
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xFF)
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)
    test_passed = await measure_pwm_duty(dut, 0xFF)
    assert test_passed, "PWM Duty Cycle test failed"

    dut._log.info("PWM Duty Cycle test completed successfully")

