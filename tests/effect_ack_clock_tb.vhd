-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;
use std.env.all;
use work.effect_ack_clock_pkg.all;

entity effect_ack_clock_tb is end entity;
architecture test of effect_ack_clock_tb is
  signal clk, rst, admit, reset_req, rb_req, rb_valid, commit : std_logic := '0';
  signal admission, nonce : word64 := to_unsigned(7, 64);
  signal s : clock_input_t := EMPTY_INPUT;
  signal rb : clock_readback_t;
  signal result : state_t;
  signal payload : std_logic_vector(31 downto 0);
  signal tiny_result : state_t;
  signal tiny_commit, tiny_valid : std_logic;
  signal tiny_rb : clock_readback_t;
  signal tiny_payload : std_logic_vector(31 downto 0);
  signal wclk, wrst, wadmit, wpulse, wfault : std_logic := '0';
  signal wreported, wcount : word64 := (others => '0');
  signal board_input : std_logic_vector(185 downto 0);
  signal board_readback : std_logic_vector(447 downto 0);
  signal board_state : std_logic_vector(2 downto 0);
  signal board_commit, board_valid, unbound_commit, unbound_valid : std_logic;
  signal board_payload, unbound_payload : std_logic_vector(31 downto 0);
  signal unbound_state : std_logic_vector(2 downto 0);
begin
  board_input <= std_logic_vector(s.epoch) & std_logic_vector(s.cycle) & s.present &
    s.verified & s.facts & std_logic_vector(s.decision) & s.effect_request & s.sink_ready & s.payload;
  bound_top : entity work.effect_ack_parallel_core generic map (BOARD_BINDING_VALIDATED => true)
    port map (clk, rst, admit, reset_req, std_logic_vector(admission), board_input,
      rb_req, std_logic_vector(nonce), board_valid, board_readback, board_state, board_commit, board_payload);
  unbound_top : entity work.effect_ack_parallel_core
    port map (clk, rst, admit, reset_req, std_logic_vector(admission), board_input,
      rb_req, std_logic_vector(nonce), unbound_valid, open, unbound_state, unbound_commit, unbound_payload);
  dut : entity work.effect_ack_clock_carrier
    port map (clk, rst, admit, reset_req, admission, s,
              rb_req, nonce, rb_valid, rb, result, commit, payload);
  tiny : entity work.effect_ack_clock_carrier generic map (COUNTER_BITS => 2)
    port map (clk, rst, admit, reset_req, admission, s,
              rb_req, nonce, tiny_valid, tiny_rb, tiny_result, tiny_commit, tiny_payload);
  independent_observer : entity work.effect_ack_coverage_witness
    port map (wclk, wrst, wadmit, '0', admission, wpulse, wreported, wcount, wfault);

  process
    file vectors : text open read_mode is "vectors.txt";
    file telemetry : text open write_mode is "readback.json";
    variable row : line;
    variable mask, decision, expected, vector_count : integer := 0;
    variable cycle : natural := 0;
    variable v : clock_input_t;
    variable captured : clock_readback_t;
    procedure edge is
    begin clk <= '0'; wait for 2 ns; clk <= '1'; wait for 2 ns; end;
    procedure boot is
    begin
      clk <= '0'; rst <= '0'; admit <= '0'; reset_req <= '0'; rb_req <= '0';
      wait for 2 ns; rst <= '1'; admit <= '1'; admission <= to_unsigned(7, 64);
      edge; admit <= '0'; cycle := 0;
      assert commit = '0' report "admission is not evaluation" severity failure;
    end;
    procedure tick(value : clock_input_t; want : state_t; released : std_logic) is
    begin
      s <= value; edge;
      assert result = want report "clocked state mismatch" severity failure;
      assert commit = released report "stale/unsafe effect release" severity failure;
      assert board_state = std_logic_vector(result) and board_commit = commit and board_payload = payload
        report "board top changed carrier semantics or bit layout" severity failure;
      assert unbound_state = std_logic_vector(BLOCK_STATE) and unbound_commit = '0' and
        unbound_payload = x"00000000" and unbound_valid = '0'
        report "unbound board top released" severity failure;
      cycle := cycle + 1;
    end;
    function complete(c : natural) return clock_input_t is
      variable x : clock_input_t := EMPTY_INPUT;
    begin
      x.epoch := to_unsigned(7, 64); x.cycle := to_unsigned(c, 64);
      x.present := '1'; x.verified := '1';
      x.facts := std_logic_vector(to_unsigned(122879, 19));
      x.decision := DONE_STATE; x.effect_request := '1'; x.sink_ready := '1';
      x.payload := x"1234abcd"; return x;
    end;
    procedure wedge is
    begin wclk <= '0'; wait for 2 ns; wclk <= '1'; wait for 2 ns; end;
    procedure wboot is
    begin
      wclk <= '0'; wrst <= '0'; wadmit <= '0'; wpulse <= '0'; wreported <= (others => '0');
      wait for 2 ns; wrst <= '1'; wadmit <= '1'; wedge; wadmit <= '0';
    end;
  begin
    boot;
    while not endfile(vectors) loop
      readline(vectors, row); read(row, mask); read(row, decision); read(row, expected);
      v := complete(cycle); v.facts := std_logic_vector(to_unsigned(mask, 19));
      v.decision := to_unsigned(decision, 3);
      assert evaluate(v) = to_unsigned(expected, 3)
        report "RTL differs from independent C oracle" severity failure;
      -- Exercise the physical-edge process as well as the entire truth table.
      if vector_count mod 1024 = 0 or expected = 2 then
        if expected = 2 then tick(v, DONE_STATE, '1');
        else tick(v, to_unsigned(expected, 3), '0'); end if;
      end if;
      vector_count := vector_count + 1;
    end loop;
    assert vector_count = 2621440 severity failure;
    v := complete(cycle); tick(v, DONE_STATE, '1');
    assert payload = x"1234abcd" severity failure;
    s <= EMPTY_INPUT; wait for 1 ns;
    assert commit = '1' and payload = x"1234abcd"
      report "input change tore registered snapshot" severity failure;
    v := complete(cycle); v.present := '0'; tick(v, BLOCK_STATE, '0');
    v := complete(cycle); tick(v, DONE_STATE, '1');
    v := complete(cycle); v.verified := '0'; tick(v, BLOCK_STATE, '0');
    v := complete(cycle); v.sink_ready := '0'; tick(v, BLOCK_STATE, '0');
    v := complete(cycle); v.facts(3) := 'X'; tick(v, BLOCK_STATE, '0');
    v := complete(cycle); v.decision := "111"; tick(v, BLOCK_STATE, '0');
    v := complete(cycle); tick(v, DONE_STATE, '1');
    rb_req <= '1'; nonce <= to_unsigned(99, 64);
    v := complete(cycle); tick(v, DONE_STATE, '1');
    assert rb_valid = '1' and rb.nonce = 99 and rb.epoch = 7 severity failure;
    assert board_valid = '1' and board_readback =
      std_logic_vector(rb.nonce) & std_logic_vector(rb.epoch) & std_logic_vector(rb.evaluated) &
      std_logic_vector(rb.witnessed) & rb.fault & rb.witness_fault & rb.reset_seen &
      std_logic_vector(rb.state) & std_logic_vector(rb.snapshot.epoch) & std_logic_vector(rb.snapshot.cycle) &
      rb.snapshot.present & rb.snapshot.verified & rb.snapshot.facts & std_logic_vector(rb.snapshot.decision) &
      rb.snapshot.effect_request & rb.snapshot.sink_ready & rb.snapshot.payload
      report "board top tore readback or changed packing" severity failure;
    assert rb.evaluated = cycle-1 and rb.witnessed = rb.evaluated and
           rb.snapshot.cycle = cycle-2 and rb.fault = '0' and rb.witness_fault = '0'
      report "readback is not coherent preceding-edge coverage" severity failure;
    captured := rb; rb_req <= '0';
    write(row, string'("{""schema"":""qikvrt_effect_ack_clock_readback_v1"",""nonce"":"));
    write(row, to_integer(rb.nonce)); write(row, string'(",""epoch"":"));
    write(row, to_integer(rb.epoch)); write(row, string'(",""evaluated"":"));
    write(row, to_integer(rb.evaluated)); write(row, string'(",""witnessed"":"));
    write(row, to_integer(rb.witnessed));
    write(row, string'(",""fault"":")); write(row, to_integer(unsigned'(0 => rb.fault)));
    write(row, string'(",""witness_fault"":")); write(row, to_integer(unsigned'(0 => rb.witness_fault)));
    write(row, string'(",""reset_seen"":")); write(row, to_integer(unsigned'(0 => rb.reset_seen)));
    write(row, string'(",""state"":")); write(row, to_integer(rb.state));
    write(row, string'(",""snapshot_epoch"":")); write(row, to_integer(rb.snapshot.epoch));
    write(row, string'(",""snapshot_cycle"":"));
    write(row, to_integer(rb.snapshot.cycle)); write(row, string'("}")); writeline(telemetry, row);
    v := complete(cycle); tick(v, DONE_STATE, '1');
    assert rb_valid = '0' and rb = captured report "readback changed without request" severity failure;
    v := complete(cycle); v.cycle := v.cycle - 1; tick(v, BLOCK_STATE, '0');
    v := complete(cycle); tick(v, BLOCK_STATE, '0');
    rb_req <= '1'; v := complete(cycle); tick(v, BLOCK_STATE, '0');
    assert rb.fault = '1' and rb.evaluated = rb.witnessed severity failure;

    boot; v := complete(1); tick(v, BLOCK_STATE, '0'); -- gap
    boot; v := complete(0); v.epoch := to_unsigned(8,64); tick(v, BLOCK_STATE, '0');
    boot; v := complete(0); tick(v, DONE_STATE, '1');
    admit <= '1'; v := complete(1); tick(v, BLOCK_STATE, '0'); -- re-admission
    admit <= '0'; v := complete(2); tick(v, BLOCK_STATE, '0');
    boot; v := complete(0); tick(v, DONE_STATE, '1');
    reset_req <= '1'; v := complete(1); tick(v, BLOCK_STATE, '0');
    reset_req <= '0'; rb_req <= '1'; v := complete(2); tick(v, BLOCK_STATE, '0');
    assert rb.reset_seen = '1' and rb.fault = '1' and rb.evaluated = 2 severity failure;
    boot;
    for i in 0 to 2 loop v := complete(i); tick(v, DONE_STATE, '1'); end loop;
    v := complete(3); tick(v, DONE_STATE, '1');
    assert tiny_result = BLOCK_STATE and tiny_commit = '0' report "counter wrapped" severity failure;
    rb_req <= '1'; v := complete(4); tick(v, DONE_STATE, '1');
    assert tiny_rb.evaluated = 3 and tiny_rb.witnessed = 3 and tiny_rb.fault = '1' severity failure;
    clk <= '0'; rst <= '0'; admit <= '0'; wait for 2 ns;
    rst <= '1'; admission <= (others => '0'); admit <= '1'; edge;
    assert result = BLOCK_STATE and commit = '0' severity failure;
    admission <= to_unsigned(7,64); edge; admit <= '0'; rb_req <= '1'; edge;
    assert rb_valid = '0' and commit = '0' report "invalid admission reopened" severity failure;

    -- Fault injection at the independent observer interface. No evaluator
    -- pulse drives the witness counter. Omissions and surplus reports latch.
    admission <= to_unsigned(7,64); wboot; wedge;
    assert wcount = 1 and wfault = '0' severity failure;
    wreported <= to_unsigned(1,64); wpulse <= '0'; wedge;
    assert wfault = '1' and wcount = 2 report "missing evaluation escaped witness" severity failure;
    wboot; wpulse <= '1'; wedge;
    assert wfault = '1' report "pre-window evaluation escaped witness" severity failure;
    wboot; wedge; wpulse <= '1'; wreported <= to_unsigned(2,64); wedge;
    assert wfault = '1' report "duplicate evaluation escaped witness" severity failure;
    wboot; wedge; wpulse <= '1'; wreported <= to_unsigned(1,64); wedge;
    assert wfault = '0' and wcount = 2 severity failure;
    wreported <= to_unsigned(1,64); wedge;
    assert wfault = '1' report "replayed count escaped witness" severity failure;
    report "PASS: 2621440 independent-oracle vectors; carrier atomicity/fencing/coverage controls";
    stop; wait;
  end process;
end architecture;

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.all;
use work.effect_ack_clock_pkg.all;

entity effect_ack_serial_tb is end entity;
architecture test of effect_ack_serial_tb is
  signal clk, rst, start, shift, latch, din, drain : std_logic := '0';
  signal dout, valid, fault, unbound_out, unbound_valid, unbound_fault : std_logic;
begin
  bound_serial : entity work.effect_ack_board_top generic map (BOARD_BINDING_VALIDATED => true)
    port map (clk, rst, start, shift, latch, din, drain, dout, valid, fault);
  unbound_serial : entity work.effect_ack_board_top
    port map (clk, rst, start, shift, latch, din, drain, unbound_out, unbound_valid, unbound_fault);
  process
    variable active : boolean := false;
    variable cycle : natural := 0;
    variable response : std_logic_vector(484 downto 0);
    variable frame : std_logic_vector(316 downto 0);
    variable rb : std_logic_vector(447 downto 0);
    variable sample : clock_input_t;
    procedure edge is
    begin
      clk <= '0'; wait for 2 ns; clk <= '1'; wait for 2 ns;
      if active then cycle := cycle + 1; end if;
      assert unbound_out = '0' and unbound_valid = '0' and unbound_fault = '1'
        report "unbound serial top exposed a usable response" severity failure;
    end;
    procedure boot is
    begin
      clk <= '0'; rst <= '0'; start <= '0'; shift <= '0'; latch <= '0'; drain <= '0'; din <= '0';
      wait for 2 ns; active := false; cycle := 0; rst <= '1'; edge;
      assert valid = '0' and fault = '0' severity failure;
    end;
    function request(admission : std_logic; value : clock_input_t; readback : std_logic := '0')
      return std_logic_vector is
    begin
      return admission & '0' & std_logic_vector(to_unsigned(7, 64)) &
        std_logic_vector(value.epoch) & std_logic_vector(value.cycle) &
        value.present & value.verified & value.facts & std_logic_vector(value.decision) &
        value.effect_request & value.sink_ready & value.payload & readback &
        std_logic_vector(to_unsigned(99, 64));
    end;
    function complete(c : natural) return clock_input_t is
      variable s : clock_input_t := EMPTY_INPUT;
    begin
      s.epoch := to_unsigned(7, 64); s.cycle := to_unsigned(c, 64);
      s.present := '1'; s.verified := '1'; s.facts := std_logic_vector(to_unsigned(122879, 19));
      s.decision := DONE_STATE; s.effect_request := '1'; s.sink_ready := '1';
      s.payload := x"1234abcd"; return s;
    end;
    procedure send(value : std_logic_vector(316 downto 0)) is
    begin
      start <= '1'; edge; start <= '0'; shift <= '1';
      for i in value'range loop din <= value(i); edge; end loop;
      shift <= '0'; latch <= '1'; edge; latch <= '0';
      if value(316) = '1' then active := true; end if;
      assert valid = '0' report "response preceded registered carrier outcome" severity failure;
      edge;
      assert valid = '1' report "complete frame produced no coherent response" severity failure;
    end;
    procedure receive(variable value : out std_logic_vector(484 downto 0)) is
    begin
      drain <= '1';
      for i in value'range loop
        assert valid = '1' report "response truncated" severity failure;
        value(i) := dout; edge;
      end loop;
      drain <= '0';
      assert valid = '0' and dout = '0' report "response replayed past its length" severity failure;
    end;
  begin
    boot;
    send(request('1', EMPTY_INPUT)); receive(response);
    assert response(35 downto 33) = std_logic_vector(BLOCK_STATE) and response(32) = '0'
      report "admission released an effect" severity failure;
    -- Counters run throughout request and response transfer, never at link rate.
    sample := complete(cycle + 318);
    send(request('0', sample)); receive(response);
    assert response(35 downto 33) = std_logic_vector(DONE_STATE) and response(32) = '1' and
      response(31 downto 0) = x"1234abcd"
      report "fresh frame lost the carrier's one-cycle result" severity failure;
    sample := complete(cycle + 318); sample.present := '0'; sample.verified := '0';
    send(request('0', sample, '1')); receive(response);
    rb := response(483 downto 36);
    assert response(484) = '1' and unsigned(rb(447 downto 384)) = 99 and
      unsigned(rb(383 downto 320)) = 7 and unsigned(rb(319 downto 256)) = sample.cycle and
      rb(319 downto 256) = rb(255 downto 192) and rb(191 downto 189) = "000" and
      rb(188 downto 186) = std_logic_vector(BLOCK_STATE) and
      unsigned(rb(121 downto 58)) = sample.cycle - 1
      report "serial transfer paused coverage or reused old verified facts" severity failure;
    assert response(32) = '0' and response(31 downto 0) = x"00000000" severity failure;
    -- Replaying the formerly valid frame cannot relabel the hardware count.
    send(request('0', complete(804))); receive(response);
    assert response(35 downto 33) = std_logic_vector(BLOCK_STATE) and response(32) = '0'
      report "stale sample released twice" severity failure;
    sample := complete(cycle + 318);
    send(request('0', sample)); receive(response);
    assert response(32) = '0' report "cycle fault was not sticky" severity failure;

    boot;
    start <= '1'; edge; start <= '0'; shift <= '1'; din <= '1'; edge;
    shift <= '0'; latch <= '1'; edge; latch <= '0'; edge;
    assert fault = '1' and valid = '0' report "truncated frame accepted" severity failure;
    boot;
    start <= '1'; edge; start <= '0'; shift <= '1'; din <= '0';
    for i in 1 to 317 loop edge; end loop;
    edge; shift <= '0'; edge;
    assert fault = '1' and valid = '0' report "overlength frame accepted" severity failure;
    boot;
    start <= '1'; edge; start <= '0'; shift <= '1'; din <= 'X'; edge; shift <= '0'; edge;
    assert fault = '1' and valid = '0' report "nonbinary input accepted" severity failure;
    boot;
    latch <= 'X'; edge; latch <= '0'; edge;
    assert fault = '1' and valid = '0' report "nonbinary control accepted" severity failure;
    boot;
    start <= '1'; edge; start <= '0'; shift <= '1'; din <= '0';
    for i in 1 to 317 loop edge; end loop;
    latch <= '1'; edge; shift <= '0'; latch <= '0'; edge;
    assert fault = '1' and valid = '0' report "simultaneous shift/latch accepted" severity failure;
    boot;
    -- Restart discards a partial frame without publishing it.
    start <= '1'; edge; start <= '0'; shift <= '1'; din <= '1'; edge; shift <= '0';
    send(request('1', EMPTY_INPUT));
    assert fault = '0' report "safe frame abort latched a fault" severity failure;
    frame := request('0', EMPTY_INPUT);
    start <= '1'; edge; start <= '0'; shift <= '1';
    for i in frame'range loop din <= frame(i); edge; end loop;
    shift <= '0'; latch <= '1'; edge; latch <= '0'; edge;
    assert fault = '1' report "unread response was overwritten" severity failure;
    receive(response);
    assert response(32) = '0' report "busy-frame rejection replayed an effect" severity failure;
    report "PASS: serial framing, one-shot freshness, continuous coverage, replay, malformed and unbound controls";
    stop; wait;
  end process;
end architecture;
