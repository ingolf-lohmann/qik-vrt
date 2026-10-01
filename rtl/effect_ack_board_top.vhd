-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.effect_ack_clock_pkg.all;

-- Flat parallel integration boundary, not a board/part/pin declaration.
-- All buses must be synchronous to clk. No implicit CDC or authentication.
-- The external reviewed build adapter may enable the static binding only
-- after validating the exact board profile and generated build manifest.
entity effect_ack_board_top is
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
        effect_payload : out std_logic_vector(31 downto 0));
end entity;

architecture rtl of effect_ack_board_top is
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
      effect_commit => commit, effect_payload => payload);
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
