-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.effect_ack_clock_pkg.all;

entity effect_ack_clock_carrier is
  generic (COUNTER_BITS : positive range 2 to 64 := 64);
  port (clk, power_reset_n, admit, reset_request : in std_logic;
        admit_epoch : in word64;
        current_input : in clock_input_t;
        readback_request : in std_logic;
        readback_nonce : in word64;
        readback_valid : out std_logic;
        readback : out clock_readback_t;
        result_state : out state_t;
        effect_commit : out std_logic;
        effect_payload : out std_logic_vector(31 downto 0);
        sampling_epoch, sampling_cycle : out word64 := (others => '0'));
end entity;

architecture rtl of effect_ack_clock_carrier is
  signal active, failed, reset_seen, pulse, commit_pending : std_logic := '0';
  signal epoch, witnessed : word64 := (others => '0');
  signal witness_fault : std_logic;
  signal count : unsigned(COUNTER_BITS-1 downto 0) := (others => '0');
  signal state : state_t := BLOCK_STATE;
  signal snapshot : clock_input_t := EMPTY_INPUT;
  signal payload : std_logic_vector(31 downto 0) := (others => '0');
begin
  -- Read-only internal tags, never caller-controlled counters or clock enables.
  sampling_epoch <= epoch;
  sampling_cycle <= resize(count, 64);
  observer : entity work.effect_ack_coverage_witness
    generic map (COUNTER_BITS => COUNTER_BITS)
    port map (clk, power_reset_n, admit, reset_request, admit_epoch,
              pulse, resize(count, 64), witnessed, witness_fault);
  result_state <= state when failed = '0' and witness_fault = '0' else BLOCK_STATE;
  effect_commit <= commit_pending and not failed and not witness_fault and power_reset_n;
  effect_payload <= payload when effect_commit = '1' else (others => '0');

  process(clk, power_reset_n)
    variable sampled : clock_input_t;
    variable evaluated : state_t;
    variable fence_ok : boolean;
  begin
    if power_reset_n = '0' then
      active <= '0'; failed <= '0'; reset_seen <= '0'; pulse <= '0';
      epoch <= (others => '0'); count <= (others => '0'); state <= BLOCK_STATE;
      snapshot <= EMPTY_INPUT; commit_pending <= '0'; payload <= (others => '0');
      readback <= EMPTY_READBACK; readback_valid <= '0';
    elsif rising_edge(clk) then
      commit_pending <= '0'; payload <= (others => '0'); pulse <= '0';
      readback_valid <= '0';
      if reset_request /= '0' then reset_seen <= '1'; failed <= '1'; end if;
      if active = '0' then
        if admit = '1' then
          if binary(std_logic_vector(admit_epoch)) and admit_epoch /= 0 and
             failed = '0' and reset_request = '0' then
            epoch <= admit_epoch; active <= '1';
          else failed <= '1'; end if;
        end if;
      else
        -- One sampling event and exactly one gate evaluation on EVERY edge.
        -- No enable, timer, caller-created cycle counter or catch-up loop.
        sampled := current_input;
        snapshot <= sampled;
        evaluated := evaluate(sampled);
        fence_ok := binary(std_logic_vector(sampled.epoch) & std_logic_vector(sampled.cycle))
          and sampled.epoch = epoch and sampled.cycle = resize(count, 64)
          and admit = '0' and reset_request = '0'
          and count /= (count'range => '1');
        pulse <= '1';
        if count /= (count'range => '1') then count <= count + 1; end if;
        if not fence_ok then failed <= '1'; end if;
        if failed /= '0' or witness_fault /= '0' or not fence_ok or
           sampled.present /= '1' or sampled.verified /= '1' or
           not binary(sampled.effect_request & sampled.sink_ready & sampled.payload) then
          state <= BLOCK_STATE;
        else
          state <= evaluated;
          if sampled.effect_request = '1' and evaluated = DONE_STATE then
            if sampled.sink_ready = '1' then
              commit_pending <= '1'; payload <= sampled.payload;
            else state <= BLOCK_STATE; end if;
          end if;
        end if;
        -- This coherent register bank observes the last completed edge.
        -- The nonce is an external challenge; counts never come from software.
        if readback_request = '1' and binary(std_logic_vector(readback_nonce)) and
           readback_nonce /= 0 then
          readback <= (nonce => readback_nonce, epoch => epoch,
            evaluated => resize(count, 64), witnessed => witnessed,
            fault => failed, witness_fault => witness_fault,
            reset_seen => reset_seen, state => state, snapshot => snapshot);
          readback_valid <= '1';
        end if;
      end if;
    end if;
  end process;
end architecture;
