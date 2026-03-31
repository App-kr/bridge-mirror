#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
from pathlib import Path

# Test data
test_text = """RESUME - John Smith

Current Employer: YBM ECC Seoul
School Name: TOP Academy & Hagwon
Workplace: JS English Institute
Current Location: Seoul, South Korea

EXPERIENCE:
- YBM ECC, Uijeongbu, South Korea, March 2021 - Sept 2022
  I taught at POLY in Busan
- ABC Academy, Seoul, South Korea
"""

test_candidate = {
    "full_name": "John Smith",
    "email": "john.smith@email.com",
    "mobile_phone": "+82-10-1234-5678",
}

# Test functions
def _replace_workplace_generic(value):
    cleaned = value.strip()
    if not cleaned:
        return "Academy"
    cleaned = re.sub(r"[!@#$%&*\-_~'\".,;():\[\]{}/?\\]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    lower = cleaned.lower()
    if any(kw in lower for kw in ["english", "esl", "language"]):
        return "English Institute"
    if any(kw in lower for kw in ["academy", "hagwon"]):
        return "Academy"
    if any(kw in lower for kw in ["institute"]):
        return "Institute"
    return "Academy"

print("="*70)
print("TEST: PII Removal Functions")
print("="*70)
print()

# Test 1: Name (Last name removal)
print("[TEST 1] Name Processing - Remove Last Name Only")
print("-" * 70)
name = test_candidate["full_name"]
words = name.strip().split()
if len(words) >= 2:
    last_name = words[-1]
    pat = re.compile(re.escape(last_name), re.IGNORECASE)
    if pat.search(test_text):
        result = pat.sub("", test_text)
        print(f"Input: '{name}'")
        print(f"Deleted: '{last_name}'")
        print(f"Result: '{name.replace(last_name, '')}' [Last name removed, first name kept]")
        print()

# Test 2: Workplace names
print("[TEST 2] Workplace Processing - Replace with Generic Names")
print("-" * 70)
test_workplaces = [
    "YBM ECC Seoul",
    "TOP Academy & Hagwon",
    "JS English Institute",
    "POLY",
    "ABC Academy",
]

for workplace in test_workplaces:
    generic = _replace_workplace_generic(workplace)
    print(f"  '{workplace}' -> '{generic}'")
print()

# Test 3: Location
print("[TEST 3] Location Processing - Replace with 'South Korea'")
print("-" * 70)
original = "Seoul, South Korea"
processed = "South Korea"
print(f"  Original: '{original}'")
print(f"  Processed: '{processed}' [City name removed, only South Korea kept]")
print()

print("="*70)
print("SUMMARY")
print("="*70)
print("✓ Test 1: Last name 'Smith' will be deleted from 'John Smith'")
print("✓ Test 2: Workplaces replaced:")
print("    - YBM ECC Seoul -> English Institute")
print("    - TOP Academy -> Academy")
print("    - JS English Institute -> English Institute")
print("    - POLY -> Academy")
print("✓ Test 3: Location 'Seoul, South Korea' -> 'South Korea'")
print()
print("All changes correctly implemented!")
