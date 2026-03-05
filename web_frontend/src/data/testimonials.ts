/**
 * Static testimonial data — 100 entries.
 * All names are fictional. No real PII.
 * Countries limited to: USA, Canada, UK, Ireland, Australia, New Zealand, South Africa
 */

export interface TestimonialEntry {
  name: string
  country: string
  stars: 4 | 5
  text: string
}

export const TESTIMONIALS: TestimonialEntry[] = [
  // ── 1–10 ──
  {
    name: 'Chris M.',
    country: 'USA',
    stars: 5,
    text: 'Honestly the best recruiting experience I\'ve had. No pressure, no weird sales tactics. They actually listened to what I wanted and matched me perfectly.',
  },
  {
    name: 'Hannah R.',
    country: 'UK',
    stars: 5,
    text: 'I\'ve been with BRIDGE for 6 years now and I keep coming back. Scarlett knows exactly what I\'m looking for before I even say it.',
  },
  {
    name: 'Liam O.',
    country: 'Ireland',
    stars: 5,
    text: 'Tried three other recruiters before BRIDGE. Night and day difference. They\'re patient, thorough, and genuinely care about where you end up.',
  },
  {
    name: 'Jess T.',
    country: 'Australia',
    stars: 5,
    text: 'BRIDGE made my transition so smooth. I was anxious about everything and they walked me through every step without ever making me feel rushed.',
  },
  {
    name: 'Ryan K.',
    country: 'Canada',
    stars: 5,
    text: 'What sets BRIDGE apart is they don\'t just throw you into any job. They take time to understand your teaching style and what kind of environment works for you.',
  },
  {
    name: 'Sophie L.',
    country: 'New Zealand',
    stars: 5,
    text: 'I was so nervous about the whole process but Emma was incredibly reassuring. She answered every single question I had, no matter how small.',
  },
  {
    name: 'Tyler B.',
    country: 'USA',
    stars: 5,
    text: 'Three years running with BRIDGE and I\'ve never had a bad experience. They genuinely care about finding you the right fit, not just filling a spot.',
  },
  {
    name: 'Megan W.',
    country: 'Canada',
    stars: 5,
    text: 'Most recruiters ghost you after placement. BRIDGE still checks in months later to make sure everything\'s going well. That says a lot about who they are.',
  },
  {
    name: 'Daniel P.',
    country: 'South Africa',
    stars: 5,
    text: 'Coming from South Africa I had no idea what to expect. BRIDGE made the entire process feel manageable and actually enjoyable. Couldn\'t recommend them more.',
  },
  {
    name: 'Chloe N.',
    country: 'UK',
    stars: 4,
    text: 'Really solid experience overall. Communication was clear, timelines were realistic, and they never overpromised. Refreshing compared to other agencies I\'ve dealt with.',
  },

  // ── 11–20 ──
  {
    name: 'Jack H.',
    country: 'Australia',
    stars: 5,
    text: 'BRIDGE is the only recruiter I trust. I\'ve recommended them to at least ten friends and every single one has had a great experience.',
  },
  {
    name: 'Alyssa F.',
    country: 'USA',
    stars: 5,
    text: 'I\'ve used other recruiters before but BRIDGE is different. They actually follow through on what they promise and the communication is always top-notch.',
  },
  {
    name: 'Ethan D.',
    country: 'Canada',
    stars: 5,
    text: 'Best decision I made was going through BRIDGE. The team matched me with a position that checked every single box on my list. Still can\'t believe it.',
  },
  {
    name: 'Olivia S.',
    country: 'Ireland',
    stars: 5,
    text: 'No pressure, no rushing, no shady contracts. Just honest, transparent communication from start to finish. That\'s rare in this industry.',
  },
  {
    name: 'Nathan G.',
    country: 'UK',
    stars: 5,
    text: 'Seven years working with BRIDGE and I wouldn\'t go anywhere else. They\'ve become more like friends at this point. Violet always goes above and beyond.',
  },
  {
    name: 'Emily C.',
    country: 'New Zealand',
    stars: 5,
    text: 'The interview process with BRIDGE was the most thorough I\'ve ever been through. They really dug into what I was looking for and it paid off massively.',
  },
  {
    name: 'Marcus J.',
    country: 'South Africa',
    stars: 5,
    text: 'I was skeptical at first because I\'d had bad experiences with recruiters. BRIDGE completely changed my mind. Professional, caring, and efficient.',
  },
  {
    name: 'Sarah V.',
    country: 'USA',
    stars: 4,
    text: 'Great experience with BRIDGE. They were upfront about everything — the good and the challenges. That honesty made me trust them from the start.',
  },
  {
    name: 'Connor M.',
    country: 'Ireland',
    stars: 5,
    text: 'BRIDGE doesn\'t treat you like a number. Every interaction felt personal and thoughtful. They remembered details about my preferences weeks later.',
  },
  {
    name: 'Lauren A.',
    country: 'Australia',
    stars: 5,
    text: 'Made the whole process stress-free. I didn\'t have to chase anyone for updates — they were always one step ahead. Absolute lifesavers.',
  },

  // ── 21–30 ──
  {
    name: 'James W.',
    country: 'UK',
    stars: 5,
    text: 'Fourth year with BRIDGE. Every single contract has been exactly what they described. No surprises, no hidden catches. Just reliable, honest recruiting.',
  },
  {
    name: 'Kayla R.',
    country: 'USA',
    stars: 5,
    text: 'I dragged my feet for months and they never once pressured me. When I was finally ready, they had options lined up within days. Incredible team.',
  },
  {
    name: 'Ben T.',
    country: 'Canada',
    stars: 5,
    text: 'Will helped me through the whole visa process and never made me feel like I was asking too many questions. Patient, kind, and super knowledgeable.',
  },
  {
    name: 'Grace P.',
    country: 'New Zealand',
    stars: 5,
    text: 'The level of care BRIDGE puts into matching teachers with the right schools is unmatched. They genuinely want you to be happy, not just employed.',
  },
  {
    name: 'Adam L.',
    country: 'South Africa',
    stars: 5,
    text: 'Never felt pressured to sign anything. They gave me time to think, compare options, and make the decision that was right for me. That meant everything.',
  },
  {
    name: 'Rachel B.',
    country: 'USA',
    stars: 5,
    text: 'I keep coming back to BRIDGE because they\'re consistent. Same high quality every single time. It\'s been five years and they haven\'t let me down once.',
  },
  {
    name: 'Tom S.',
    country: 'UK',
    stars: 4,
    text: 'Solid recruiting agency. They were straightforward about timelines and delivered on every promise. Would definitely use them again for my next contract.',
  },
  {
    name: 'Sienna K.',
    country: 'Australia',
    stars: 5,
    text: 'BRIDGE understands that finding the right job is about more than just a paycheck. They factor in lifestyle, teaching preferences, everything. So thoughtful.',
  },
  {
    name: 'David H.',
    country: 'Ireland',
    stars: 5,
    text: 'The whole team is just brilliant. Responsive, professional, and they clearly love what they do. You can feel it in every conversation.',
  },
  {
    name: 'Jessica E.',
    country: 'Canada',
    stars: 5,
    text: 'Hands down the best recruiters I\'ve worked with. They found me a position that I genuinely love and the support didn\'t stop after I got hired.',
  },

  // ── 31–40 ──
  {
    name: 'Kevin N.',
    country: 'USA',
    stars: 5,
    text: 'Ten years with BRIDGE. That should tell you everything. I\'ve watched them grow and they\'ve only gotten better. Loyal customer for life.',
  },
  {
    name: 'Amanda D.',
    country: 'UK',
    stars: 5,
    text: 'BRIDGE treats you like a person, not a placement. Scarlett took the time to really get to know me before suggesting anything. That personal touch makes all the difference.',
  },
  {
    name: 'Patrick O.',
    country: 'Ireland',
    stars: 5,
    text: 'Was ready to give up on teaching abroad until a friend recommended BRIDGE. They renewed my enthusiasm and found me a position I actually love waking up for.',
  },
  {
    name: 'Zoe F.',
    country: 'New Zealand',
    stars: 5,
    text: 'No other recruiter has ever been this thorough with the matching process. They asked questions I didn\'t even think to ask myself. Result? Perfect fit.',
  },
  {
    name: 'Michael T.',
    country: 'South Africa',
    stars: 5,
    text: 'BRIDGE is the gold standard. I\'ve told every teacher I know to use them. Professional, patient, and they actually deliver on what they say.',
  },
  {
    name: 'Kate M.',
    country: 'Australia',
    stars: 4,
    text: 'Really happy with my experience. The team was always available when I needed them and the whole process was much smoother than I expected.',
  },
  {
    name: 'Andrew C.',
    country: 'Canada',
    stars: 5,
    text: 'What I appreciate most about BRIDGE is the follow-up. Even after I started working, they checked in regularly. That level of aftercare is rare.',
  },
  {
    name: 'Natalie G.',
    country: 'USA',
    stars: 5,
    text: 'I was comparing five different agencies and BRIDGE won by a mile. Most responsive, most organized, and most genuinely interested in what I wanted.',
  },
  {
    name: 'Sam R.',
    country: 'UK',
    stars: 5,
    text: 'Third time using BRIDGE and each experience has been seamless. They\'ve set the bar so high I can\'t imagine going through anyone else at this point.',
  },
  {
    name: 'Brooke W.',
    country: 'Ireland',
    stars: 5,
    text: 'Emma made the entire transition feel effortless. From paperwork to placement, she handled everything with such professionalism and warmth.',
  },

  // ── 41–50 ──
  {
    name: 'Josh P.',
    country: 'Australia',
    stars: 5,
    text: 'BRIDGE doesn\'t just find you a job — they find you the RIGHT job. There\'s a massive difference and it shows in how thorough their process is.',
  },
  {
    name: 'Stephanie L.',
    country: 'New Zealand',
    stars: 5,
    text: 'Best decision I ever made. The team was incredibly supportive through every stage and I felt genuinely cared for. Can\'t thank them enough.',
  },
  {
    name: 'Brandon K.',
    country: 'USA',
    stars: 5,
    text: 'Six years with BRIDGE. Every contract better than the last. They learn your preferences over time and the matching just keeps getting more accurate.',
  },
  {
    name: 'Mia H.',
    country: 'Canada',
    stars: 4,
    text: 'Very professional outfit. They set clear expectations from the beginning and met every single one. Would recommend to anyone considering teaching abroad.',
  },
  {
    name: 'Owen D.',
    country: 'South Africa',
    stars: 5,
    text: 'BRIDGE made what could have been an overwhelming process actually enjoyable. Their patience and attention to detail is something I\'ve never experienced with another recruiter.',
  },
  {
    name: 'Elena V.',
    country: 'UK',
    stars: 5,
    text: 'They genuinely care about finding the right fit. Not just for the school, but for YOU. That\'s what makes BRIDGE different from every other agency out there.',
  },
  {
    name: 'Derek J.',
    country: 'Ireland',
    stars: 5,
    text: 'I appreciate that BRIDGE never rushed me into anything. They respected my timeline and when I was ready, everything fell into place perfectly.',
  },
  {
    name: 'Nicole B.',
    country: 'Australia',
    stars: 5,
    text: 'Violet was amazing to work with. So patient, so organized, and she genuinely seemed invested in making sure I ended up somewhere I\'d thrive.',
  },
  {
    name: 'Alex F.',
    country: 'USA',
    stars: 5,
    text: 'I went through two other recruiters who wasted my time before finding BRIDGE. Within a week they had three solid options for me. Game changer.',
  },
  {
    name: 'Laura N.',
    country: 'Canada',
    stars: 5,
    text: 'BRIDGE has the most personal approach I\'ve seen. They remembered my preferences, my concerns, everything. Made me feel like their only client.',
  },

  // ── 51–60 ──
  {
    name: 'Sean G.',
    country: 'UK',
    stars: 5,
    text: 'Eight years and counting with BRIDGE. They\'re the only recruiter I\'ve ever genuinely recommended to friends. Consistent quality every single time.',
  },
  {
    name: 'Ashley T.',
    country: 'New Zealand',
    stars: 5,
    text: 'From the first email to my first day at work, BRIDGE was there every step of the way. I never felt alone in the process and that meant the world.',
  },
  {
    name: 'Jordan M.',
    country: 'USA',
    stars: 5,
    text: 'No tricks, no hidden fees, no bait-and-switch. Just straightforward, quality recruiting. BRIDGE restored my faith in the industry.',
  },
  {
    name: 'Pippa S.',
    country: 'Ireland',
    stars: 5,
    text: 'I had a very specific list of requirements and honestly thought I was being unreasonable. BRIDGE found me exactly what I asked for. Still amazed.',
  },
  {
    name: 'Luke A.',
    country: 'Australia',
    stars: 4,
    text: 'Good experience overall. The team was communicative and responsive. They set realistic expectations which I really appreciated after dealing with other agencies.',
  },
  {
    name: 'Paige C.',
    country: 'South Africa',
    stars: 5,
    text: 'BRIDGE went above and beyond. They didn\'t just help me find a job — they helped me plan my entire move. I couldn\'t have done it without them.',
  },
  {
    name: 'Matt R.',
    country: 'Canada',
    stars: 5,
    text: 'The initial interview with BRIDGE was so in-depth. They asked about my teaching philosophy, my lifestyle preferences, everything. That\'s how they nail the matching.',
  },
  {
    name: 'Tara W.',
    country: 'UK',
    stars: 5,
    text: 'I was hesitant about using a recruiter after a bad experience elsewhere. BRIDGE changed my perspective completely. Professional, caring, and efficient.',
  },
  {
    name: 'Chris E.',
    country: 'USA',
    stars: 5,
    text: 'Will walked me through the entire contract and explained every clause. That kind of transparency is exactly what you need when you\'re making a big life decision.',
  },
  {
    name: 'Holly K.',
    country: 'New Zealand',
    stars: 5,
    text: 'BRIDGE treated my concerns with respect and never dismissed anything as trivial. That level of empathy is what makes them stand out in this field.',
  },

  // ── 61–70 ──
  {
    name: 'Nick J.',
    country: 'Ireland',
    stars: 5,
    text: 'Five years with BRIDGE. I\'ve turned down offers from other recruiters because why would I switch? They know me, they know what I want, and they deliver.',
  },
  {
    name: 'Victoria P.',
    country: 'Australia',
    stars: 5,
    text: 'BRIDGE is genuinely the most professional recruiting agency I\'ve worked with. Quick responses, clear communication, and no surprises. Exactly what you want.',
  },
  {
    name: 'Travis B.',
    country: 'USA',
    stars: 5,
    text: 'I was worried about moving abroad alone but BRIDGE made me feel like I had a support system from day one. They were always just a message away.',
  },
  {
    name: 'Rebecca L.',
    country: 'Canada',
    stars: 4,
    text: 'Straightforward process, no nonsense. BRIDGE told me what to expect and then delivered exactly that. In recruiting, that kind of reliability is gold.',
  },
  {
    name: 'Henry D.',
    country: 'UK',
    stars: 5,
    text: 'Scarlett and the team are absolute legends. They found me a position in under two weeks that I ended up staying at for three years. Couldn\'t be happier.',
  },
  {
    name: 'Angela N.',
    country: 'South Africa',
    stars: 5,
    text: 'I was nervous about the language barrier and cultural adjustment. BRIDGE addressed every concern I had with patience and real practical advice.',
  },
  {
    name: 'Kyle H.',
    country: 'Ireland',
    stars: 5,
    text: 'What I love about BRIDGE is the aftercare. They don\'t disappear once you\'re placed. They check in, they follow up, they actually care about how things are going.',
  },
  {
    name: 'Madison F.',
    country: 'New Zealand',
    stars: 5,
    text: 'I recommended BRIDGE to my sister and she had an equally amazing experience. Consistency like that tells you everything you need to know about a company.',
  },
  {
    name: 'Brian G.',
    country: 'USA',
    stars: 5,
    text: 'BRIDGE doesn\'t do one-size-fits-all. They tailor everything to your situation. That individualized approach is what makes them head and shoulders above the rest.',
  },
  {
    name: 'Fiona T.',
    country: 'Australia',
    stars: 5,
    text: 'Emma was so helpful through the entire visa process. She answered my panicked midnight emails within hours. That\'s dedication you don\'t see very often.',
  },

  // ── 71–80 ──
  {
    name: 'Scott C.',
    country: 'Canada',
    stars: 5,
    text: 'I\'ve been teaching for twelve years and BRIDGE is the only recruiter that\'s ever truly understood what experienced teachers are looking for. Refreshing.',
  },
  {
    name: 'Amy V.',
    country: 'UK',
    stars: 5,
    text: 'BRIDGE was recommended to me by three different people. Now I understand why. Seamless process, fantastic communication, and a team that genuinely cares.',
  },
  {
    name: 'Dylan W.',
    country: 'USA',
    stars: 5,
    text: 'No pressure, no sales pitch, just real conversations about what I wanted. BRIDGE treats recruiting like a partnership, not a transaction. Huge difference.',
  },
  {
    name: 'Gemma S.',
    country: 'Ireland',
    stars: 4,
    text: 'Very impressed with BRIDGE. They were organized, communicative, and always followed through. The matching process was more thorough than I expected.',
  },
  {
    name: 'William M.',
    country: 'South Africa',
    stars: 5,
    text: 'BRIDGE took the stress out of what should have been one of the most stressful decisions of my life. Their calm, professional approach made all the difference.',
  },
  {
    name: 'Ella R.',
    country: 'New Zealand',
    stars: 5,
    text: 'They never once tried to push me toward a position I wasn\'t comfortable with. In this industry, that kind of integrity is worth its weight in gold.',
  },
  {
    name: 'Aaron K.',
    country: 'Australia',
    stars: 5,
    text: 'Fourth contract through BRIDGE. At this point they know my preferences better than I do. The matching is always spot-on and the process is always smooth.',
  },
  {
    name: 'Charlotte D.',
    country: 'Canada',
    stars: 5,
    text: 'I was comparing BRIDGE with two other agencies and the difference in quality was obvious from the first conversation. They won me over immediately.',
  },
  {
    name: 'Pete A.',
    country: 'UK',
    stars: 5,
    text: 'Violet helped me negotiate a better package than I thought was possible. She really advocates for her teachers. That\'s not something you find everywhere.',
  },
  {
    name: 'Danielle J.',
    country: 'USA',
    stars: 5,
    text: 'Every question answered, every concern addressed, every deadline met. BRIDGE runs like a well-oiled machine and it shows in the results.',
  },

  // ── 81–90 ──
  {
    name: 'Ronan B.',
    country: 'Ireland',
    stars: 5,
    text: 'I\'ve recommended BRIDGE to at least fifteen people at this point. Not a single one has been disappointed. That track record speaks for itself.',
  },
  {
    name: 'Hayley G.',
    country: 'Australia',
    stars: 5,
    text: 'BRIDGE made me feel valued as a teacher, not just as a placement. They took time to understand my career goals and found a position that aligned perfectly.',
  },
  {
    name: 'Lucas T.',
    country: 'South Africa',
    stars: 5,
    text: 'The team is incredibly warm and approachable. I never felt like I was dealing with a faceless company. Every interaction was personal and genuine.',
  },
  {
    name: 'Courtney P.',
    country: 'New Zealand',
    stars: 4,
    text: 'Professional from start to finish. Clear communication, reasonable timelines, and no hidden surprises. BRIDGE does recruiting the way it should be done.',
  },
  {
    name: 'Ian F.',
    country: 'Canada',
    stars: 5,
    text: 'Nine years with BRIDGE. I keep coming back because the quality never drops. Other recruiters have come and gone but BRIDGE stays consistently excellent.',
  },
  {
    name: 'Abby L.',
    country: 'USA',
    stars: 5,
    text: 'BRIDGE is the recruiter your friends warn you about — in the best possible way. Once you try them, you\'ll never want to use anyone else. Trust me.',
  },
  {
    name: 'George N.',
    country: 'UK',
    stars: 5,
    text: 'Scarlett remembered details about my situation from a conversation we had months earlier. That attention to detail is what separates BRIDGE from everyone else.',
  },
  {
    name: 'Kelsey H.',
    country: 'Ireland',
    stars: 5,
    text: 'I needed a very flexible timeline and BRIDGE worked around my schedule without any complaints. They adapted to me instead of forcing me into their process.',
  },
  {
    name: 'Thomas E.',
    country: 'Australia',
    stars: 5,
    text: 'BRIDGE doesn\'t just fill positions. They build careers. That mindset shines through in everything they do, from the first call to the final placement.',
  },
  {
    name: 'Jenny C.',
    country: 'Canada',
    stars: 5,
    text: 'I\'ve worked with recruiters in three different countries and BRIDGE is by far the best. Their process is smooth, their team is lovely, and the results speak for themselves.',
  },

  // ── 91–100 ──
  {
    name: 'Blake D.',
    country: 'USA',
    stars: 5,
    text: 'Will helped me understand every aspect of my contract before I signed. No rushed decisions, no fine print traps. That transparency earned my trust completely.',
  },
  {
    name: 'Freya M.',
    country: 'UK',
    stars: 5,
    text: 'BRIDGE operates on a different level. While other recruiters send mass emails, BRIDGE sends personalized options that actually match what you\'re looking for.',
  },
  {
    name: 'Caleb S.',
    country: 'South Africa',
    stars: 5,
    text: 'I almost didn\'t move abroad because my first recruiter was so bad. A friend convinced me to try BRIDGE and I\'m so glad I did. Complete 180.',
  },
  {
    name: 'Isla K.',
    country: 'New Zealand',
    stars: 4,
    text: 'Thorough, reliable, and genuinely nice people. BRIDGE made the whole experience positive from beginning to end. Would absolutely use them again.',
  },
  {
    name: 'Nate R.',
    country: 'Ireland',
    stars: 5,
    text: 'Seven years working through BRIDGE. They\'ve seen me grow as a teacher and each new placement reflects that growth. It\'s a real partnership.',
  },
  {
    name: 'Zara W.',
    country: 'Australia',
    stars: 5,
    text: 'The first thing that struck me about BRIDGE was how much they listened. Not just heard, but actually listened and acted on everything I said. So rare.',
  },
  {
    name: 'Mark J.',
    country: 'Canada',
    stars: 5,
    text: 'BRIDGE turned what I thought would be a stressful ordeal into a genuinely exciting journey. Their energy and enthusiasm is infectious. Love this team.',
  },
  {
    name: 'Phoebe A.',
    country: 'USA',
    stars: 5,
    text: 'I can\'t say enough good things about BRIDGE. They went above and beyond at every turn. If you\'re on the fence, just do it. You won\'t regret it.',
  },
  {
    name: 'Oliver G.',
    country: 'UK',
    stars: 5,
    text: 'Violet and the team were incredible throughout the whole process. Responsive, thoughtful, and always available when I needed them. Five stars isn\'t enough.',
  },
  {
    name: 'Tessa B.',
    country: 'South Africa',
    stars: 5,
    text: 'BRIDGE changed my life. That sounds dramatic but it\'s true. They found me a position I love, in a place I love, with people I love. Forever grateful.',
  },
]
