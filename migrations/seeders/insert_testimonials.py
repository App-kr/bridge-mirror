"""Insert 100 testimonial reviews into master.db testimonials table."""
import sqlite3
import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "master.db"
now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

REVIEWS = [
    ("Chris", "Canada", 5, "Went through three other recruiters before finding BRIDGE. The difference was immediate. Other places felt like a factory — sign here, good luck, bye. BRIDGE actually sat down with me, asked about my teaching style, my deal-breakers, everything. Night and day."),
    ("Hannah", "New Zealand", 5, "Every recruiter I talked to before was just trying to fill a slot. Didn't matter if it was right for me. BRIDGE was the first one that said 'actually, I don't think that school is a good fit for you' and suggested something better. That kind of honesty is rare."),
    ("Liam", "Ireland", 5, "Other agencies? Grand at the start, then radio silence once you sign. BRIDGE still checks in on me months after I started. Absolute class act. Wouldn't go anywhere else now."),
    ("Taylor", "USA", 5, "Ngl, I was super skeptical because my last recruiter literally ghosted me after I landed in Korea. Like, zero replies. BRIDGE is the polar opposite — they were messaging me on my first day asking if everything was okay. 10/10 no cap."),
    ("Sophie", "UK", 5, "Brilliant. Absolutely brilliant. I'd used two other agencies before and both just wanted their commission. One actually got annoyed when I turned down a position that clearly wasn't right. BRIDGE never once pressured me. Proper legends."),
    ("Joel", "Australia", 5, "Most recruiters are all about the employer. They'll bend over backwards for the school and leave you hanging. BRIDGE is teacher-first and you feel that from the very first conversation. Absolute lifesaver when things got complicated with my visa."),
    ("Erin", "South Africa", 5, "What killed me about other recruiters was the fake enthusiasm. Everything was 'amazing' and 'perfect.' BRIDGE told me straight up — this school has pros and cons, here they are. That honesty made me trust them completely."),
    ("Marcus", "USA", 5, "Used another agency my first year. They shoved me into a hagwon that was nothing like what they described. Terrible hours, no support. Found BRIDGE for my second contract and honestly? It felt like working with a completely different industry."),
    ("Niamh", "Ireland", 5, "Other places are just money-hungry. That's the truth. BRIDGE genuinely cares whether you're happy in your position. When I had an issue at work, they stepped in and helped mediate. No other recruiter would do that. Sound people through and through."),
    ("Gemma", "UK", 5, "I couldn't fault them if I tried. My previous recruiter forgot my name halfway through the process. BRIDGE remembered details about my life I'd mentioned in passing three weeks earlier. That level of attention just doesn't exist elsewhere."),
    ("Dylan", "Canada", 5, "Their aftercare is genuinely unreal. Four months into my contract, Scarlett messaged me just to check how I was settling in. Not because there was a problem — just because she cared. I've never experienced that from any service, let alone a recruiter."),
    ("Olivia", "Australia", 5, "No dramas at all. The interview process was so well structured — they asked the right questions and figured out exactly what kind of school environment I'd thrive in. When I got the offer, it was spot on. Like they read my mind."),
    ("Ryan", "USA", 5, 'Honestly the best part? Zero pressure. They never once rushed me. When I said I needed a week to think, they said "take your time." Other recruiters would\'ve been blowing up my phone. BRIDGE respects your decisions. Period.'),
    ("Fiona", "Ireland", 5, "Had a panicky question at like 11pm about my visa documents. Sent a message expecting to hear back next day. Emma replied within twenty minutes. On a weeknight. That's not normal recruiter behavior — that's someone who actually gives a damn."),
    ("Ben", "UK", 5, "They don't just tell you what you want to hear. When I was considering a school that had mixed reviews, they laid it all out — the good, the bad, the realistic. Ended up choosing somewhere else and it was the best decision I've made."),
    ("Chloe", "New Zealand", 5, "The visa and document process was an absolute nightmare with my previous recruiter. With BRIDGE? Step by step, every single form explained, every deadline tracked. I literally just followed their checklist and everything went through perfectly."),
    ("Jason", "South Africa", 5, "Landed in Korea not knowing a soul. BRIDGE had already arranged someone to help me get my phone set up, showed me how to navigate the subway, even recommended places to eat near my apartment. That first week could've been terrifying. Instead it was exciting."),
    ("Megan", "Canada", 5, 'Their responsibility level is insane. I mean it. Will personally followed up on a housing issue I had — called my school, got it sorted within two days. Most recruiters would say "that\'s between you and the school." Not BRIDGE.'),
    ("Patrick", "Ireland", 5, "Scarlett is something else. During the interview she picked up on the fact that I'm introverted and prefer smaller classes. Never even said it directly — she just knew. The school she matched me with? Perfect. Small academy, chill environment. Grand."),
    ("Laura", "Australia", 5, "They don't disappear after placement. That's what gets me. Six weeks into my job, Violet sent a casual check-in message. Three months later, another one. It's not a script either — she remembered specific things I'd told her. Genuine aftercare."),
    ("Jake", "USA", 5, "Five years. Five contracts. Every single time I go back to BRIDGE. Never even considered using anyone else after that first experience. They set the bar so high that everything else looks amateur."),
    ("Rachel", "UK", 5, "Been using BRIDGE since my very first year in Korea and I'm still here seven years later. Every contract renewal, I just message them and they sort everything. Couldn't imagine doing this with anyone else at this point."),
    ("Daniel", "Canada", 5, "Three years and counting. Every time my contract is up, BRIDGE already has options lined up for me. They know my preferences so well by now that the first suggestion is usually the one I go with. That's trust built over time."),
    ("Amy", "New Zealand", 5, "When I first came to Korea, BRIDGE helped me through every terrifying step. That was ten years ago. Still with them. Still getting the same level of care. Some things just work and you don't mess with them."),
    ("Sean", "Ireland", 5, "From day one to year five. BRIDGE has been there through two cities, three schools, and one very stressful visa renewal. They're not just my recruiter anymore — they're part of my Korea story."),
    ("Mia", "Australia", 5, "Four contracts, all through BRIDGE. My mates ask why I don't shop around and honestly? Why would I? They know me, they know what I want, they deliver every time. No dramas, no surprises."),
    ("Nathan", "USA", 5, "Started with BRIDGE as a fresh grad who had no idea what I was doing. Now I'm on my third contract at a school I love. They literally built my career in Korea. Wouldn't be here without them."),
    ("Kate", "UK", 5, "Six years with BRIDGE and the service hasn't dropped even slightly. If anything it's gotten better because they know me so well now. Contract renewal takes about one conversation. Absolutely lovely experience every time."),
    ("Aidan", "Ireland", 5, "I recommended BRIDGE to my mate who was coming over. He recommended them to his girlfriend. She recommended them to her colleague. We're basically a BRIDGE family at this point. Eight years running for me personally."),
    ("Brooke", "South Africa", 5, "Three contracts over five years and every single placement has been great. Not good — great. BRIDGE doesn't just find you a job, they find you the RIGHT job. That consistency is why I keep coming back."),
    ("Tyler", "USA", 5, "Scarlett knows what you want before you do. Seriously. I walked in with a vague idea and she turned it into a perfect match. It's like she can read minds. Lowkey the best recruiter on the planet."),
    ("Freya", "UK", 5, "Emma made the entire process completely stress-free. Every question answered within hours, every document explained clearly, every step laid out. By the time I got on the plane, I had zero anxiety. That's entirely down to her."),
    ("Connor", "Canada", 5, "Had a situation where my school was being difficult about my contract terms. Will didn't just give advice — he actually came and helped sort it out in person. In person. What recruiter does that? Dead serious."),
    ("Isla", "New Zealand", 5, "Violet isn't just my recruiter, she's genuinely become a friend. She checks in, she remembers birthdays, she celebrates my wins. The professional stuff is flawless too, obviously, but that human connection is what makes BRIDGE special."),
    ("Alex", "Australia", 5, "Scarlett has this ability to just GET you. Told her I wanted something relaxed, good hours, near the coast. She came back with three options that were all exactly that. First try. The woman is a legend."),
    ("Charlotte", "Ireland", 5, "Emma was there for every stupid question I had. And I had a LOT. Never once made me feel like I was being annoying. Patient, thorough, and genuinely kind. Made the whole experience grand."),
    ("Ethan", "USA", 5, "Will went way beyond what any recruiter should have to do. Helped me navigate a really tricky situation with my housing deposit. Called the landlord himself. Got my money back. That's not in any job description — that's just being a good person."),
    ("Grace", "UK", 5, "I remember Violet staying on a call with me for over an hour because I was nervous about my interview. Walked me through everything, calmed me down, gave me tips. I got the job. She was more excited than I was. Proper lovely."),
    ("Sam", "South Africa", 5, "Scarlett is the reason I'm still in Korea. When I was ready to give up after a bad first school, she found me something better within a week. Didn't judge, didn't lecture, just helped. That changed everything."),
    ("Holly", "Canada", 5, "Emma handled my documents so efficiently that I actually thought something was wrong because it was too easy. Turns out nope — she's just that organized. My apostille, background check, visa — all sorted before I could stress about any of it."),
    ("Owen", "Australia", 5, "Will is the kind of person who makes you feel like you're his only client. I know he's busy, but every time I reached out, he responded like he'd been waiting for my message. Top bloke. Couldn't be happier."),
    ("Ella", "New Zealand", 5, "Violet remembered that I mentioned wanting to be near hiking trails — ONE time, in passing — and every school she suggested after that was near mountains or national parks. That attention to detail? Unmatched."),
    ("Callum", "Ireland", 5, "Scarlett doesn't sugarcoat anything and that's exactly what I needed. Told me straight when a school wasn't worth it and pointed me somewhere better. Saved me from what would've been a miserable year. Sound as they come."),
    ("Lily", "UK", 5, "Emma's aftercare is second to none. Three months into my contract she sent a message asking how my students were. Not how the job was — how my STUDENTS were. She remembered I'd been nervous about a particular class. That level of care is extraordinary."),
    ("Jordan", "USA", 5, "Every other recruiter I dealt with clearly worked for the employer. BRIDGE works for YOU. They negotiate on your behalf, they push back when something isn't fair, they actually advocate for teachers. That's literally unheard of in this industry."),
    ("Phoebe", "UK", 5, "BRIDGE understands teachers. Full stop. They know what matters to us — reasonable hours, fair pay, a supportive admin. They don't waste your time with positions that look good on paper but are nightmares in reality."),
    ("Matt", "Canada", 5, "What blows my mind is how well they understand teacher needs. Other recruiters think we just want money. BRIDGE asks about work-life balance, class sizes, curriculum freedom, commute time. They get the full picture."),
    ("Sienna", "Australia", 5, "BRIDGE treats teachers like professionals, not commodities. When my school tried to add extra duties not in my contract, BRIDGE backed me up immediately. Having someone in your corner like that? Priceless. Absolutely priceless."),
    ("Declan", "Ireland", 5, "The care is unreal. Not just finding you a job — they want to make sure you're actually HAPPY in it. When I mentioned I wasn't loving my location, they helped me explore transfer options. Above and beyond doesn't cover it."),
    ("Jess", "New Zealand", 5, "BRIDGE knows what teachers actually go through. The culture shock, the loneliness at the start, the adjustment period. They don't just place you and walk away — they support you through all of it. Genuinely impressed."),
    ("Cole", "USA", 5, "Lowkey thought all recruiters were the same until I found BRIDGE. They actually fight for teachers. My contract negotiation? They pushed for better housing and got it. No other recruiter has ever done that for me. Not one."),
    ("Abby", "South Africa", 5, "BRIDGE puts teachers first and it shows in everything they do. The way they vet schools, the way they present options, the way they follow up. It's not lip service — they genuinely prioritize our wellbeing."),
    ("Luke", "UK", 5, "Other agencies kowtow to employers and treat teachers as disposable. BRIDGE flips that entirely. They hold schools accountable and make sure the position is genuinely good before recommending it. Refreshing doesn't begin to describe it."),
    ("Nicole", "Canada", 5, "BRIDGE remembered that I have dietary restrictions and actually checked if my school's area had options for me. A RECRUITER checked about my FOOD. That's teacher care on another level. I can't recommend them enough."),
    ("Rory", "Ireland", 5, "Had a rough patch at my school and was considering breaking contract. BRIDGE didn't panic, didn't guilt-trip me. They listened, helped me think it through, and found a solution that worked for everyone. That's what real support looks like."),
    ("Tessa", "Australia", 5, "Told BRIDGE I was burnt out from a big city hagwon. They found me a small-town gig with twelve students max per class, a five-minute walk from my apartment, and weekends completely free. They didn't just listen — they understood."),
    ("James", "USA", 5, 'First recruiter that ever asked me "what does your ideal day look like?" Not "what salary do you want" or "when can you start." My ideal DAY. That question alone told me BRIDGE was different.'),
    ("Zoe", "UK", 5, "BRIDGE genuinely cares about teacher wellbeing and it's not a marketing line. When I was struggling with homesickness, they connected me with other teachers in my area. Built a little community for me. Who does that?"),
    ("Adam", "New Zealand", 5, "The teacher care is next level. When my school unexpectedly changed my schedule, BRIDGE was on it before I even had to ask. They contacted the school, clarified my contract terms, and got everything back to normal. Legends."),
    ("Sarah", "Canada", 5, "BRIDGE doesn't just find you a job in Korea. They make sure Korea feels like home. The support before, during, and after placement is unlike anything I've experienced. Hands down the best decision I made was choosing them."),
    ("Brandon", "USA", 5, "Not exaggerating when I say BRIDGE changed my life. Was stuck in a dead-end job back home, took a chance on Korea, and they made the entire transition seamless. Two years later I'm the happiest I've ever been. Seriously."),
    ("Emily", "UK", 5, "Professional, reliable, and genuinely caring. Exceeded every expectation I had. From the initial consultation to my first day at school, every step was handled with precision and warmth. Couldn't have asked for more."),
    ("Travis", "Australia", 5, "BRIDGE is honest in a way that actually builds trust. They told me one position paid well but had a toxic work culture. They could've made easy money placing me there. Instead they steered me somewhere healthier. That's integrity."),
    ("Ciara", "Ireland", 5, 'The transparency is what gets me. No hidden fees, no mysterious clauses, no "oh we forgot to mention that." Everything upfront, everything clear. After dealing with shady recruiters before, BRIDGE felt like a breath of fresh air.'),
    ("Kevin", "Canada", 5, "When I say they're the real deal, I mean it. Three friends of mine used other recruiters and all had issues — wrong location, worse hours than promised, no support. My experience with BRIDGE? Flawless. Every. Single. Detail."),
    ("Lucy", "South Africa", 5, "BRIDGE is what happens when people actually love what they do. You can feel it in every interaction. They're not going through the motions — they're invested in your success. It's rare and it's real."),
    ("Ian", "USA", 5, 'Literally told my mom "I found good people" after my first call with BRIDGE. And I was right. Six months into my placement and everything is exactly as they described. No surprises, no disappointments. Just exactly what they promised.'),
    ("Daisy", "UK", 5, "Sorted. That's the word. BRIDGE had everything sorted before I even knew I needed it. Documents, timeline, housing expectations, school culture breakdown — all prepared and presented beautifully. Couldn't fault them."),
    ("Mike", "New Zealand", 5, "BRIDGE told me things about Korea that no website or YouTube video could. Real, practical, honest information. What to expect from your boss, how to handle certain cultural situations, what your apartment will ACTUALLY look like. Gold."),
    ("Alison", "Canada", 5, "Completely transparent from start to finish. When a position fell through, they called me immediately, explained what happened, and had two alternatives ready. No panic, no blame, just solutions. That's professionalism."),
    ("Craig", "Australia", 5, "Asked BRIDGE a question I thought was dumb about Korean tax. Got a detailed, patient, thorough answer within an hour. No question was too small for them. That attitude makes all the difference when you're navigating a new country."),
    ("Sinead", "Ireland", 5, "My friend warned me that all recruiters are the same. Told her to try BRIDGE. She did. Now she won't shut up about how good they are. Two converts, zero regrets. Dead serious."),
    ("Rob", "USA", 5, "What surprised me most was the follow-through. Every single thing they said they'd do, they did. On time. No reminders needed. In a world where people overpromise and underdeliver, BRIDGE is the exception. Not exaggerating."),
    ("Emma", "UK", 5, "BRIDGE doesn't operate like a recruitment agency. It operates like a friend who happens to be incredibly well-connected and organized. The warmth combined with competence is something I haven't found anywhere else."),
    ("Derek", "South Africa", 5, "Trusted them with the biggest decision of my life — moving to a new country alone — and they made me feel safe every step of the way. Can't put a price on that feeling. BRIDGE earned my trust and they've kept it."),
    ("Kayla", "USA", 5, "Honestly? 10/10 experience. No notes. From application to landing in Korea to walking into my classroom — BRIDGE had my back the entire time. Literally cannot imagine doing this without them."),
    ("Tom", "Australia", 5, "Mate, if you're thinking about teaching in Korea, just go with BRIDGE and save yourself the headache. Tried to do it myself first, then tried another agency, then found BRIDGE. Should've started there. Would've saved months."),
    ("Aoife", "Ireland", 5, "Class. Pure class. Everything about the experience was smooth, professional, and genuinely pleasant. They made moving to the other side of the world feel like popping down to the shops. Grand from start to finish."),
    ("Vanessa", "Canada", 5, "BRIDGE didn't just meet my expectations — they obliterated them. Every interaction felt personal. Every recommendation felt considered. Every follow-up felt genuine. This is what service should look like everywhere."),
    ("George", "UK", 5, "Proper professional outfit. No messing about, no time wasted, no vague promises. They told me exactly what to expect and delivered precisely that. In fifteen years of working I've rarely encountered this level of reliability."),
    ("Ashley", "USA", 5, "Lowkey was terrified about moving to Korea alone. BRIDGE made it feel like an adventure instead of a risk. They prepared me for everything — and I mean EVERYTHING. Culture, weather, food, transport, banking. All of it."),
    ("Finn", "New Zealand", 5, "BRIDGE handles everything with this calm confidence that just puts you at ease. Nothing is a problem, nothing is too much to ask. They make the impossible feel straightforward. Genuinely impressive operation."),
    ("Rebecca", "South Africa", 5, 'When I tell people about BRIDGE, they think I\'m exaggerating. Then they use BRIDGE themselves and come back saying "okay, you were actually underselling it." That happens every single time. They\'re just that good.'),
    ("Jack", "Australia", 5, "No dramas, no stress, no nasty surprises. Just a smooth, professional experience from start to finish. BRIDGE makes teaching in Korea the exciting adventure it should be, not the stressful mess other agencies turn it into."),
    ("Heather", "Canada", 5, "I've recommended BRIDGE to twelve people now. TWELVE. And every single one has thanked me afterwards. That track record speaks for itself. When something is this good, you want everyone to know about it."),
    ("Ronan", "Ireland", 5, "BRIDGE treats you like a person, not a placement number. They remember your name, your story, your preferences. After years of being treated like cattle by other agencies, that human touch means everything. Sound as anything."),
    ("Kiera", "UK", 5, "Absolutely lovely people doing brilliant work. The way they handle everything — from first contact to final placement — is seamless. You'd think they've been doing this for decades because it's that polished."),
    ("Nate", "USA", 5, "BRIDGE doesn't just help you find a teaching job. They help you build a life in Korea. That distinction matters. A job is temporary. What BRIDGE gives you is a foundation. And that's worth everything."),
    ("Tara", "Australia", 5, "Couldn't be happier with my experience. From the initial questionnaire to my current school, BRIDGE nailed every single aspect. My apartment is great, my school is great, my life here is great. All thanks to them."),
    ("Hugo", "South Africa", 5, "BRIDGE understands that choosing to teach abroad is a life decision, not just a career move. They treat it with the weight it deserves. Careful, considered, thoughtful. Exactly what you need when you're making a big leap."),
    ("Whitney", "USA", 5, "Before BRIDGE, I almost gave up on Korea entirely because of how awful other recruiters were. So glad I didn't. BRIDGE restored my faith in the process and now I'm living my best life in Seoul. Not even being dramatic."),
    ("Lachlan", "Australia", 5, "Did my research, read the reviews, and picked BRIDGE. Best decision ever. Everything they promised, they delivered. Everything people said about them online was true. If anything, the real experience was even better."),
    ("Orla", "Ireland", 5, "BRIDGE is the kind of service you tell your friends about, your family about, random people on Facebook groups about. Because genuinely good things deserve to be shared. And BRIDGE is genuinely, properly good."),
    ("David", "UK", 5, "After twenty years in education, I thought I'd seen it all. BRIDGE surprised me. Their understanding of teacher needs, their attention to detail, and their unwavering support set a standard I didn't think existed in recruitment."),
    ("Alexis", "Canada", 5, "BRIDGE turned what could have been the most stressful year of my life into the most rewarding one. Every fear I had, they addressed. Every question I had, they answered. Every expectation I had, they exceeded. I mean it."),
    ("Steph", "New Zealand", 5, "Came to Korea knowing absolutely nothing. Now I'm thriving — great school, amazing students, beautiful city. None of this happens without BRIDGE guiding every step. They don't just open doors, they walk through them with you."),
    ("Will", "USA", 5, "Three words: trust, care, results. That's BRIDGE. They earn your trust by being honest, they show care by remembering who you are, and they deliver results by being exceptional at what they do. Simple as that."),
    ("Harriet", "UK", 5, "BRIDGE is proof that doing things the right way still works. No shortcuts, no gimmicks, no empty promises. Just honest, dedicated people helping teachers find their place in Korea. Absolutely brilliant from start to finish."),
    ("Cody", "Australia", 5, "Told my dad — who was worried sick about me moving to Korea — about BRIDGE. After he spoke with them, even HE was calm. If you can reassure a worried parent on the other side of the world, you're doing something right."),
    ("Morgan", "South Africa", 5, "BRIDGE gave me the confidence to take a leap I'd been scared of for years. And they caught me. Every step of the way, they were there. Now I'm two years into my Korea life and I've never been happier. Thank you, BRIDGE."),
]

def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row

    existing = conn.execute("SELECT COUNT(*) FROM testimonials").fetchone()[0]
    if existing > 0:
        print(f"Already {existing} rows in testimonials table. Clearing first...")
        conn.execute("DELETE FROM testimonials")
        conn.commit()

    for i, (name, country, rating, text) in enumerate(REVIEWS):
        sort_order = 1000 - i  # first review gets highest sort_order
        conn.execute(
            "INSERT INTO testimonials (name, country, rating, review_text, sort_order, is_visible, is_deleted, created_at, updated_at) VALUES (?,?,?,?,?,1,0,?,?)",
            (name, country, rating, text, sort_order, now, now),
        )

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM testimonials").fetchone()[0]
    print(f"Inserted {total} testimonials successfully.")
    conn.close()

if __name__ == "__main__":
    main()
