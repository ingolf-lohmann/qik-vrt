-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.effect_ack_clock_pkg.all;

-- Separate sequential observer: counts clk edges, never calls evaluate and
-- never increments from the evaluator's pulse. Same clock, not an independent
-- oscillator: whole-domain clock loss needs an external board witness.
entity effect_ack_coverage_witness is
  generic (COUNTER_BITS : positive range 2 to 64 := 64);
  port (clk, power_reset_n, admit, reset_request : in std_logic;
        admit_epoch : in word64;
        evaluation_pulse : in std_logic;
        reported_count : in word64;
        edge_count : out word64;
        fault : out std_logic);
end entity;

architecture rtl of effect_ack_coverage_witness is
  signal active, failed : std_logic := '0';
  signal count : unsigned(COUNTER_BITS-1 downto 0) := (others => '0');
begin
  edge_count <= resize(count, 64);
  fault <= failed;
  process(clk, power_reset_n)
  begin
    if power_reset_n = '0' then
      active <= '0'; failed <= '0'; count <= (others => '0');
    elsif rising_edge(clk) then
      if active = '0' then
        if admit = '1' then
          if binary(std_logic_vector(admit_epoch)) and admit_epoch /= 0 and
             failed = '0' and reset_request = '0' then active <= '1';
          else failed <= '1'; end if;
        end if;
      else
        if admit /= '0' or reset_request /= '0' or
           not binary(std_logic_vector(reported_count)) or
           reported_count /= resize(count, 64) or
           (count = 0 and evaluation_pulse /= '0') or
           (count /= 0 and evaluation_pulse /= '1') then failed <= '1'; end if;
        if count = (count'range => '1') then failed <= '1';
        else count <= count + 1; end if;
      end if;
    end if;
  end process;
end architecture;
