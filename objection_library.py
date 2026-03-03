"""
OBJECTION LIBRARY & RECOVERY LOGIC (v1.0)
Professional merchant services objection handling for Agent Alan.
"""

OBJECTIONS = {
    "rates_high": {
        "pattern": ["rates are high", "too expensive", "better deal elsewhere", "lower rate"],
        "strategy": "Anchor on total cost — not the rate, the TOTAL. Use specificity to create credibility.",
        "response_logic": "Yeah, I hear that a lot. Here's what I've found though — most processors show you a low rate up front, but then there's the interchange markup, the batch fees, the statement fees, the PCI compliance fee... it adds up. What we do is actually eliminate the percentage entirely, so you're just paying a flat monthly. Honestly, the easiest way to see it is if I just pull up your last statement — takes me about two minutes to show you the difference. What does your statement usually look like, around how many pages?"
    },
    "interchange_confusion": {
        "pattern": ["fees don't make sense", "what is interchange", "too many line items", "statements are confusing"],
        "strategy": "Be the expert who makes it simple. Sound like a peer explaining, not a salesperson pitching.",
        "response_logic": "So interchange is basically the wholesale cost that Visa and Mastercard charge — think of it like the cost of goods. Your processor takes that and marks it up, and that markup is where they make their money. The problem is most merchants never see that breakdown. What we do is either show you exactly what you're paying at cost, or we move you to a model where you don't pay a percentage at all. If you want, shoot me page one of your statement and I'll show you exactly where the markup is hiding."
    },
    "comparison_needed": {
        "pattern": ["need to compare", "send me info", "talk to my partner", "already have a guy", "check with my accountant", "check with my spouse"],
        "strategy": "Make comparison effortless. Assumptive language. Remove friction. Offer to include their decision-maker.",
        "response_logic": "That's smart, honestly I'd do the same thing. Here's what I'll do — I'll put the full analysis in writing so they can review it too. And if it would be helpful, I'm happy to jump on a quick call with both of you together so I can answer any questions directly. When would work for everyone?"
    },
    "busy_frustrated": {
        "pattern": ["busy right now", "not interested", "bad time", "call back later"],
        "strategy": "Respect their time — then give them one specific reason to stay. Offer two time options.",
        "response_logic": "Completely understand — I only need 15 minutes and I can work around your schedule completely. What's a slower time for you — early morning before the rush, or later in the afternoon?"
    },
    "happy_with_processor": {
        "pattern": ["we're happy", "we're good", "we're fine", "happy with what we have", "no complaints"],
        "strategy": "Don't attack their processor. Reframe satisfaction as untested assumption. Offer free audit as zero-risk check.",
        "response_logic": "That's honestly what I love to hear — but let me ask you this: has anyone ever shown you an itemized breakdown of every fee you're paying? Not just the rate, but the monthly fees, batch fees, PCI fees, statement fees? Most owners I sit with are happy — until they see the full picture. I'll tell you right now if you're getting a fair deal. If you are, I'll shake your hand and walk out. Fair enough?"
    },
    "identity_confusion": {
        "pattern": ["who is this", "where are you calling from", "how did you get my number"],
        "strategy": "Sound like a peer, not a solicitor. Short, confident, no over-explaining.",
        "response_logic": "Yeah, sorry about that — it's Alan over at Signature Card Services. I do free rate reviews for business owners — takes five minutes and most find savings they didn't know were there. Is the owner around?"
    },
    "send_email": {
        "pattern": ["send me something", "email me", "send me an email", "put something in writing"],
        "strategy": "Redirect to in-person/call with real numbers. A brochure doesn't sell — custom analysis does.",
        "response_logic": "I can definitely do that — but honestly, what I do is very numbers-specific to your business. A generic brochure won't show you what YOU'RE actually paying versus what you could be paying. What I'd rather do is get 15 minutes on your calendar and bring actual numbers. If after that you're not interested, no problem at all. What does Thursday look like?"
    },
    "locked_contract": {
        "pattern": ["locked in", "under contract", "can't switch", "early termination", "ETF"],
        "strategy": "Run the break-even math. ETF vs. monthly savings = months to recoup. Under 3 months = no-brainer.",
        "response_logic": "That's actually more common than you'd think. Can I ask — do you know when it expires and what the early termination fee is? Sometimes the monthly savings are so significant that it makes financial sense to buy out the contract. For example, if you're saving $400 a month and your termination fee is $500 — you break even in 6 weeks. Let's run the math and see if it makes sense."
    },
    "need_to_think": {
        "pattern": ["need to think about it", "let me think", "not sure yet", "need some time"],
        "strategy": "Respect the pause. Identify what's really holding them back. Offer written proposal as concrete next step.",
        "response_logic": "Absolutely, this is a business decision and I respect that. Can I ask — is there something specific you're unsure about, or is it more just wanting time to process everything? What if I put together a formal savings proposal with everything in writing — exact rates, exact fees, exact monthly savings — and get that to you by tomorrow? That way you have something concrete to review."
    },
    "savings_too_small": {
        "pattern": ["not enough savings", "not worth switching", "savings aren't enough", "only saving a little"],
        "strategy": "Ask their threshold, then restructure the offer. Introduce additional value (next-day funding, PCI elimination, Edge).",
        "response_logic": "I respect that — can I ask what number would make it worth it to you? Because sometimes there are additional ways I can structure the program — like next-day funding, eliminating your PCI fee, or a cash discount program — that can increase those savings significantly. Let me see if I can get those numbers up for you."
    },
    "processor_matched_rate": {
        "pattern": ["they matched", "processor lowered", "they gave me a better rate", "matched your rate"],
        "strategy": "Turn the match into validation. Question why they were overcharging in the first place. Offer rate lock guarantee.",
        "response_logic": "I'm glad they did — that means our conversation saved you money already. Here's my question though: why were they charging you that much in the first place? They only lowered it because you asked. What happens in 6 months when your rep changes or they quietly add fees back? I'd be happy to put our offer in writing with a rate lock guarantee — so you always know exactly what you're getting. Worth comparing?"
    },
    "not_ready": {
        "pattern": ["not ready", "maybe later", "not the right time", "after the holidays"],
        "strategy": "Find the trigger event. Set a specific callback date. Stay warm, not pushy.",
        "response_logic": "Totally fair. Can I ask — is there a timeline that makes more sense? Like after a busy season, or once you hit a certain volume? I'd rather check back with you at the right time than push you before you're ready. What would make this the right time for you?"
    },
    "went_with_someone": {
        "pattern": ["went with someone else", "already signed", "chose another company", "just switched"],
        "strategy": "Congratulate, gather intel, plant 6-month seed. Contracts end, service issues arise.",
        "response_logic": "I appreciate you letting me know — congrats on getting that sorted out. Can I ask who you went with, just so I know for future reference? Good choice — they're a solid company. Hey, I'd love to stay in touch. Things change — contracts end, service issues come up — and I'd want to be your first call if that happens. Mind if I check back in with you in about 6 months?"
    },
    "switching_headache": {
        "pattern": ["pain to switch", "hassle", "headache", "too much work", "don't want to deal with it"],
        "strategy": "Remove switching anxiety. You handle EVERYTHING. Zero downtime. 48-hour turnaround.",
        "response_logic": "I hear that a lot and I completely understand. Here's the truth though — I handle the entire onboarding. I order the equipment, I do the programming, I coordinate the timing so there's zero downtime. Most of my clients are up and running within 48 hours and they say it was easier than they expected. What if we scheduled the setup for a morning before you open — would that take the stress out of it?"
    },
    "no_statement": {
        "pattern": ["don't have my statement", "can't find it", "don't have it on me"],
        "strategy": "Help them find it immediately (online portal) or set a specific follow-up.",
        "response_logic": "No problem at all. You can usually log into your processor's online portal and pull it up on your phone right now — or if you give me your processor's name, I can show you exactly where to find it. Alternatively, I can leave you a simple checklist of what to look for and we can reconnect Thursday — does that work?"
    },
    "use_bank": {
        "pattern": ["use our bank", "bank handles it", "bank processing", "through our bank", "bank does our processing"],
        "strategy": "Educate that banks overcharge on processing. Separate banking from processing. Offer comparison.",
        "response_logic": "A lot of business owners go that route — feels safe and convenient. Here's what most people don't know though: banks almost never offer competitive processing rates. They count on loyalty. In fact, bank processing is consistently some of the most expensive in the industry. I'm not asking you to change your banking relationship — just your processing. They're completely separate. Want me to show you the comparison?"
    },
    "dont_decide": {
        "pattern": ["don't make that decision", "not my call", "owner handles that", "you need to talk to", "I just work here"],
        "strategy": "Get to the decision maker. Don't waste time pitching the wrong person. Set specific callback.",
        "response_logic": "No problem at all — who does handle that? What I'd love to do is set up time when they're available. This directly affects your bottom line so I want to make sure the right person sees the numbers. What's the best way to reach them?"
    },
    "never_heard_of_you": {
        "pattern": ["never heard of you", "who are you", "don't know your company", "never heard of your company"],
        "strategy": "Turn small company into advantage — low overhead = better rates, personal service vs call center.",
        "response_logic": "That's fair — we're not a household name like Chase or Square, and that's by design. We don't spend millions on advertising — we keep overhead low and pass those savings to our merchants. The difference is when you call me, you get ME — not a call center. When was the last time someone from your current processor called YOU to check in on your account?"
    },
    "burned_before": {
        "pattern": ["burned before", "bad experience", "got screwed", "last processor", "last rep", "promised me", "was a disaster", "won't fall for that"],
        "strategy": "This is a TRUST WOUND, not a rate objection. Listen fully. Lead with empathy and written transparency.",
        "response_logic": "I'm sorry to hear that — and unfortunately it happens more than it should in this industry. What went wrong — was it rates that changed, hidden fees, or service? That's exactly what I hear all the time and why I operate differently. Everything I quote is in writing before you sign anything. I'll show you the exact contract line by line. I'd rather lose the deal than have you feel that way again. Would you let me earn your trust starting with full transparency?"
    },
    "no_contract": {
        "pattern": ["don't want a contract", "no contracts", "month to month", "don't want to be locked in", "no commitment"],
        "strategy": "Reframe contract as rate PROTECTION, not a trap. Show ETF vs savings math.",
        "response_logic": "Totally understandable. Here's what the contract really means — it protects YOUR rate from changing. Without one, processors can raise rates whenever they want. The contract locks your pricing in. And the ETF is modest — let me show you the savings in just the first 3 months, because the math might make the contract feel very different."
    },
    "square_cheap": {
        "pattern": ["square charges 2.6", "stripe is cheaper", "only 2.6%", "flat rate is simpler", "square is easier"],
        "strategy": "Do the volume math. Show the dollar gap. Simple ≠ cheapest at real volume.",
        "response_logic": "Square is great for small volume — simple and easy. But at your volume, you're paying Square approximately $[calculate] per month. On interchange-plus, that same volume runs about $[our number]. That's $[gap] every single month — or $[annual] per year. At what point does simplicity stop being worth that much money?"
    },
    "only_care_rate": {
        "pattern": ["just give me the rate", "best rate", "lowest rate", "only care about rate", "what's your rate"],
        "strategy": "Rate is one piece. Total cost includes monthly, PCI, batch, statement fees. Give complete picture.",
        "response_logic": "I respect that — and I'll give you the most competitive rate I can. But let me be straight: the rate is only one piece. I've seen merchants get a great rate and still overpay because of monthly fees, PCI fees, and batch fees they didn't know about. Can I give you a complete number — total cost per month — so you know exactly what you're comparing?"
    },
    "want_zero_fees": {
        "pattern": ["zero fees", "no fees", "no processing fees", "eliminate fees", "don't want to pay fees"],
        "strategy": "Introduce cash discount / Edge program. 100% legal, near-zero processing cost.",
        "response_logic": "There's actually a way to do exactly that — it's called a cash discount program. You post a price that includes processing cost, and cash customers get a discount. Card customers pay the posted price. Your processing cost goes near zero. 100% legal and a lot of businesses are moving to it. Want me to show you how it works for your business?"
    },
    "call_next_month": {
        "pattern": ["call me next month", "try me later", "not right now", "maybe in a few weeks", "after the season"],
        "strategy": "Find out WHY next month. Quantify cost of waiting. Set specific callback.",
        "response_logic": "Absolutely. Is there something happening next month that makes the timing better? I want to call at the right time. Between now and then, that's another $[monthly overage] out the door — I just want to make sure that's a conscious choice."
    },
    "going_through_changes": {
        "pattern": ["going through changes", "changing things", "restructuring", "new management", "transition"],
        "strategy": "Changes can be your best opportunity (new location, expansion, new POS). Explore what's changing.",
        "response_logic": "Totally understand — what kind of changes? Depending on what's happening, this might actually be perfect timing — or I might want to wait too. I'd rather come back at the right moment than push you when it doesn't make sense."
    },
    "competitor_quoted_lower": {
        "pattern": ["quoted me lower", "got a better quote", "someone else is cheaper", "lower quote"],
        "strategy": "Request the quote for comparison. Focus on total cost, not headline rate. Expose hidden fees.",
        "response_logic": "I'd love to see that quote — seriously. In this industry, low quotes often leave out monthly fees, PCI fees, or have rate tiers that kick in for certain card types. I want to compare total cost, not headline rate. If they're genuinely lower all-in, I'll tell you. If there are fees they didn't mention, you'll want to know before you sign."
    },
    "clover_equipment": {
        "pattern": ["clover", "don't want to lose equipment", "keep my terminal", "my equipment"],
        "strategy": "Clover can often be reprogrammed. Separate equipment from processing decision.",
        "response_logic": "Clover is actually a great system. Here's something most people don't know: Clover devices can often be reprogrammed to work with a different processor. It depends on where you got it and whether it's locked. Let me look into that before we assume anything. Would you be open to moving forward if we could keep your Clover setup?"
    },
    "terminal_breaks": {
        "pattern": ["terminal breaks", "what if something goes wrong", "equipment issue", "support", "who do I call"],
        "strategy": "Personal service differentiator. Direct number, replacement equipment, no call center.",
        "response_logic": "If your terminal goes down, you call me directly — not a 1-800 line. I have replacement equipment and I personally handle getting you back up. Every hour of downtime costs real money. When's the last time your current processor's rep gave you their personal cell?"
    },
    "rates_go_up": {
        "pattern": ["rates go up", "rates increase", "fees change", "price increase", "what if rates change"],
        "strategy": "Rate lock in contract. Only interchange (set by Visa/MC) can change — affects everyone equally.",
        "response_logic": "Your rate is locked in the contract for the full term. The only thing that can change is interchange — the base cost set by Visa and Mastercard — which affects every processor equally. Our markup is fixed. I'll show you exactly where that's stated before you sign."
    },
    "dont_like_salespeople": {
        "pattern": ["don't like salespeople", "hate sales calls", "stop calling", "don't trust salespeople"],
        "strategy": "Empathize. Reframe as transparent truth-teller, not pitcher. Offer math-only approach.",
        "response_logic": "I don't blame you — most people in my position lead with a pitch and don't listen. Here's the deal: I make money when I save you money. If I can't show real savings, I don't deserve your business. Let me just look at your numbers and tell you the truth — even if the truth is that you're getting a great deal. Fair?"
    },
    "research_online": {
        "pattern": ["research online", "look into it", "google it", "check online", "do my own research"],
        "strategy": "Validate but warn: processor sites are confusing. Offer to save them hours. Set follow-up.",
        "response_logic": "You absolutely can and there's good info out there. Fair warning though: processor websites are designed to be confusing, and without a real statement to compare, it's hard to know what you'd actually pay. What I do in 15 minutes would take hours online. But if you'd rather research first, totally understand. Would it be okay if I followed up in a week?"
    },
    # VERTICAL-SPECIFIC OBJECTIONS
    "tip_mismatch": {
        "pattern": ["tips don't match", "tip issues", "tip adjustment problems", "tip mismatch"],
        "strategy": "Restaurant pain point. Position automatic tip adjustment as solved problem.",
        "response_logic": "That's a real pain point and I'm glad you mentioned it. Our system handles tip adjustments automatically — the authorization matches the final settled amount. No more tip mismatches or manual adjustments. I can show you exactly how it works."
    },
    "toast_pos_locked": {
        "pattern": ["use toast", "use clover and can't change", "locked into pos", "can't change pos", "built into our pos"],
        "strategy": "Separate POS hardware from processing. Explore integration options.",
        "response_logic": "You don't have to change your POS. We can integrate with many configurations, or process payments separately without touching your current system. Let me look at your specific setup — there are usually more options than people realize."
    },
    "billing_software_bundled": {
        "pattern": ["billing software handles", "processing is built into", "bundled with our software", "part of our billing system"],
        "strategy": "Medical office objection. Research compatibility first. Show markup hidden inside software.",
        "response_logic": "I completely understand — the last thing you want is to disrupt your billing. Before anything else, I'll research whether your specific software supports an external processor. Many do. If it doesn't, I'll tell you upfront and we'll decide together if the savings justify any changes. No surprises."
    },
    "hsa_fsa_cards": {
        "pattern": ["hsa cards", "fsa cards", "health savings", "flexible spending", "accept hsa"],
        "strategy": "Reassure — HSA/FSA runs on Visa/MC networks. No payment types lost.",
        "response_logic": "Absolutely — HSA and FSA cards run on the Visa and Mastercard networks and process exactly like regular debit and credit cards. Any professional processor handles them. You won't lose a single payment type by switching."
    },
    "doctor_decides": {
        "pattern": ["doctor makes decisions", "have to check with the doctor", "doctor handles finances", "need to ask the doctor"],
        "strategy": "Empower the office manager. Provide clean numbers for a 5-minute pitch to the doctor.",
        "response_logic": "That's actually why I want to work with you first. If you can show the doctor a written analysis with specific savings numbers — that's a 5-minute conversation. I'll make the numbers so clear the decision practically makes itself. Can you get me 5 minutes with the doctor after your next staff meeting?"
    },
    "thin_margins": {
        "pattern": ["margins are thin", "can't afford to change", "margins are tight", "barely making it"],
        "strategy": "Retail objection. Thin margins = biggest reason TO look at processing. Every dollar counts.",
        "response_logic": "That's actually the most important reason to look at your processing. Thin margins mean every dollar counts. If I can put real savings back in your pocket without changing anything about how you run your store — isn't that worth 10 minutes? Thin margins are exactly why my best retail clients switched."
    },
    "holiday_bad_timing": {
        "pattern": ["holiday season", "busy season coming", "can't change right now", "bad timing to switch", "black friday"],
        "strategy": "Reframe: best time to switch is BEFORE high-volume periods. Savings proportional to volume.",
        "response_logic": "That's smart thinking, but actually the best time to switch is right before a high-volume period — because your savings are proportional to your volume. If you do $80K in December instead of $30K, your savings that month are nearly three times higher. Let's get you set up now so you're saving during your biggest month of the year."
    },
    "chargebacks_concern": {
        "pattern": ["lots of chargebacks", "chargeback problem", "disputed transactions", "online chargebacks"],
        "strategy": "Normalize. Ask for rate. Offer chargeback reduction tips as added value.",
        "response_logic": "That's worth knowing upfront — thank you for telling me. What's your approximate chargeback rate? That's within a manageable range. We work with merchants who have online channels and I'll make sure your agreement accounts for that. I'd also love to show you a few quick things you can do to reduce chargebacks — it directly impacts your bottom line."
    },
    "cash_discount_interest": {
        "pattern": ["cash discount program", "zero fees", "want zero processing", "pay no fees", "surcharge program"],
        "strategy": "Retail/any vertical. Explain cash discount mechanics. Position as solution you can set up.",
        "response_logic": "That's actually a great option and I can set that up for you. A cash discount program means you post a price that includes the processing cost — customers who pay cash get a small discount, customers who pay card pay the posted price. Your processing cost effectively goes to zero. It's fully legal and a growing number of businesses are doing it. Want me to show you exactly how it would work?"
    },
    # PHONE MASTERY RAPID-RESPONSE OBJECTIONS
    "who_are_you_with": {
        "pattern": ["who are you with", "what company", "who do you work for", "who is this calling from"],
        "strategy": "Answer directly and pivot to value. Don't over-explain or sound defensive.",
        "response_logic": "Signature Card Services — I do free rate reviews for business owners. Takes about five minutes and most find savings they didn't know were there. Got a quick minute?"
    },
    "how_got_number": {
        "pattern": ["how did you get my number", "where did you get my number", "how'd you get my number", "who gave you this number"],
        "strategy": "Normalize the outreach. You're a local rep reaching out to area businesses. Keep it casual.",
        "response_logic": "You're a local business — I reach out to owners in the area to offer free rate reviews on their card processing. No pressure, just real numbers. Most people I talk to are surprised at what they find."
    },
    "already_talked_to_someone": {
        "pattern": ["already talked to someone like you", "had someone call about this", "you guys already called", "someone already pitched me"],
        "strategy": "Differentiate your approach. Most reps quote rates — you analyze statements. Different value.",
        "response_logic": "I hear that a lot — and most reps just quote a rate and hope it sticks. What I do is different — I actually pull up your statement line by line and show you where every dollar is going. No pitch, just your real numbers. If you're getting a fair deal, I'll tell you that too. Worth five minutes?"
    },
    "is_this_sales_call": {
        "pattern": ["is this a sales call", "are you selling something", "is this a solicitation", "this a cold call"],
        "strategy": "Reframe as analysis, not sales. You tell the truth based on their numbers.",
        "response_logic": "It's a free analysis call, actually. I look at what you're paying on card processing and tell you the truth — even if the truth is that you've got a great deal. No obligation. Most business owners I talk to just want to know their real numbers."
    },
    "just_switched": {
        "pattern": ["we just switched", "just changed processors", "recently switched", "new processor"],
        "strategy": "Plant the 6-month seed. New processor honeymoon ends. Stay in their orbit.",
        "response_logic": "Perfect timing, actually — when did you switch? Here's what I'd suggest: give it 6 months and then compare your first few statements to what they promised. Rates and fees have a way of creeping up after the initial period. Would it be okay if I checked back in with you around that time?"
    }
}

RECOVERY_PHRASES = [
    "Yeah, I hear that a lot actually. Most people feel that way until they see the actual breakdown side by side.",
    "That makes sense. So let me ask you this — is it more the monthly fee that bugs you or the per-transaction cost?",
    "Honestly, that's exactly why most of our merchants switched over. They said the same thing before they saw the numbers.",
    "No, I totally get it. Out of curiosity though — when's the last time someone actually audited your statement for you?",
    "Fair enough. Can I just ask one thing before I let you go — do you know what your effective rate actually is right now?",
    "I get it. The only reason I bring it up is every business I sit down with finds at least one fee they didn't know they were paying.",
    "Totally respect that. What if I just showed you what your own numbers look like — takes two minutes. If there's nothing to save, I'll tell you that.",
    "I hear you. Quick question though — has anyone ever broken down your statement line by line and shown you where every dollar goes?",
    "That's fair. Look, I'm not trying to sell you anything right now. I just want to know if you're getting a fair deal. Most people aren't and don't realize it.",
    "Makes sense. Let me ask — if I could show you an extra $300 to $500 a month, would that be worth 15 minutes?",
    "That's completely fair — most business owners say the same thing before they see their numbers.",
    "I'm not here to pressure you — 8 out of 10 businesses I sit with are overpaying without knowing it. If you're the 2 out of 10, I'll shake your hand and leave.",
    "I'd rather be straight with you and earn a referral than push a deal that doesn't work.",
    "What would help you feel more confident about moving forward? I'd rather address what's holding you back than have you sitting on savings.",
]

CLOSING_SCRIPTS = {
    "statement_request": "Here's what I'll do — can you grab your latest processing statement? I'll look at it and tell you exactly what you're paying and if there's room to save. No obligation, no pressure. I do these all day — takes me about five minutes. You can snap a pic and text it to me, or I'll give you my email.",
    "meeting_set": "I'm going to be in your area this week. Would morning or afternoon work better for a quick walkthrough? I'll bring the numbers specific to your business.",
    "callback_set": "When's a good time to catch you for 15 minutes? I'll have everything prepared with your actual numbers — rates, fees, potential savings. Tuesday or Thursday work?",
    "curiosity_hook": "Something jumped out when I was looking at your numbers. When's a good time to go over it with you?",
    "new_business": "Congrats on the new business — exciting time. I specialize in getting new businesses set up with the best rates from day one, before they get locked into something expensive. Can I grab 15 minutes with you this week?",
    "follow_up_proposal": "I put together your personalized savings analysis based on your actual volume. Current monthly cost vs. projected cost on our program — everything in writing. Can we get 10 minutes this week to walk through it?",
    "switching_ease": "I handle the entire onboarding — equipment, programming, timing. Zero downtime. Most of my clients are up and running within 48 hours. What if we set it up for a morning before you open?",
    "trust_rebuild": "Everything I quote is in writing before you sign. I'll show you the contract line by line. I'd rather lose the deal than surprise you with anything. Would you let me earn your trust starting with full transparency?",
    "research_redirect": "When you're looking around, ask any processor three things: what's the monthly fee, what's the PCI fee, and what's the ETF. Then call me and I'll compare honestly. That way you're comparing the full picture.",
    "bank_comparison": "I'm not asking you to change banks — just your processing. They're completely separate. Want me to show you the comparison side by side? Most bank merchants are shocked at the difference.",
}

# GATEKEEPER SCREENING RESPONSES
# These are responses to common gatekeeper screening questions — spoken as natural language.
GATEKEEPER_RESPONSES = {
    "whos_calling": {
        "pattern": ["who's calling", "who is this", "may I ask who's calling", "can I ask who's calling"],
        "responses": [
            "Yeah, it's Alan.",
            "It's Alan — he'll know what it's about.",
            "Hey, it's Alan over at SCS Direct."
        ]
    },
    "whats_regarding": {
        "pattern": ["what's this regarding", "what is this about", "what's this about", "can I tell them what it's regarding", "may I ask what this is about"],
        "responses": [
            "It has to do with his finances. Is he available?",
            "It's regarding the business finances. Can I speak with the owner?",
            "It's about their processing setup. Just need a quick minute with them."
        ]
    },
    "theyre_busy": {
        "pattern": ["they're busy", "not available", "in a meeting", "not here right now", "stepped out", "can I take a message"],
        "responses": [
            "No problem — when's a better time to catch them?",
            "Got it. What time do they usually get in?",
            "Okay, I'll try them again later today. Thanks."
        ]
    },
    "send_email": {
        "pattern": ["can you send an email", "send me something", "put something in the mail", "email us"],
        "responses": [
            "I would, but it's really a thirty-second conversation — it won't make sense in an email. When's a good time to catch the owner?",
            "Sure, what's the best email? And what time should I follow up to walk them through it?",
            "Honestly it's easier to explain over the phone — takes about two minutes. When's he usually free?"
        ]
    }
}
