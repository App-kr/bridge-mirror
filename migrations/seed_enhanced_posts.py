"""
Enhanced community posts — reference: Dave's ESL Cafe, Waygook, EPIK, Reddit r/teachinginkorea
실제 ESL 교사들이 가장 많이 검색하고 필요로 하는 실질 정보 중심
"""

import sqlite3, os, sys
from pathlib import Path

DB_PATH = os.getenv("BRIDGE_DB_PATH", str(Path(__file__).resolve().parent.parent / "master.db"))

POSTS = [
    # ══════════════════════════════════════════════════════════════════
    # TIPS — 실사용자 선호 콘텐츠 (Dave's ESL Cafe / Waygook 레퍼런스)
    # ══════════════════════════════════════════════════════════════════
    {
        "board": "tips",
        "title": "Resume & CV Guide — How to Stand Out to Korean Schools",
        "pinned": 0,
        "body": """# Resume & CV Guide for Teaching in Korea

Your resume is the first thing a school director sees. In Korea, **presentation matters as much as content**. Here's how to make yours stand out.

## Format
- **1 page max** — Korean directors are busy and prefer concise resumes
- Use a clean, professional template (no fancy colors or graphics)
- **Include a professional photo** in the top-right corner (passport-style, smiling)
- PDF format only — Word docs can break formatting on Korean computers

## Must-Have Sections
1. **Personal Information**: Full name, nationality, date of birth, current location
2. **Education**: University name, degree, major, graduation date
3. **Teaching Experience**: Most recent first, include school name + city + dates + age group taught
4. **Certifications**: TEFL/TESOL/CELTA with hours and institution
5. **Skills**: Classroom management, curriculum development, technology skills

## What Korean Schools Actually Look For
- **Photo quality** — Dress professionally, smile naturally
- **Stability** — Completed contracts (no mid-contract runners)
- **Age group experience** — Match what the school teaches
- **Korean experience** — Even 6 months counts significantly

## Common Mistakes
- Listing irrelevant work experience (barista, retail) — only include if you have no teaching experience
- Generic objective statements — be specific about Korea
- Typos or grammar errors — have someone proofread
- No photo — this is considered incomplete in Korea

## Pro Tip
Tailor your resume for each application. If applying to a kindergarten, highlight experience with young learners. For an academy, emphasize after-school experience."""
    },
    {
        "board": "tips",
        "title": "What to Pack for Korea — The Essential Packing List",
        "pinned": 0,
        "body": """# What to Pack for Teaching in Korea

After 10+ years of placing teachers, here's what you actually need (and what you can skip).

## Bring From Home
- **Documents**: Originals of degree, apostilled CBC, TEFL cert (keep copies separate)
- **Deodorant**: Hard to find Western brands in Korea — bring a year's supply
- **Medications**: Prescription meds + doctor's note in English; allergy meds, pain relievers
- **Shoes above size 280mm (US 11+)**: Large sizes are rare and expensive
- **Clothes above XL**: Finding larger Western sizes is difficult
- **Comfort items**: Favorite snacks, family photos, a good book for the plane

## Skip These — Buy in Korea
- **Electronics**: Korea has cheaper phones, adapters, cables
- **Bedding**: Your apartment will have basics; buy quality locally
- **Winter coat**: Korean paddings (long puffer coats) are affordable and made for Korean winters
- **Toiletries**: Korean skincare and hygiene products are excellent and cheap
- **Kitchen items**: Your apartment should be furnished; Daiso has everything else for 1,000 won

## Clothing Tips
- **Work clothes**: Business casual — collared shirts, slacks, modest dresses
- **No visible tattoos**: Some schools are strict — bring clothes that cover them
- **Indoor shoes**: Many schools require separate indoor footwear
- **Layers**: Korean buildings are well-heated but outdoor temps vary dramatically

## Tech Essentials
- **Unlocked phone**: Get a Korean SIM at the airport
- **Laptop**: For lesson planning and video calls home
- **USB drive**: Korean schools still use them frequently
- **Power adapter**: Korea uses Type C/F (European-style round, 220V)

## Pro Tips
- Pack light — you'll want to shop in Korea (fashion is amazing and affordable)
- Ship a box via sea mail (takes 4-6 weeks but cheap for heavy items)
- Download Papago and Naver Map before you arrive"""
    },
    {
        "board": "tips",
        "title": "First Week Survival Guide — Your First 7 Days in Korea",
        "pinned": 0,
        "body": """# Your First Week in Korea — Survival Guide

The first week can be overwhelming. Here's a day-by-day guide to get settled fast.

## Day 1-2: Immediate Essentials
1. **Get a Korean phone number** — Visit any SKT, KT, or LG U+ store with your passport
2. **Get cash** — ATMs at convenience stores (GS25, CU, 7-Eleven) work with foreign cards
3. **Download essential apps**:
   - **Naver Map** (NOT Google Maps — it doesn't work properly in Korea)
   - **Papago** (translation)
   - **KakaoTalk** (everyone uses it, including your school)
   - **Coupang** (Korean Amazon)
   - **배달의민족 (Baedal Minjok)** or **Coupang Eats** (food delivery)

## Day 3-4: Admin Tasks
4. **Open a bank account** — Go with a Korean-speaking colleague; bring passport + ARC (or come back after ARC)
5. **Register at immigration** — Your school should help with ARC application
6. **Health check** — Required for your ARC; your school will arrange this
7. **Learn your neighborhood** — Find the nearest convenience store, subway station, and laundromat

## Day 5-7: Get Comfortable
8. **Stock your apartment** — Visit Daiso (cheap household goods) and a local mart
9. **Try the school cafeteria** — Most schools provide lunch
10. **Explore your neighborhood** — Walk around, find coffee shops, restaurants
11. **Set up internet banking** — Your bank can help (bring your phone)

## Cultural Quick Tips
- **Bow slightly** when greeting older people or your boss
- **Remove shoes** when entering homes and some restaurants
- **Don't tip** — It's not expected and can even be rude
- **Use two hands** when giving/receiving from elders
- **Trash separation** is serious — learn the system from day one

## Emergency Numbers
- Police: 112
- Fire/Ambulance: 119
- Immigration Helpline: 1345 (multilingual)
- BRIDGE Support: Check your welcome email for our direct line"""
    },
    {
        "board": "tips",
        "title": "Classroom Management — Tips from Experienced Teachers",
        "pinned": 0,
        "body": """# Classroom Management in Korean Schools

Managing a classroom in Korea is different from Western teaching. Here's what actually works.

## For Kindergarten (3-7 years)
- **Routine is everything** — Same greeting song, same warmup, same structure daily
- **Use visual timers** — "When this timer runs out, we move to the next activity"
- **Reward systems work** — Sticker charts, stamp cards, small prizes
- **Energy management** — Alternate between active games and calm activities
- **Korean co-teacher** — Work closely with them; they handle discipline and parent communication

## For Elementary (8-13 years)
- **Be fun but firm** — These kids test boundaries constantly
- **Games with purpose** — Every game should reinforce the lesson target
- **Team competitions** — Korean kids are naturally competitive; use it
- **Phone/tablet policy** — Establish rules from day one
- **Positive reinforcement** — Public praise goes further than public correction

## For Middle/High School
- **Respect their time** — Teens are exhausted from their schedules
- **Make it relevant** — Pop culture, music, trending topics
- **Less textbook, more conversation** — They get enough textbook at school
- **Don't take attitude personally** — It's usually exhaustion, not disrespect
- **Group work** — Shy students participate more in small groups

## Universal Tips
- **Learn student names fast** — Use name tags for the first month
- **Volume control** — Use countdown methods, clap patterns, or whisper technique
- **Never yell** — It damages your relationship and doesn't work long-term
- **Prepare 20% more material** — Better to have too much than too little
- **Start strict, ease up later** — Much easier than the reverse

## Cultural Notes
- Korean students may be quiet — it's cultural, not disinterest
- Physical punishment is **illegal** — never touch a student
- Some students will call you "Teacher" not your name — this is respectful
- End-of-class bowing is normal — bow back"""
    },
    {
        "board": "tips",
        "title": "Korean Language Basics — 20 Phrases Every Teacher Needs",
        "pinned": 0,
        "body": """# Korean for ESL Teachers — 20 Essential Phrases

You don't need to be fluent, but these phrases will make your daily life much easier.

## At School
1. **안녕하세요** (annyeonghaseyo) — Hello (formal)
2. **감사합니다** (gamsahamnida) — Thank you (formal)
3. **죄송합니다** (joesonghamnida) — I'm sorry (formal)
4. **화장실 어디예요?** (hwajangsil eodiyeyo?) — Where is the bathroom?
5. **네 / 아니요** (ne / aniyo) — Yes / No
6. **잠깐만요** (jamkkanmanyo) — Just a moment
7. **이해 못 해요** (ihae mot haeyo) — I don't understand

## Daily Life
8. **이거 얼마예요?** (igeo eolmayeyo?) — How much is this?
9. **이거 주세요** (igeo juseyo) — This one please
10. **영수증 주세요** (yeongsujeung juseyo) — Receipt please
11. **카드 돼요?** (kadeu dwaeyo?) — Can I pay by card?
12. **매워요?** (maewoyo?) — Is it spicy?
13. **안 맵게 해주세요** (an maepge haejuseyo) — Not spicy please
14. **포장이요** (pojangniyo) — To go / takeout

## Transportation
15. **여기 세워주세요** (yeogi sewojuseyo) — Stop here please (taxi)
16. **얼마나 걸려요?** (eolmana geollyeoyo?) — How long does it take?

## Social
17. **괜찮아요** (gwaenchanayo) — It's okay / I'm fine
18. **맛있어요** (masisseoyo) — It's delicious
19. **건배!** (geonbae!) — Cheers!
20. **다음에 또 봐요** (daeume tto bwayo) — See you next time

## Learning Tips
- **Hangul takes 2-3 hours to learn** — The Korean alphabet is logical and phonetic
- Use the **Talk To Me In Korean** (TTMIK) app — it's free and excellent
- Practice with your Korean co-teacher — they'll appreciate the effort
- KakaoTalk has a built-in translator for messages
- Many Korean words come from English: 커피 (keopi = coffee), 버스 (beoseu = bus)

## Why It Matters
Even basic Korean effort earns massive respect from your colleagues and students. Schools love teachers who try to integrate, and your daily life becomes 10x easier."""
    },
    {
        "board": "tips",
        "title": "Saving Money in Korea — Budget Tips for Teachers",
        "pinned": 0,
        "body": """# How to Save Money Teaching in Korea

One of the biggest perks of teaching in Korea is the saving potential. Here's how to maximize it.

## Your Monthly Budget (Typical)
| Category | Budget (KRW) | Notes |
|----------|-------------|-------|
| Rent | 0 (school-provided) | Or 400-600K if housing allowance |
| Food | 300-500K | Cooking at home saves a lot |
| Transport | 50-100K | T-money card, subway + bus |
| Phone | 30-50K | Prepaid plans are cheapest |
| Utilities | 50-150K | Electric, gas, water, internet |
| Social/Fun | 200-400K | Dining out, drinks, activities |
| **Total** | **630K-1.2M** | |

## With a 2.5M salary, you can save 1.0-1.5M per month

## Top Saving Tips
1. **Cook at home** — Korean grocery stores are affordable; rice, eggs, and vegetables are cheap
2. **School lunch** — Many schools provide free lunch; that's 22 meals/month saved
3. **Public transport** — Subway + bus is cheap and efficient; skip taxis
4. **Coupang Rocket Delivery** — Free next-day delivery; compare prices before buying in stores
5. **Avoid Itaewon/Gangnam prices** — Local Korean restaurants are 5,000-8,000 won per meal vs 15,000+ in expat areas
6. **Korean haircuts** — 10,000-15,000 won vs 40,000+ at "foreigner" salons

## Banking & Transfers
- **Wise (TransferWise)** — Best exchange rates for sending money home
- **Toss** — Korean fintech app; great for splitting bills and cashback
- **National Pension refund** — You get your pension contributions back when you leave Korea (most nationalities)

## Hidden Income
- **Severance pay** — After 1 year, you get 1 month's salary as severance
- **Flight reimbursement** — Many contracts include round-trip airfare
- **Housing deposit return** — Any deposit you put down comes back
- **Tax refund** — File before you leave; many teachers overpay taxes

## What to Avoid
- **Expensive coffee shops daily** — Make coffee at home (4,500 won/day = 135,000 won/month)
- **Convenience store meals** — Cooking is cheaper and healthier
- **ATM fees** — Use your Korean bank's ATMs, not foreign ones
- **Impulse shopping** — Korean online shopping is addictive; set a monthly limit"""
    },
    {
        "board": "tips",
        "title": "Weekend Trips — Best Destinations Near Your City",
        "pinned": 0,
        "body": """# Weekend Trip Guide for Teachers in Korea

Korea is small enough that you can visit almost anywhere in a weekend. Here are the best trips by season.

## Spring (March - May)
- **Jinhae Cherry Blossom Festival** — The most famous cherry blossom spot in Korea (Busan area)
- **Gyeongju** — Ancient capital with temples, tombs, and cherry blossoms
- **Boseong Green Tea Fields** — Stunning terraced tea plantations

## Summer (June - August)
- **Busan Beaches** — Haeundae and Gwangalli are iconic
- **Jeju Island** — Korea's Hawaii; fly for as low as 30,000 won on budget airlines
- **Sokcho & Seoraksan** — Mountain hiking and fresh seafood on the east coast
- **Boryeong Mud Festival** — The biggest foreigner-friendly festival

## Fall (September - November)
- **Seoraksan National Park** — Best autumn foliage in Korea
- **Naejangsan** — Stunning maple tunnel
- **Andong Hahoe Village** — Traditional Korean village + mask dance festival
- **DMZ Tour** — Book in advance; fascinating history

## Winter (December - February)
- **Ski Resorts** — Pyeongchang, Yongpyong, High1 Resort (lift + rental from 60,000 won)
- **Busan Christmas Market** — Less crowded than Seoul in winter
- **Jeonju Hanok Village** — Traditional village with amazing street food
- **Ice Fishing Festivals** — Hwacheon or Pyeongchang

## Budget Travel Tips
- **KTX** — Korea's bullet train; Seoul to Busan in 2.5 hours
- **Express Bus** — Cheaper than KTX; comfortable and frequent
- **Airbnb/Guesthouse** — 30-50,000 won/night; way cheaper than hotels
- **T-money card** — Works on all buses and subways nationwide
- **Temple Stay** — Spend a night at a Buddhist temple for 50-80,000 won (includes meals)

## Day Trips from Seoul
- **Nami Island** — 1.5 hours, famous from K-dramas
- **DMZ** — Guided tours only, book 3+ days ahead
- **Suwon Hwaseong Fortress** — UNESCO World Heritage, 30 min by subway
- **Incheon Chinatown** — Great food, 1 hour by subway"""
    },
    {
        "board": "tips",
        "title": "Video Interview Tips — Ace Your School Interview",
        "pinned": 0,
        "body": """# How to Ace Your Korean School Interview

Most interviews are conducted via Google Meet or Zoom. Here's what to expect and how to prepare.

## What They Ask (90% of interviews)
1. **Tell me about yourself** — Keep it 2 minutes; teaching background + why Korea
2. **Why do you want to teach in Korea?** — Be genuine; mention culture, career growth
3. **What age group do you prefer?** — Match the school's needs if possible
4. **Describe your teaching style** — Use specific examples
5. **How would you handle a difficult student?** — Show patience and strategy
6. **What would you do if you couldn't speak Korean and needed help?** — Show resourcefulness
7. **Do you have any questions for us?** — Always ask at least 2-3 questions

## Technical Setup
- **Camera**: Eye level, well-lit room (face a window or use a desk lamp)
- **Background**: Clean and neutral (no messy beds or posters)
- **Audio**: Use headphones with a mic; test audio before the call
- **Internet**: Wired connection if possible; close other apps/tabs
- **Dress**: Business casual from head to toe (you might need to stand up)

## What Schools Look For
- **Enthusiasm** — Smile, be energetic, show genuine interest
- **Reliability** — Will this person complete their contract?
- **Flexibility** — Can they adapt to Korean school culture?
- **Professionalism** — Are they punctual, prepared, and polite?
- **Clear speech** — Can students understand them easily?

## Questions to Ask the School
- What curriculum or textbooks do you use?
- How many students per class?
- What does a typical day look like?
- Is there a Korean co-teacher in the classroom?
- What support do you offer for new teachers?
- What is the housing like?

## Red Flags to Watch For
- They won't discuss salary or benefits clearly
- No contract before you fly
- "We'll figure out housing when you arrive"
- Extremely vague job description
- Pressure to decide immediately

## After the Interview
- Send a brief thank-you email within 24 hours
- If you don't hear back in 3-5 days, follow up once
- BRIDGE will coordinate between you and the school"""
    },
    {
        "board": "tips",
        "title": "Contract Red Flags — What to Check Before Signing",
        "pinned": 0,
        "body": """# Understanding Your Korean Teaching Contract

Before signing anything, make sure you understand every clause. Here's what to look for.

## Must-Have Clauses
- **Salary**: Exact monthly amount in KRW (before tax)
- **Working hours**: Daily start/end time, total weekly teaching hours
- **Housing**: Free single housing OR housing allowance amount
- **Vacation**: Minimum 10 paid days + national holidays
- **Severance**: 1 month salary after 12 months (required by Korean law)
- **Flight**: At least one-way; most offer round-trip
- **Health insurance**: 50/50 split employer-employee (required by law)
- **National pension**: 50/50 split (required by law)
- **Contract period**: Start date and end date (usually 12 months)

## Red Flags
- **"Salary negotiable"** — Get the exact number in writing
- **"Up to 30 teaching hours"** — This usually means exactly 30; negotiate if too high
- **No mention of overtime pay** — Any work beyond contract hours must be compensated
- **"Housing deposit from your salary"** — School should cover the deposit
- **"6-month probation"** — Unusual for ESL; negotiate to remove or reduce
- **Penalty clauses** — Check what happens if you leave early; excessive penalties are a red flag
- **"You will be responsible for..."** — Vague duties can mean anything

## Korean Labor Law Protections
- Maximum 40 hours/week (52 with overtime)
- Overtime must be compensated at 150% rate
- Severance pay is **legally required** after 1 year
- You cannot be fired without cause
- 4 major insurances are mandatory (health, pension, employment, accident)

## What BRIDGE Recommends
1. **Read every line** before signing
2. Get the contract in **both English and Korean** — the Korean version is legally binding
3. Ask about the **Letter of Release** policy in case of disputes
4. **Never pay a recruiter fee** — legitimate recruiters are paid by the school
5. Send your contract to BRIDGE for a **free review** before signing"""
    },
    {
        "board": "tips",
        "title": "Cultural Do's and Don'ts — Korean Workplace Culture",
        "pinned": 0,
        "body": """# Korean Workplace Culture for Foreign Teachers

Understanding Korean workplace norms will make your life much smoother.

## Do's
- **Arrive early** — Being "on time" means 5-10 minutes early in Korea
- **Greet everyone** — Say hello to every colleague when you arrive
- **Join dinners** — Staff dinners (회식 hoesik) are important for bonding
- **Accept gifts graciously** — Korean colleagues often share food and small gifts
- **Dress conservatively** — Even on casual days, avoid shorts, tank tops, or revealing clothing
- **Show interest in Korean culture** — Ask about holidays, try Korean food, learn basic phrases

## Don'ts
- **Don't leave before your boss** — Wait until senior staff leave (or ask permission)
- **Don't refuse soju** — At least accept the first glass; it's okay to sip slowly
- **Don't call in sick casually** — Koreans have very different sick day culture
- **Don't argue publicly** — Save disagreements for private conversations
- **Don't eat at your desk during class hours** — Use break time
- **Don't be too casual with the director** — Maintain respect hierarchy

## Understanding 눈치 (Nunchi)
Nunchi is the Korean concept of "reading the room." It means:
- Noticing when others are busy and not interrupting
- Picking up on subtle hints rather than waiting for direct instructions
- Adapting your behavior to the situation
- Understanding that "maybe" often means "no"

## Hierarchy in Korean Schools
- **Director (원장님)**: Ultimate authority — always show respect
- **Head Teacher**: Your direct supervisor — go to them with issues
- **Korean Co-teacher**: Your daily partner — build a strong relationship
- **Other Staff**: Janitors, bus drivers, kitchen staff — be friendly to everyone

## Holiday Awareness
- **Seollal (Lunar New Year)** — 3-day holiday, usually February
- **Chuseok** — Korean Thanksgiving, 3-day holiday, usually September/October
- **Children's Day (May 5)** — Schools are closed
- **Teacher's Day (May 15)** — You'll receive gifts and appreciation

## When Things Go Wrong
- Talk to your Korean co-teacher first
- If unresolved, speak with your recruiter (BRIDGE)
- Document everything in writing (email/KakaoTalk)
- Korean labor board (고용노동부) handles serious disputes: call 1350"""
    },
    {
        "board": "tips",
        "title": "Health & Fitness — Staying Healthy in Korea",
        "pinned": 0,
        "body": """# Staying Healthy as a Teacher in Korea

## Healthcare System
Korea has excellent, affordable healthcare. With your national health insurance:
- **Doctor visit**: 5,000-15,000 won copay
- **Specialist**: 15,000-30,000 won
- **Hospital stay**: Very affordable compared to Western countries
- **Dental**: Covered for basics; cosmetic is out-of-pocket but still cheap
- **Pharmacy**: Right next to most clinics; show your prescription

## Finding a Doctor
- **Use Naver Map** to search "병원" (hospital) or specific specialties
- Many clinics near universities have English-speaking doctors
- **International clinics** in Seoul: Severance Hospital, Samsung Medical Center
- Walk-ins are common — no appointment needed for most clinics

## Mental Health
Teaching abroad can be isolating. Take care of your mental health:
- **Seoul Global Center**: Free counseling in English (02-2075-4180)
- **Crisis helpline**: 1393 (Korean), 1588-9191 (multilingual)
- Many schools offer EAP (Employee Assistance Programs)
- Join expat groups on Facebook or Reddit for community support

## Staying Fit
- **Gym memberships**: 50-80,000 won/month (much cheaper than Western countries)
- **Korean hiking culture**: Mountains are everywhere; well-maintained trails
- **Han River parks**: Free running/cycling paths (bike rental 1,000 won/hour)
- **Public pools**: 5,000-8,000 won per visit
- **Yoga/Pilates studios**: Popular and affordable

## Food & Nutrition
- Korean food is generally healthy — lots of vegetables, fermented foods, lean protein
- **Watch the sodium** — Korean food can be very salty
- **Meal prep** — Buy in bulk at Costco or Homeplus
- **Western food cravings**: Coupang sells imported foods; Itaewon/Haebangchon have Western restaurants

## Common Health Issues for Teachers
- **Voice strain** — Tea with honey, throat lozenges, learn to project without straining
- **Back pain** — Many teachers sit on low Korean-style furniture
- **Weight gain** — School lunches are large; portions in Korea can be big
- **Seasonal allergies** — Yellow dust (황사) in spring; wear a mask on bad days
- **Air quality** — Check the AirVisual app daily; wear KF94 masks when needed"""
    },
    {
        "board": "tips",
        "title": "TEFL vs TESOL vs CELTA — Which Certificate Do You Need?",
        "pinned": 0,
        "body": """# Teaching Certifications Explained

Confused about which certification to get? Here's a straightforward comparison.

## Quick Answer
For most Korean academy/school positions: **Any 120+ hour TEFL/TESOL is fine.**

## Comparison

### TEFL (Teaching English as a Foreign Language)
- **Hours**: 120-150 hours typical
- **Cost**: $200-500 online
- **Time**: 1-3 months self-paced
- **Best for**: Academy (hagwon) jobs, most Korean positions
- **Where**: International TEFL Academy, i-to-i, Bridge (unrelated to us!)

### TESOL (Teaching English to Speakers of Other Languages)
- **Hours**: 120-150 hours typical
- **Cost**: $200-600
- **Time**: Similar to TEFL
- **Best for**: Same as TEFL — the names are essentially interchangeable
- **Note**: Some university programs offer TESOL master's degrees

### CELTA (Certificate in English Language Teaching to Adults)
- **Hours**: 120 hours intensive
- **Cost**: $1,500-2,500
- **Time**: 4-5 weeks full-time or part-time over several months
- **Best for**: International schools, university positions, career teachers
- **Where**: British Council centers, authorized training centers
- **Note**: Includes observed teaching practice — much more rigorous

### Teaching License
- Full government teaching credential from your home country
- **Best for**: International schools, EPIK, public schools
- **Highest salary bracket** in most positions

## What Korean Schools Actually Require
- **Academies (Hagwon)**: TEFL/TESOL preferred but not always required
- **Public Schools (EPIK/GEPIK)**: TEFL preferred; gives application points
- **International Schools**: CELTA/teaching license often required
- **Universities**: Master's degree + CELTA or equivalent usually required

## Our Recommendation
1. If you're new to teaching: Get a **120-hour online TEFL** before applying
2. If you want a career in ESL: Invest in **CELTA**
3. If you already have teaching experience: Your resume matters more than certificates
4. **Avoid** certificates under 100 hours — many schools won't accept them"""
    },

    # ══════════════════════════════════════════════════════════════════
    # KOREA — 추가 생활 정보
    # ══════════════════════════════════════════════════════════════════
    {
        "board": "korea",
        "title": "Transportation Guide — Getting Around Korea Like a Local",
        "pinned": 0,
        "body": """# Transportation in Korea — Complete Guide

Korea's public transport is world-class. Here's everything you need to know.

## T-money Card
- **Buy at any convenience store** (2,500 won for the card)
- **Recharge**: Convenience stores or subway station machines
- Works on: All buses, subways, and taxis nationwide
- **Transfer discount**: Free transfer between bus and subway within 30 minutes

## Subway
- Seoul Metro covers the entire capital region
- **Operating hours**: ~5:30 AM to ~12:00 AM
- Color-coded lines, English announcements, clear signage
- **Base fare**: 1,350 won (increases with distance)
- **Naver Map** gives real-time subway directions and estimated times

## Bus
- **Blue (간선)**: Long-distance trunk routes
- **Green (지선)**: Local neighborhood routes
- **Red (광역)**: Express between cities/suburbs
- **Yellow (순환)**: Circular routes within districts
- Tap T-money when boarding AND exiting

## KTX (Bullet Train)
- Seoul to Busan: 2h 30min (from 59,800 won)
- Seoul to Gwangju: 1h 50min
- Book on **SRT** or **Korail** app (English available)
- **Tip**: Book early for discounts; standing tickets are cheaper

## Taxi
- **Base fare**: ~4,800 won (varies by city)
- **Kakao T app**: Korea's Uber; shows fare estimate, English available
- **Late night** (12AM-4AM): 20-40% surcharge
- **International taxis**: Available at airports, English-speaking drivers

## Intercity Bus
- Cheaper than KTX, covers more destinations
- Book on **Express Bus** app or pay at the terminal
- Most buses have USB charging and reclining seats

## Driving
- International Driving Permit valid for 1 year
- **Not recommended** — parking is expensive, traffic is heavy, public transport is better
- If needed: Korean license conversion is straightforward with your IDP"""
    },
    {
        "board": "korea",
        "title": "Phone & Internet Setup — Your Digital Life in Korea",
        "pinned": 0,
        "body": """# Setting Up Your Phone & Internet in Korea

Korea has the fastest internet in the world. Here's how to get connected.

## Mobile Phone Plans
### Prepaid SIM (first option)
- Buy at airport arrival hall (KT, SKT, LG U+)
- **30-day tourist SIM**: ~35,000-55,000 won (unlimited data)
- Only need passport

### Monthly Plan (after ARC)
- Visit any carrier store with passport + ARC
- **Budget plans**: 25,000-35,000 won/month (enough data)
- **Unlimited plans**: 45,000-65,000 won/month
- **MVNOs** (cheaper): KT M Mobile, SK 7mobile — same network, lower prices

## Essential Apps
| App | Purpose |
|-----|---------|
| KakaoTalk | Messaging (everyone uses it) |
| Naver Map | Navigation (Google Maps doesn't work well) |
| Papago | Translation (better than Google for Korean) |
| Coupang | Online shopping (next-day delivery) |
| Toss | Banking, payments, splitting bills |
| 배달의민족 | Food delivery |
| Kakao T | Taxi, parking, bike rental |
| AirVisual | Air quality check |
| Subway Korea | Subway navigation |

## Home Internet
- Usually **included in your apartment** or set up by school
- If you need to set up: KT, SK, LG U+ — 30,000-40,000 won/month
- Speed: 100Mbps to 1Gbps (yes, really)
- Installation: Same-day or next-day in most areas

## WiFi
- **Free WiFi everywhere**: Subway, buses, cafes, convenience stores
- Quality varies — have your mobile data as backup
- **Public WiFi names**: iptime, KT_GiGA, U+zone, olleh WiFi

## Banking Apps
- Your Korean bank will have an app with English support
- **Toss**: Modern fintech app, great for daily use
- **Kakao Pay**: Linked to KakaoTalk, widely accepted
- International transfers: Use **Wise** for best rates"""
    },

    # ══════════════════════════════════════════════════════════════════
    # SUPPORT — 추가 교사 지원 자료
    # ══════════════════════════════════════════════════════════════════
    {
        "board": "support",
        "title": "Apartment Guide — Understanding Korean Housing",
        "pinned": 0,
        "body": """# Korean Housing for Teachers — What to Expect

## School-Provided Housing
Most schools provide a **furnished studio apartment (원룸)** near the school.

### What's Usually Included
- Bed or sleeping pad, desk, chair
- Refrigerator, washing machine, stove/gas range
- Air conditioning / heating
- Basic kitchenware (pots, rice cooker)
- Internet connection

### What You'll Need to Buy
- Bedding (blankets, pillows) — or school may provide
- Towels, hangers, cleaning supplies
- Kitchen utensils, dishes, cups
- Shower supplies

## Housing Allowance Option
Some schools offer 300,000-600,000 KRW/month instead of housing.
- **Pros**: Choose your own place, live where you want
- **Cons**: Finding housing alone is difficult; deposits are high
- **Key money (전세) system**: Large deposit (millions of won) = low/no monthly rent
- **Monthly rent (월세)**: Smaller deposit + monthly rent

## Tips for Your Apartment
- **Heating**: Most Korean apartments use ondol (heated floors) — very warm and cozy
- **Laundry**: Usually no dryer — use a drying rack or laundromat
- **Trash**: Strict separation required. Buy designated trash bags from convenience stores
- **Noise**: Korean apartments have thin walls — be considerate, especially at night
- **Mold**: Common in summer — use the bathroom fan and dehumidifier

## If There Are Issues
1. Tell your school/director first — they should handle maintenance
2. Document with photos before and after
3. Keep a record of all communications
4. Contact BRIDGE if your school isn't responsive"""
    },
    {
        "board": "support",
        "title": "Tax Guide for Foreign Teachers in Korea",
        "pinned": 0,
        "body": """# Tax Guide for ESL Teachers in Korea

## Tax Rate Options
Foreign teachers can choose between:

### Option 1: Flat Rate (단일세율)
- **19% flat tax** on gross salary (no deductions)
- Simple and straightforward
- Usually better for higher salaries or those without many deductions

### Option 2: Progressive Rate (누진세율)
- Same as Korean nationals
- 6-45% based on income brackets
- Can claim deductions (pension, insurance, medical expenses)
- Usually better for typical ESL salaries (2.0-3.0M range)

### Tax Treaty Exemption
Some countries have tax treaties with Korea:
- **USA**: First 2 years exempt from Korean income tax (if you meet requirements)
- **UK**: Similar 2-year exemption
- **Canada**: Partial exemptions available
- Check your country's specific treaty terms

## Year-End Tax Settlement (연말정산)
- Happens every January-February
- Your school's accountant handles the paperwork
- You may get a **refund** or owe additional tax
- Keep receipts for medical expenses, donations, transportation

## When You Leave Korea
- File final tax return before departure
- Apply for **National Pension refund** (lump sum payout)
- Pension refund processing: 1-3 months after departure
- Some countries have pension transfer agreements (check yours)

## Monthly Deductions from Your Salary
| Item | Your Share | School's Share |
|------|-----------|---------------|
| Income Tax | ~3-8% | — |
| National Pension | 4.5% | 4.5% |
| Health Insurance | ~3.5% | ~3.5% |
| Employment Insurance | ~0.9% | ~1.6% |

## Pro Tips
- **Ask your school** which tax option is better for you
- **Keep all receipts** — medical, education, transportation
- **National Pension refund** is a nice lump sum when you leave
- Consult the **National Tax Service** helpline: 126 (English available)"""
    },

    # ══════════════════════════════════════════════════════════════════
    # SUPPORT_KR — 추가 학원 지원 자료
    # ══════════════════════════════════════════════════════════════════
    {
        "board": "support_kr",
        "title": "4대보험 안내 — 원어민 강사 보험 가입 필수사항",
        "pinned": 0,
        "body": """# 원어민 강사 4대보험 가입 안내

외국인 근로자(E-2 비자)도 **4대보험 가입이 법적 의무**입니다.

## 4대보험 개요

### 1. 국민건강보험
- 사업주 50% + 근로자 50% 부담
- 급여의 약 7.09% (2026년 기준)
- 가입 즉시 의료 혜택 이용 가능
- **외국인도 가입 의무** (체류기간 6개월 이상)

### 2. 국민연금
- 사업주 50% + 근로자 50% 부담
- 급여의 9% (각 4.5%)
- **출국 시 일시금 반환** 가능 (상호주의 국가)
- 미국, 캐나다, 호주 등은 반환 가능; 일부 국가는 제외

### 3. 고용보험
- 사업주 약 1.6% + 근로자 약 0.9%
- 실업급여 수급 가능 (조건 충족 시)
- **E-2 비자 근로자도 가입 대상**

### 4. 산재보험
- **전액 사업주 부담**
- 근무 중 사고/질병 보상
- 출퇴근 사고도 포함

## 자주 묻는 질문

**Q: 원어민이 4대보험 가입을 거부하면?**
A: 법적 의무이므로 거부 불가. 미가입 시 사업주에게 과태료 부과.

**Q: 시간제(파트타임) 강사도 가입해야 하나요?**
A: 주 15시간 이상, 1개월 이상 근무 시 가입 의무.

**Q: 국민연금 환급 절차는?**
A: 출국 후 국민연금공단에 신청 → 1-3개월 내 해외 계좌로 입금.

## 실무 체크리스트
- [ ] 입사 후 14일 이내 4대보험 취득 신고
- [ ] 급여명세서에 공제 내역 명시
- [ ] 외국인등록번호로 건강보험 EDI 등록
- [ ] 퇴직 시 상실 신고 + 국민연금 반환 안내"""
    },
    {
        "board": "support_kr",
        "title": "표준근로계약서 작성 가이드 — 필수 기재사항",
        "pinned": 0,
        "body": """# 원어민 강사 표준근로계약서 작성 가이드

## 필수 기재사항 (근로기준법 제17조)

### 1. 근로계약기간
- 시작일과 종료일 명시 (보통 12개월)
- 수습기간이 있는 경우 별도 명시 (최대 3개월)
- 갱신 조건 명시

### 2. 근무장소 및 업무 내용
- 실제 근무할 주소
- 구체적인 업무 내용 (수업, 교재 준비, 행사 참여 등)
- 수업 대상 연령 및 레벨

### 3. 근로시간 및 휴게
- 1일/1주 근로시간 (법정 주 40시간)
- 수업시간 vs 근무시간 구분 명시
- 휴게시간 (4시간 근무 시 30분, 8시간 시 1시간)
- 초과근무 수당 규정

### 4. 급여
- 기본급 (세전 금액, 원화 표시)
- 지급일 (매월 몇 일)
- 지급방법 (계좌이체)
- 수당 항목 (초과근무, 교통비 등)

### 5. 휴일 및 휴가
- 주휴일 (보통 일요일)
- 유급연차 (1년 미만 근무 시 월 1일)
- 공휴일 처리 방법
- 병가 규정

### 6. 숙소
- 제공 여부 및 형태
- 숙소 수준 (옵션, 면적 등)
- 또는 주거지원금 금액

### 7. 항공권
- 편도/왕복 지원 여부
- 금액 상한선

## 한글·영문 병기 필수
- **법적 효력은 한글 계약서 기준**
- 영문은 강사 이해를 위한 참고용
- 양 언어 간 불일치 시 한글본 우선

## 주의사항
- 위약금 조항은 근로기준법 위반 소지 있음
- "갑의 사정에 따라 변경 가능" 같은 일방적 조항 지양
- 근로계약서 사본은 반드시 근로자에게 교부"""
    },

    # ══════════════════════════════════════════════════════════════════
    # TESTIMONIALS — 추가 후기
    # ══════════════════════════════════════════════════════════════════
    {
        "board": "testimonials",
        "title": "Rachel P. — New Zealand to Jeju",
        "pinned": 0,
        "body": """# Rachel P. — New Zealand to Jeju Island

**Background**: 26, from Auckland. Bachelor's in Communications, 120-hour TEFL certificate. No prior teaching experience.

## Why I Chose Korea
I'd been working in marketing for two years and felt stuck. A friend who taught in Seoul kept posting these amazing travel photos and I thought — why not? I found BRIDGE through a Reddit thread and sent in my application on a whim.

## The Process
The BRIDGE team was incredibly responsive. Within a week of my application, I had a phone consultation where they asked about my preferences. I said I wanted somewhere with nature and a smaller community feel — they immediately suggested Jeju.

My interview with the school was smooth. The director was friendly, asked standard questions, and seemed genuinely interested in what I could bring to the table. BRIDGE prepped me beforehand so I knew what to expect.

Documents took about 6 weeks total (NZ police check + apostille + degree verification). BRIDGE walked me through every step and kept a shared checklist so nothing fell through the cracks.

## Life on Jeju
I teach at a small academy in Jeju City. My students are mostly elementary-aged and absolutely hilarious. The Korean co-teacher is wonderful and has become one of my closest friends here.

Jeju is stunning — I hike Hallasan on weekends, swim at hidden beaches, and the cost of living is lower than Auckland. My apartment overlooks tangerine orchards. I sometimes have to pinch myself.

## The Honest Parts
- I miss my family, especially during Korean holidays when everyone goes to their hometowns
- The language barrier was frustrating for the first two months
- My school expected more admin work than I anticipated
- But the support from BRIDGE made every challenge manageable

## Would I Recommend BRIDGE?
Absolutely. They weren't just a recruiter — they felt like a support system. Even months after I arrived, I could message them with questions and get a response within hours.

**Time in Korea**: 14 months and counting. Already renewed my contract."""
    },
    {
        "board": "testimonials",
        "title": "Chris M. — USA to Daejeon",
        "pinned": 0,
        "body": """# Chris M. — USA (Texas) to Daejeon

**Background**: 31, from Houston. Bachelor's in History, CELTA certified. 2 years teaching experience in Thailand.

## Switching from Thailand to Korea
I loved Thailand but wanted better salary and savings potential. Korea was the obvious choice — higher pay, free housing, and a strong education system. After some bad experiences with other recruiters, I found BRIDGE through ESL Cafe forums.

## Why BRIDGE Was Different
Most recruiters I'd dealt with before felt like used car salesmen — pushing any job to get their commission. BRIDGE actually listened. When I said I wanted a hagwon with maximum 25 teaching hours and a school that wouldn't pile on admin work, they found exactly that.

They were also transparent about what to expect. "This school is great but the director can be strict about punctuality" — that kind of honest heads-up is rare in this industry.

## Daejeon — The Underrated City
Seoul gets all the hype, but Daejeon is incredible for quality of life. It's smaller, cheaper, less crowded, and still has KTX access to Seoul in under an hour. The food is amazing, the people are friendly, and I have a spacious apartment that would cost triple in Gangnam.

## My School
I teach middle school students at an English academy. Classes are small (6-8 students), the curriculum is well-organized, and my Korean co-teacher handles all parent communication. I work 9:30 AM to 6:30 PM with genuine breaks.

## Finances
On a 2.7M salary with free housing:
- Monthly expenses: about 800K won
- Monthly savings: about 1.5M won (roughly $1,100 USD)
- Severance after year 1: 2.7M won bonus
- This is life-changing for someone who was living paycheck to paycheck in the US.

## Advice for Others
1. Don't limit yourself to Seoul — smaller cities offer better value
2. Trust your recruiter but verify everything in the contract
3. Bring a good attitude and be flexible
4. Korea rewards teachers who stay and build relationships

**Time in Korea**: 2 years. Planning to stay at least one more."""
    },
]


def seed():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout = 5000")

    inserted = 0
    skipped = 0

    for post in POSTS:
        # Check if title+board already exists
        cur = conn.execute(
            "SELECT 1 FROM community_posts WHERE title = ? AND board = ? AND is_deleted = 0",
            (post["title"], post["board"])
        )
        if cur.fetchone():
            skipped += 1
            continue

        conn.execute(
            "INSERT INTO community_posts (board, title, body, author_hash, pinned) VALUES (?, ?, ?, 'bridge_admin', ?)",
            (post["board"], post["title"], post["body"].strip(), post.get("pinned", 0))
        )
        inserted += 1

    conn.commit()
    conn.close()
    print(f"Inserted: {inserted}, Skipped (already exist): {skipped}")


if __name__ == "__main__":
    seed()
