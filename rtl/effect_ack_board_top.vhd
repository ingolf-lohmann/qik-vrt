-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.effect_ack_clock_pkg.all;

-- Internal parallel integration boundary; this entity is NOT a package top.
-- All buses must be synchronous to clk. No implicit CDC or authentication.
-- The external reviewed build adapter may enable the static binding only
-- after validating the exact board profile and generated build manifest.
entity effect_ack_parallel_core is
  generic (BOARD_BINDING_VALIDATED : boolean := false);
  port (clk, power_reset_n, admit, reset_request : in std_logic;
        admit_epoch : in std_logic_vector(63 downto 0);
        current_input_bits : in std_logic_vector(185 downto 0);
        readback_request : in std_logic;
        readback_nonce : in std_logic_vector(63 downto 0);
        readback_valid : out std_logic;
        readback_bits : out std_logic_vector(447 downto 0);
        result_state : out std_logic_vector(2 downto 0);
        effect_commit : out std_logic;
        effect_payload : out std_logic_vector(31 downto 0);
        sampling_epoch, sampling_cycle : out word64 := (others => '0'));
end entity;

architecture rtl of effect_ack_parallel_core is
  signal sample : clock_input_t;
  signal telemetry : clock_readback_t;
  signal admitted, valid, commit : std_logic;
  signal state : state_t;
  signal payload : std_logic_vector(31 downto 0);
begin
  -- Layout is fixed in the processor-clock machine contract. High bits first.
  sample <= (epoch => unsigned(current_input_bits(185 downto 122)),
    cycle => unsigned(current_input_bits(121 downto 58)),
    present => current_input_bits(57), verified => current_input_bits(56),
    facts => current_input_bits(55 downto 37),
    decision => unsigned(current_input_bits(36 downto 34)),
    effect_request => current_input_bits(33), sink_ready => current_input_bits(32),
    payload => current_input_bits(31 downto 0));
  admitted <= admit when BOARD_BINDING_VALIDATED else '0';
  carrier : entity work.effect_ack_clock_carrier
    port map (clk => clk, power_reset_n => power_reset_n, admit => admitted,
      reset_request => reset_request, admit_epoch => unsigned(admit_epoch),
      current_input => sample, readback_request => readback_request,
      readback_nonce => unsigned(readback_nonce), readback_valid => valid,
      readback => telemetry, result_state => state,
      effect_commit => commit, effect_payload => payload,
      sampling_epoch => sampling_epoch, sampling_cycle => sampling_cycle);
  effect_commit <= commit when BOARD_BINDING_VALIDATED else '0';
  effect_payload <= payload when BOARD_BINDING_VALIDATED else (others => '0');
  result_state <= std_logic_vector(state) when BOARD_BINDING_VALIDATED else std_logic_vector(BLOCK_STATE);
  readback_valid <= valid when BOARD_BINDING_VALIDATED else '0';
  readback_bits <= std_logic_vector(telemetry.nonce) & std_logic_vector(telemetry.epoch) &
    std_logic_vector(telemetry.evaluated) & std_logic_vector(telemetry.witnessed) &
    telemetry.fault & telemetry.witness_fault & telemetry.reset_seen &
    std_logic_vector(telemetry.state) & std_logic_vector(telemetry.snapshot.epoch) &
    std_logic_vector(telemetry.snapshot.cycle) & telemetry.snapshot.present &
    telemetry.snapshot.verified & telemetry.snapshot.facts &
    std_logic_vector(telemetry.snapshot.decision) & telemetry.snapshot.effect_request &
    telemetry.snapshot.sink_ready & telemetry.snapshot.payload;
end architecture;

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.effect_ack_clock_pkg.all;

-- Ten synchronous pins. No independent serial clock, divider, implicit CDC,
-- pin assignment or physical authentication. The wide buses stay on chip.
-- A 317-bit request is shifted MSB first, then latched on a separate edge.
-- A complete request supplies ONE fresh sample; the continuously running
-- carrier sees absent/unverified inputs on every intervening clock edge.
entity effect_ack_board_top is
  generic (BOARD_BINDING_VALIDATED : boolean := false);
  port (clk, power_reset_n, frame_start, frame_shift, frame_latch,
        serial_in, response_shift : in std_logic;
        serial_out, response_valid, transport_fault : out std_logic);
end entity;

architecture rtl of effect_ack_board_top is
  signal rx : std_logic_vector(316 downto 0) := (others => '0');
  signal tx : std_logic_vector(484 downto 0) := (others => '0');
  signal rx_count : natural range 0 to 317 := 0;
  signal tx_count : natural range 0 to 485 := 0;
  signal collecting, failed, pending, accept_frame, malformed : std_logic := '0';
  signal input_bits : std_logic_vector(185 downto 0);
  signal next_epoch, next_cycle : word64;
  signal admitted, reset_req, rb_req, rb_valid, commit : std_logic;
  signal rb_bits : std_logic_vector(447 downto 0);
  signal state : std_logic_vector(2 downto 0);
  signal payload : std_logic_vector(31 downto 0);
begin
  malformed <= '1' when not binary(frame_start & frame_shift & frame_latch & response_shift)
    or (frame_shift = '1' and (collecting /= '1' or rx_count = 317 or
        frame_start /= '0' or (serial_in /= '0' and serial_in /= '1')))
    or (frame_latch = '1' and (collecting /= '1' or rx_count /= 317 or
        frame_start /= '0' or frame_shift /= '0' or tx_count /= 0 or pending /= '0'))
    else '0';
  accept_frame <= '1' when BOARD_BINDING_VALIDATED and power_reset_n = '1' and
    failed = '0' and malformed = '0' and frame_latch = '1' else '0';
  admitted <= rx(316) when accept_frame = '1' else '0';
  reset_req <= '1' when failed = '1' or malformed = '1' else
    rx(315) when accept_frame = '1' else '0';
  rb_req <= rx(64) when accept_frame = '1' else '0';
  input_bits <= rx(250 downto 65) when accept_frame = '1' else
    std_logic_vector(next_epoch) & std_logic_vector(next_cycle) & std_logic_vector(to_unsigned(0, 58));
  core : entity work.effect_ack_parallel_core
    generic map (BOARD_BINDING_VALIDATED => BOARD_BINDING_VALIDATED)
    port map (clk, power_reset_n, admitted, reset_req, rx(314 downto 251), input_bits,
      rb_req, rx(63 downto 0), rb_valid, rb_bits, state, commit, payload, next_epoch, next_cycle);
  response_valid <= '1' when BOARD_BINDING_VALIDATED and power_reset_n = '1' and tx_count /= 0 else '0';
  serial_out <= tx(484) when response_valid = '1' else '0';
  transport_fault <= failed when BOARD_BINDING_VALIDATED else '1';

  process(clk, power_reset_n)
  begin
    if power_reset_n = '0' then
      rx <= (others => '0'); tx <= (others => '0'); rx_count <= 0; tx_count <= 0;
      collecting <= '0'; failed <= '0'; pending <= '0';
    elsif rising_edge(clk) then
      pending <= accept_frame;
      if malformed = '1' then failed <= '1'; collecting <= '0'; rx_count <= 0;
      elsif frame_start = '1' then
        rx <= (others => '0'); rx_count <= 0; collecting <= '1';
      elsif frame_shift = '1' then
        rx <= rx(315 downto 0) & serial_in; rx_count <= rx_count + 1;
      elsif frame_latch = '1' then
        collecting <= '0'; rx_count <= 0;
      end if;
      -- Capture the complete outcome of the preceding accepted edge, including
      -- its one-cycle commit/payload. Transmission never reruns that effect.
      if pending = '1' then
        tx <= rb_valid & rb_bits & state & commit & payload; tx_count <= 485;
      elsif response_shift = '1' and tx_count /= 0 then
        tx <= tx(483 downto 0) & '0'; tx_count <= tx_count - 1;
      end if;
    end if;
  end process;
end architecture;
