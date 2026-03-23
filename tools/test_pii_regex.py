import re
import sys
sys.path.insert(0, 'Q:/Claudework/bridge base/tools')
from doc_processor import (
    RE_EMAIL, RE_PHONE, RE_URL, RE_LINKEDIN, RE_KAKAO, RE_SNS,
    RE_KR_ADDRESS, RE_PASSPORT, PII_LINE_LABELS, remove_pii_from_text
)

print("=== FALSE POSITIVE TESTS ===")
print("(These should NOT be removed)")

# Phone regex vs dates/years
test_dates = [
    "2018-2022",
    "March 2020",
    "2023.03.15",
    "Grade 8-10",
    "4 years",
    "(10-11)",
    "Level (14) B.Ed.",
    "13 December 2018",
]
for t in test_dates:
    result = RE_PHONE.sub(lambda m: '[PHONE_HIT]' if len(re.sub(r'\D','',m.group()))>=7 else m.group(), t)
    if result != t:
        print(f"  PHONE FALSE POS: '{t}' -> '{result}'")

# Passport regex vs normal text
test_passport = [
    "B.ED",
    "Bachelor of Education",
    "REQV Level 14",
    "BS12345678",  # Real passport - SHOULD match
    "M12345678",   # Real passport - SHOULD match
]
for t in test_passport:
    result = RE_PASSPORT.sub('[PASSPORT_HIT]', t)
    if result != t:
        print(f"  PASSPORT: '{t}' -> '{result}'")

# PII_LINE_LABELS vs normal text
test_lines = [
    "Timeline of events",
    "Cell biology course",
    "Hotel management",
    "Hostel coordinator",
    "Contact Information",
    "Deadline: March 2025",
    "Telephone: +82-10-1234-5678",
    "Line manager: Mr. Kim",
    "Online teaching experience",
    "LinkedIn: linkedin.com/in/john",
    "Email: john@gmail.com",
    "Mobile: 010-1234-5678",
]
for line in test_lines:
    stripped = line.strip().lower()
    matched = False
    for label in PII_LINE_LABELS:
        if stripped.startswith(label) and (
            len(stripped) == len(label)
            or stripped[len(label):].lstrip().startswith(':')
            or stripped[len(label):].lstrip().startswith(' ')
        ):
            matched = True
            print(f"  LINE_LABEL: '{line}' matched by '{label}'")
            break

print()
print("=== FULL TEXT TEST ===")
test_text = """John Michael Smith
ESL Teacher Resume

Education:
Bachelor of Education (B.ED) - 4 years
Cape Peninsula University of Technology
Completion date: 13 December 2018
REQV: Level (14) B.Ed.

Employment History (South Korea)
Company: Francis Parker Collegiate (Kyowon Wiz)
Position: ESL teacher (Kindergarten and Elementary)
Province: Gyeonggi-do
Start Date: 15th April 2023

Contact Information
Email: john.smith@gmail.com
Phone: +82-10-1234-5678
Line ID: john_line_id
Cell: 010-9876-5432
LinkedIn: linkedin.com/in/johnsmith

Address: Seoul, Gangnam-gu, South Korea
Current Location: Bundang, Seongnam-si, Gyeonggi-do
"""

result = remove_pii_from_text(test_text, "John Michael Smith")
print(result)
print()
print("=== ISSUES FOUND ===")
if "13 December 2018" not in result:
    print("  BUG: Date '13 December 2018' was deleted!")
if "B.ED" not in result and "B.Ed" not in result:
    print("  BUG: 'B.ED'/'B.Ed' was deleted by passport regex!")
if "(14)" not in result:
    print("  BUG: Level number '(14)' was deleted!")
if "4 years" not in result:
    print("  BUG: '4 years' was deleted!")
if "15th April 2023" not in result:
    print("  BUG: Date '15th April 2023' was deleted!")
if "Cape Peninsula" not in result:
    print("  BUG: University name was deleted!")
if "Timeline" in test_text and "Timeline" not in result:
    print("  BUG: 'Timeline' was incorrectly deleted!")
