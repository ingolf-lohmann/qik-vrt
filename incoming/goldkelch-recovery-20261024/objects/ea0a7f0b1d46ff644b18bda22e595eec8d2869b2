-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

package effect_ack_clock_pkg is
  subtype word64 is unsigned(63 downto 0);
  subtype state_t is unsigned(2 downto 0);
  constant NACK_STATE : state_t := "000";
  constant CONTINUE_STATE : state_t := "001";
  constant DONE_STATE : state_t := "010";
  constant ISOLATE_STATE : state_t := "011";
  constant BLOCK_STATE : state_t := "100";
  -- Bit order is exactly tests/test_effect_ack_core.c:input_from_mask.
  type clock_input_t is record
    epoch, cycle : word64;
    present, verified : std_logic;
    facts : std_logic_vector(18 downto 0);
    decision : state_t;
    effect_request, sink_ready : std_logic;
    payload : std_logic_vector(31 downto 0);
  end record;
  constant EMPTY_INPUT : clock_input_t := (
    epoch => (others => '0'), cycle => (others => '0'),
    present => '0', verified => '0', facts => (others => '0'),
    decision => (others => '0'), effect_request => '0', sink_ready => '0',
    payload => (others => '0'));
  type clock_readback_t is record
    nonce, epoch, evaluated, witnessed : word64;
    fault, witness_fault, reset_seen : std_logic;
    state : state_t;
    snapshot : clock_input_t;
  end record;
  constant EMPTY_READBACK : clock_readback_t := (
    nonce => (others => '0'), epoch => (others => '0'),
    evaluated => (others => '0'), witnessed => (others => '0'),
    fault => '1', witness_fault => '1', reset_seen => '0',
    state => BLOCK_STATE, snapshot => EMPTY_INPUT);
  function binary(v : std_logic_vector) return boolean;
  function evaluate(s : clock_input_t) return state_t;
end package;

package body effect_ack_clock_pkg is
  function binary(v : std_logic_vector) return boolean is
  begin
    for i in v'range loop
      if v(i) /= '0' and v(i) /= '1' then return false; end if;
    end loop;
    return true;
  end function;
  function evaluate(s : clock_input_t) return state_t is
    variable f : std_logic_vector(18 downto 0) := s.facts;
  begin
    if not binary(f & std_logic_vector(s.decision)) or s.decision > 4 then
      return BLOCK_STATE;
    elsif f(17) = '1' or f(13) = '1' then return BLOCK_STATE;
    elsif f(1) = '0' or f(2) = '0' then return NACK_STATE;
    elsif f(18) = '1' or s.decision = 4 then return BLOCK_STATE;
    elsif s.decision = 3 then return ISOLATE_STATE;
    elsif s.decision /= 2 then return CONTINUE_STATE;
    elsif f(12 downto 0) = "1111111111111" and
          f(16 downto 14) = "111" then return DONE_STATE;
    else return CONTINUE_STATE;
    end if;
  end function;
end package body;
