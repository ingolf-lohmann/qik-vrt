"use strict";

function normalized(token) {
  return token
    .normalize("NFKD")
    .toLocaleLowerCase("de-DE")
    .replace(/[^\p{L}\p{N}]+/gu, "");
}

function mergeWithWordOverlap(existing, addition, maxOverlapWords = 24) {
  const left = existing.trim().split(/\s+/u).filter(Boolean);
  const right = addition.trim().split(/\s+/u).filter(Boolean);

  if (left.length === 0) return right.join(" ");
  if (right.length === 0) return left.join(" ");

  const limit = Math.min(maxOverlapWords, left.length, right.length);
  let overlap = 0;
  for (let width = limit; width >= 1; width -= 1) {
    const leftTail = left.slice(-width).map(normalized);
    const rightHead = right.slice(0, width).map(normalized);
    if (leftTail.every((word, index) => word && word === rightHead[index])) {
      overlap = width;
      break;
    }
  }

  return [...left, ...right.slice(overlap)].join(" ");
}

module.exports = { mergeWithWordOverlap, normalized };
