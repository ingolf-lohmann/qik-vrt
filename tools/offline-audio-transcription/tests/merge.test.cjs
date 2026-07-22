"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { mergeWithWordOverlap } = require("../src/merge.cjs");

test("removes an exact overlapping word sequence", () => {
  assert.equal(
    mergeWithWordOverlap("Die Ordnung bestimmt die Bedeutung", "die Bedeutung früherer Spuren neu"),
    "Die Ordnung bestimmt die Bedeutung früherer Spuren neu",
  );
});

test("compares overlap case-insensitively and ignores punctuation", () => {
  assert.equal(
    mergeWithWordOverlap("Das ist der Beweisstand.", "der Beweisstand ist prüfbar"),
    "Das ist der Beweisstand. ist prüfbar",
  );
});

test("keeps non-overlapping text", () => {
  assert.equal(mergeWithWordOverlap("Erster Satz.", "Zweiter Satz."), "Erster Satz. Zweiter Satz.");
});
