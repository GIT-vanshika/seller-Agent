# AURA COMMERCE --- DESIGNER.md

## Creative Direction & UI Design System for the AI Purchase Confidence & Deal Agent

> Give this document to Antigravity before making further frontend
> changes.
>
> This is a design-direction document, not a request to blindly rewrite
> the application. Antigravity must inspect the current frontend first,
> preserve working behavior, and then implement the visual system
> described here.

------------------------------------------------------------------------

# 01 --- THE DESIGNER ROLE

Act as the **Creative Director + Principal Product Designer + Senior
Frontend Engineer** for this product.

Your job is not to make the website merely "clean".

Your job is to make the interface feel like a **real next-generation
commerce product that happens to contain an AI agent**.

The visual experience should communicate, without explanation:

-   premium commerce
-   confidence
-   intelligence
-   evidence
-   negotiation
-   financial safety
-   transaction readiness

The product should feel **designed**, not assembled from cards.

### Design north star

> **Confidence becomes visible.**

The buyer should feel that the interface is actively helping them move
from:

**I am unsure → I have evidence → let's negotiate → we have a deal →
this deal is locked → I can pay.**

The UI itself should tell that story.

------------------------------------------------------------------------

# 02 --- PRODUCT EXPERIENCE

The product is **AURA Commerce**.

It is an AI purchase confidence and deal agent.

The interface combines:

1.  Product discovery
2.  Product information
3.  Evidence-backed trust
4.  Conversational AI
5.  Seller-controlled negotiation
6.  Quantity-aware commercial offers
7.  Deterministic deal validation
8.  Razorpay checkout

These must feel like **one continuous experience**, not separate
modules.

The design must NOT look like a product card + chatbot + evidence
dashboard + calculator + payment widget stitched together.

------------------------------------------------------------------------

# 03 --- VISUAL PERSONALITY

## Desired feeling

Imagine:

**Apple Store** × **Shopify Plus** × **Stripe** × **a polished AI
concierge**

Do not copy any brand.

We want:

-   editorial
-   sophisticated
-   quiet confidence
-   premium whitespace
-   strong typography
-   precise financial presentation
-   subtle motion
-   rich product imagery
-   restrained color

The interface should feel:

**Premium, intelligent, calm, tactile, trustworthy, modern.**

It should NOT feel:

-   generic SaaS
-   admin dashboard
-   developer tool
-   chatbot wrapper
-   neon AI website
-   crypto dashboard
-   glassmorphism demo
-   purple-gradient startup template
-   excessive rounded cards
-   "everything is a pill"

------------------------------------------------------------------------

# 04 --- CORE VISUAL CONCEPT

## "Commerce Stage"

The entire page is one stage.

Desktop:

``` text
┌─────────────────────────────────────────────────────────────────────┐
│ AURA                                      Products       AI ACTIVE   │
├───────────────────────────────────┬─────────────────────────────────┤
│                                   │                                 │
│          PRODUCT WORLD            │          AI CONCIERGE           │
│                                   │                                 │
│  Large product visual             │  Conversation                  │
│  Product identity                 │  Evidence references            │
│  Price / specs                    │  Negotiation                    │
│                                   │  Deal state                     │
│  Evidence / reality media         │  Checkout transition            │
│                                   │                                 │
└───────────────────────────────────┴─────────────────────────────────┘
```

The split must feel intentional, not like "two columns".

Desktop ratio: approximately **58--62% product / 38--42% concierge**.

Mobile should become a deliberate vertical story:

``` text
Product
↓
Evidence
↓
AI conversation
↓
Negotiation
↓
Deal
↓
Payment
```

Do not simply shrink the desktop layout.

------------------------------------------------------------------------

# 05 --- COLOR SYSTEM

Use a restrained neutral foundation.

## Foundation

``` text
Canvas        #F7F8FA
Surface       #FFFFFF
Surface Soft  #F1F3F6
Ink           #111827
Ink Soft      #475569
Muted         #94A3B8
Border        #E5E7EB
```

## Intelligence / evidence

``` text
Sapphire      #2563EB
Sapphire Soft #EFF6FF
```

Use sapphire for AI activity, evidence provenance, cited evidence and
subtle focus rings.

## Negotiation

``` text
Amber         #B7791F
Amber Soft    #FFF7E6
```

Use amber sparingly for negotiation in progress and offer/counter
states.

## Deal / success

``` text
Emerald       #16845B
Emerald Soft  #ECFDF5
```

Use emerald for accepted deals, validation, savings, payment readiness
and successful transaction.

### Important

Do not turn the entire interface blue/green/amber.

Color should **explain state**, not decorate the page.

------------------------------------------------------------------------

# 06 --- TYPOGRAPHY

Use a modern system / Inter / Geist-style sans-serif.

### Product name

Approximately 32--44px desktop, 26--32px mobile, weight 600--700, tight
tracking.

### Section title

16--20px, weight 600.

### Body

14--16px, weight 400--500, line-height around 1.5.

### Micro labels

11--12px, weight 500--600, slightly expanded letter spacing.

### Financial numbers

Use monospaced or tabular-number treatment.

Examples:

``` text
₹2,500
₹2,125 / unit
₹4,250 total
```

Prices should feel like **financial data**, not ordinary text.

------------------------------------------------------------------------

# 07 --- SHAPE LANGUAGE

Do not make every element a giant rounded rectangle.

Use hierarchy:

``` text
Outer stage       20–24px
Important cards   16–20px
Small controls    10–14px
Pills             only for status/category/provenance
```

Avoid decorative pill overload.

------------------------------------------------------------------------

# 08 --- SHADOWS & DEPTH

Depth should be subtle.

Prefer:

-   thin borders
-   soft shadows
-   layered surfaces
-   spacing

Avoid:

-   giant shadows
-   floating everything
-   excessive blur
-   glass panels
-   neon glow

The page should feel **physical and expensive**, not futuristic for its
own sake.

------------------------------------------------------------------------

# 09 --- TOP NAVIGATION

The top bar is not an admin toolbar.

It should feel like a premium storefront header.

Suggested:

``` text
AURA
Commerce

[ Fashion ] [ Electronics ] [ Home ] [ ... ]

                         ● Concierge active
```

Do not expose:

``` text
MODE: price_hesitation
```

or internal classifier terminology to buyers.

------------------------------------------------------------------------

# 10 --- PRODUCT NAVIGATION

Replace the raw HTML dropdown with a horizontal product rail.

Each item can contain:

``` text
[thumbnail]
Product name
₹price
```

Selected product:

-   stronger border
-   subtle elevation
-   crisp focus
-   slightly larger thumbnail
-   smooth hero transition

It should feel like **shopping**, not a dashboard filter.

------------------------------------------------------------------------

# 11 --- PRODUCT HERO

The product hero is the visual anchor.

The image should dominate.

Suggested composition:

``` text
┌──────────────────────────────────────────┐
│                                          │
│             PRODUCT IMAGE                │
│                                          │
│                                          │
│  CATEGORY                                │
│  Silk Designer Dress                     │
│  Handcrafted • Occasion Wear             │
│                                          │
│  ₹2,500                                  │
│  Listed price                            │
│                                          │
└──────────────────────────────────────────┘
```

Show:

-   category
-   name
-   concise descriptor
-   listed price
-   key specifications

Do not dump every specification above the fold.

------------------------------------------------------------------------

# 12 --- PRODUCT MEDIA

When real media exists, use it:

-   professional listing image
-   seller reality image
-   seller reality video
-   customer photo
-   customer video

Every item needs clear provenance:

``` text
SELLER LISTING
SELLER REALITY
CUSTOMER EXPERIENCE
```

Never imply customer media is seller-verified.

Never invent media.

If an asset does not exist, create an elegant empty state rather than
fabricated evidence.

------------------------------------------------------------------------

# 13 --- EVIDENCE WALL

This is one of the product's strongest visual differentiators.

Do not render a boring static list called "Quality Evidence".

Create an **Evidence Wall**:

``` text
REAL-WORLD EVIDENCE

[ Seller reality video ]
[ Customer photo       ]
[ Customer review      ]
[ Catalog specification]
```

Each item should communicate:

-   what it is
-   who supplied it
-   what it can support
-   whether AI is currently citing it

------------------------------------------------------------------------

# 14 --- EVIDENCE ACTIVATION WOW MOMENT

This is a critical interaction.

Before a trust question, evidence is quiet.

Buyer asks:

> "Are these pictures actually real?"

AI answers.

At the same time, the relevant evidence card should:

-   receive a subtle sapphire outline
-   brighten slightly
-   show `✓ CITED IN ANSWER`
-   optionally scroll into view
-   animate once, not continuously

The visual message is:

> **The AI did not just answer. It found the evidence supporting the
> answer.**

This is the **Confidence Becomes Visible** moment.

------------------------------------------------------------------------

# 15 --- EVIDENCE PROVENANCE

Every evidence item must visibly communicate origin.

Use a small provenance line such as:

``` text
Seller reality
Customer experience
Seller listing
```

Do not use misleading labels such as "Verified reality" unless the
underlying system actually supports that claim.

------------------------------------------------------------------------

# 16 --- AI CONCIERGE

The AI should feel like a **commerce concierge**, not ChatGPT embedded
in a website.

Header:

``` text
AURA CONCIERGE
● Active
```

Trust:

``` text
AURA CONCIERGE
Trust & evidence
```

Negotiation:

``` text
AURA CONCIERGE
Commercial review
```

Deal:

``` text
AURA CONCIERGE
Deal ready
```

Never expose internal classifier terminology.

------------------------------------------------------------------------

# 17 --- CHAT DESIGN

The conversation is the heart of the experience.

Do not use identical generic bubbles for everything.

Different message types should have different visual grammar.

### Buyer message

Simple, dark, compact.

### AI answer

More spacious.

Allow embedded:

-   evidence references
-   product facts
-   commercial cards
-   action controls

The AI message should sometimes become a **visual composition**, not
just text.

------------------------------------------------------------------------

# 18 --- AI ANSWER + EVIDENCE REFERENCE

Example:

``` text
AURA

The seller has provided a natural-light video of this dress,
and there is also a customer photo from a real purchase.

I can't guarantee the exact offline appearance, but these
references give you a better sense of the fabric and color.

[ Seller reality video ]   [ Customer photo ]
```

These references should connect visually to the Evidence Wall.

------------------------------------------------------------------------

# 19 --- QUICK ACTIONS

Quick actions must be contextual.

### Browsing

``` text
See real-world evidence
Ask about this product
```

### Trust state

``` text
Show cited evidence
Ask another question
```

### Negotiation

``` text
Try a counter
Change quantity
Accept offer
```

### Deal state

``` text
Review deal
Pay securely
```

Do not permanently display random action chips.

------------------------------------------------------------------------

# 20 --- NEGOTIATION EXPERIENCE

Negotiation should feel like a **commercial conversation**, not a
calculator.

When the buyer says:

> "₹2500 is too much. Can you do better?"

the workspace enters:

## COMMERCIAL REVIEW

Example:

``` text
┌─────────────────────────────────────────┐
│ COMMERCIAL REVIEW             ROUND 1/5 │
│                                         │
│ Listed price          ₹2,500            │
│ Your offer            ₹1,800            │
│                                         │
│ AURA COUNTER-OFFER                     │
│ ₹2,400 / unit                           │
│                                         │
│ Save ₹100 / unit                        │
│                                         │
│ [ Accept ]       [ Make another offer ] │
└─────────────────────────────────────────┘
```

Use actual backend responses.

**Never invent or calculate a final price in the frontend.**

------------------------------------------------------------------------

# 21 --- NEGOTIATION VISUAL RHYTHM

Make movement understandable:

``` text
LISTED
₹2,500
   ↓
YOUR OFFER
₹1,800
   ↓
COUNTER
₹2,400
```

Later:

``` text
ROUND 2 / 5
₹2,325
```

Do not show:

-   target price
-   reservation price
-   seller floor
-   BATNA
-   aspiration
-   private policy parameters

------------------------------------------------------------------------

# 22 --- QUANTITY AS A COMMERCIAL LEVER

Quantity deserves a premium visual treatment.

Example:

``` text
Quantity

[ − ]  2  [ + ]

2 units
₹2,125 / unit
₹4,250 total
```

If the backend returns a bulk tier:

``` text
2-unit rate
Better per-unit price
```

The buyer should feel:

> "Buying more created a better commercial outcome."

Do not reveal private seller economics.

------------------------------------------------------------------------

# 23 --- DEAL DESK

The Deal Desk is a signature component.

It must appear **inside the conversation flow**, not as a permanent
green box below the page.

Example:

``` text
┌────────────────────────────────────────────┐
│ COMMERCIAL DEAL DESK             ROUND 3/5 │
│                                            │
│ Silk Designer Dress                        │
│                                            │
│ 2 units                                    │
│ ₹2,125 / unit                              │
│                                            │
│ Total                                      │
│ ₹4,250                                     │
│                                            │
│ You save ₹750                              │
│                                            │
│ [ Accept ₹4,250 ]                          │
│ [ Make another offer ]                     │
└────────────────────────────────────────────┘
```

The card should feel like an evolving object.

------------------------------------------------------------------------

# 24 --- DEAL CARD TRANSFORMATION

Use one continuous visual object:

``` text
Conversation
      ↓
Negotiation card
      ↓
Agreement
      ↓
Validation
      ↓
Deal certificate
```

Before agreement:

``` text
COMMERCIAL REVIEW
```

After acceptance:

``` text
DEAL AGREED
```

After backend validation:

``` text
DEAL VALIDATED
```

Do not replace it with an unrelated card elsewhere.

------------------------------------------------------------------------

# 25 --- VALIDATED DEAL CERTIFICATE

This should feel like a digital receipt/certificate.

Example:

``` text
┌─────────────────────────────────────────────┐
│                                             │
│  ✓ DEAL VALIDATED                           │
│                                             │
│  Silk Designer Dress                        │
│                                             │
│  Quantity                         2          │
│  Unit price                 ₹2,125           │
│  Total                     ₹4,250           │
│                                             │
│  ─────────────────────────────────────────  │
│                                             │
│  Validated by AURA Commerce control plane   │
│                                             │
│  Price locked for this transaction          │
│                                             │
│  [ Pay ₹4,250 securely ]                    │
│                                             │
└─────────────────────────────────────────────┘
```

Do not expose implementation details such as hashes in the primary buyer
experience unless they provide actual buyer value.

------------------------------------------------------------------------

# 26 --- PAYMENT TRANSITION

The transition to payment should feel like the natural conclusion of
negotiation.

After clicking:

``` text
Pay ₹4,250 securely
```

show:

``` text
Preparing your locked deal...

✓ Deal validated
✓ Amount confirmed
✓ Razorpay order secured
```

Then launch the actual payment experience when implemented.

The interface should communicate:

> **The conversation has become a transaction.**

------------------------------------------------------------------------

# 27 --- SUCCESS STATE

Use a polished transaction completion state:

``` text
PAYMENT COMPLETE

₹4,250

Silk Designer Dress
2 units

Order confirmed

Razorpay order
••••••••

[ Continue shopping ]
```

Use restrained celebratory motion.

No confetti explosion.

------------------------------------------------------------------------

# 28 --- MOTION PRINCIPLES

Motion is important, but restraint is more important.

Use motion for:

-   state changes
-   evidence activation
-   product switching
-   negotiation updates
-   deal validation
-   payment transition

Avoid:

-   perpetual floating
-   bouncing cards
-   excessive gradients
-   spinning loaders everywhere
-   animation on every element

Desired motion:

**physical object + editorial transition**

Suggested timing:

``` text
120–180ms   micro interactions
200–300ms   component transitions
350–500ms   major state transitions
```

Respect `prefers-reduced-motion`.

------------------------------------------------------------------------

# 29 --- PRODUCT SWITCH TRANSITION

When switching products:

1.  Product rail selection changes.
2.  Product image transitions.
3.  Product identity updates.
4.  Evidence wall refreshes.
5.  Conversation context resets safely for the new product.
6.  Negotiation state does not leak across products.

Do not flash the entire page.

------------------------------------------------------------------------

# 30 --- LOADING STATES

Avoid generic:

``` text
Loading...
```

Use contextual copy:

``` text
Checking the product evidence…
Reviewing your offer…
Preparing your deal…
```

Loading copy describes the operation; it must never fabricate its
result.

------------------------------------------------------------------------

# 31 --- EMPTY STATES

Example:

``` text
No additional customer media yet

We only show evidence that is actually available
for this product.
```

Do not fill missing evidence with fake stock imagery.

------------------------------------------------------------------------

# 32 --- ERROR STATES

Errors should be calm and useful.

Better:

``` text
We couldn't complete that request.

Your current deal has not been changed.

[ Try again ]
```

For payment:

``` text
We couldn't prepare checkout.

Your validated deal is still unchanged.
```

Never imply payment occurred if it did not.

------------------------------------------------------------------------

# 33 --- RESPONSIVE DESIGN

Test at:

-   1440px
-   1280px
-   1024px
-   768px
-   390px

At smaller widths:

-   collapse the split stage intelligently
-   keep product identity visible
-   keep conversation dominant
-   make deal totals sticky when useful
-   avoid horizontal overflow
-   preserve readable financial numbers

------------------------------------------------------------------------

# 34 --- ACCESSIBILITY

Requirements:

-   keyboard navigation
-   visible focus states
-   semantic buttons
-   adequate contrast
-   alt text for meaningful images
-   accessible media controls
-   reduced-motion support
-   no color-only status communication

------------------------------------------------------------------------

# 35 --- DESIGN ANTI-PATTERNS

Absolutely avoid:

### Generic SaaS dashboard

Sidebar + metrics + cards + blue button + gray background.

### ChatGPT clone

Huge chat window with nothing else.

### Developer inspection UI

``` text
Mode: price_hesitation
validated_deal: true
round_number: 3
JSON
hash
```

### Permanent deal box

The deal should emerge from the conversation.

### Static evidence drawer

Evidence should activate when relevant.

### Rainbow AI UI

No neon rainbow gradients.

### Purple AI cliché

Avoid purple/pink "AI magic" styling.

### Glassmorphism everywhere

Do not use blur as a substitute for hierarchy.

### Excessive pills

A pill must communicate state or category.

### Fake evidence

Never fabricate product media, reviews, provenance or verification.

------------------------------------------------------------------------

# 36 --- INFORMATION DENSITY

The interface should be rich without being crowded.

Use:

-   whitespace
-   grouping
-   typography
-   visual hierarchy

rather than borders around everything.

A component does not need a box simply because it contains information.

------------------------------------------------------------------------

# 37 --- DESIGN STATES

The frontend should visually represent:

``` text
1. Browsing
2. Product Selected
3. Product Question
4. Trust Hesitation
5. Trust Evidence Active
6. Price Hesitation
7. Negotiation Active
8. Counter Offer Received
9. Buyer Counter / Accept
10. Deal Reached
11. Deal Validated
12. Payment
13. Payment Success
```

The visual language must evolve between states.

The UI should feel like a **living state machine**, not a static page.

------------------------------------------------------------------------

# 38 --- STATE VISUAL LANGUAGE

### Browsing

Quiet, editorial, product-first.

### Product selected

Product hero gains prominence.

### Product question

AI becomes visually active.

### Trust

Sapphire evidence language appears.

### Evidence active

Cited media activates.

### Price hesitation

Commercial review begins.

### Negotiation

Deal Desk appears.

### Counter offer

Financial values update with subtle motion.

### Acceptance

Interface becomes calmer and more decisive.

### Validation

Emerald validation state.

### Payment

Minimal, focused transaction state.

### Success

Quiet confidence.

------------------------------------------------------------------------

# 39 --- DESIGN TOKENS IN CODE

Centralize visual tokens.

Prefer CSS variables / design tokens:

``` css
--canvas
--surface
--ink
--muted
--border
--sapphire
--sapphire-soft
--amber
--amber-soft
--emerald
--emerald-soft
--radius-stage
--radius-card
--radius-control
--shadow-soft
--shadow-elevated
```

Do not scatter arbitrary visual values throughout `page.tsx`.

------------------------------------------------------------------------

# 40 --- COMPONENT ARCHITECTURE

If appropriate, extract:

``` text
AuraHeader
ProductRail
ProductHero
EvidenceWall
EvidenceCard
ConciergePanel
ChatStream
ChatMessage
EvidenceCitation
DealDesk
NegotiationProgress
QuantityControl
ValidatedDealCertificate
CheckoutPreview
PaymentSuccess
```

Do not create components purely for abstraction theatre.

Extract when it improves readability, state isolation, reuse, visual
consistency or testing.

------------------------------------------------------------------------

# 41 --- FRONTEND/BACKEND BOUNDARY

The design must never weaken the economic architecture.

The frontend may DISPLAY:

-   listed price
-   buyer offer
-   backend counter
-   quantity
-   total
-   savings
-   validation status

The frontend must NEVER become the authority for:

-   seller floor
-   target price
-   reservation price
-   BATNA
-   seller private policy
-   authorized discount
-   final economic decision

The backend remains authoritative.

------------------------------------------------------------------------

# 42 --- DATA-DRIVEN UI

Do not hardcode visual state when the backend already provides it.

Evidence activation should use:

``` text
assessment.evidence_ids_used
```

Negotiation display should use:

``` text
round_number
effective_unit_price
quantity
total_payable
```

Deal state should use the validated deal returned by the backend.

The frontend's job is:

> **Translate trustworthy backend state into beautiful visual state.**

------------------------------------------------------------------------

# 43 --- TRUST PRINCIPLE

The UI should reinforce:

> **Evidence-backed confidence, not absolute certainty.**

Never design badges that accidentally promise:

``` text
100% Authentic
Guaranteed Offline Match
Verified Reality
Guaranteed Durability
```

unless the underlying system actually supports that claim.

------------------------------------------------------------------------

# 44 --- NEGOTIATION PRINCIPLE

The visual experience should communicate:

> **Reward commitment, not desperation.**

Multiple units can receive better commercial treatment when authorized
by seller policy.

But:

-   do not expose seller floor
-   do not imply infinite negotiation
-   do not make the AI look desperate to close

The AI should feel like a **confident salesperson**.

------------------------------------------------------------------------

# 45 --- SALESPERSON PERSONALITY

AURA should feel:

-   helpful
-   commercially aware
-   calm
-   slightly assertive
-   transparent
-   confident

Not:

-   desperate
-   overly friendly
-   robotic
-   manipulative
-   submissive

Example:

> "For one piece, I can do ₹2,400. If you're taking two, I can give you
> the better unit rate."

------------------------------------------------------------------------

# 46 --- BUILDATHON WOW STRATEGY

Judges should understand the product in under 20 seconds.

The screen should answer:

### What is this?

AI commerce concierge.

### What does it do?

Helps you trust and negotiate a product.

### What is special?

Evidence becomes visible and negotiation becomes interactive.

### What happens next?

A validated deal becomes a payment.

Ideal demo:

``` text
PRODUCT
   ↓
"Are these pictures real?"
   ↓
EVIDENCE ACTIVATES
   ↓
"₹2500 is too much. What can you do?"
   ↓
DEAL DESK APPEARS
   ↓
"Can I take 2?"
   ↓
BETTER UNIT RATE
   ↓
"Done"
   ↓
VALIDATED DEAL
   ↓
PAY VIA RAZORPAY
```

------------------------------------------------------------------------

# 47 --- IMPLEMENTATION RULE FOR ANTIGRAVITY

Before changing code:

## STEP 1 --- Inspect

Inspect:

-   `frontend/app/page.tsx`
-   `frontend/app/globals.css`
-   `frontend/app/layout.tsx`
-   current API response shapes
-   current evidence data
-   current screenshots/browser behavior

Do not assume documentation matches runtime.

## STEP 2 --- Diagnose

Explain:

-   what is visually weak
-   what already works
-   what can be preserved
-   what needs redesign
-   where state already exists
-   where new state is actually necessary

## STEP 3 --- Implement incrementally

Use this order:

``` text
B1 — Commerce shell + visual hierarchy
B2 — Product hero + product rail
B3 — Concierge conversation
B4 — Evidence activation
B5 — Negotiation Deal Desk
B6 — Validated Deal → Payment transition
B7 — Final polish
```

Only advance after testing each stage.

------------------------------------------------------------------------

# 48 --- CRITICAL IMPLEMENTATION RULE

**Do not sacrifice functionality for visual design.**

Before visual refactors, preserve:

-   API contracts
-   session state
-   negotiation behavior
-   product isolation
-   evidence provenance
-   validation behavior
-   payment guards

If a visual change requires a logic change, stop and explain why.

------------------------------------------------------------------------

# 49 --- HARD TESTING REQUIREMENT

After every implementation step, Antigravity MUST hard test.

Do not report only TypeScript/build success.

Minimum browser scenarios:

### A --- Fresh page

-   product loads
-   exactly one greeting
-   no console errors

### B --- Product question

-   response appears
-   chat remains intact
-   no fake evidence

### C --- Trust

Ask:

> "Are these pictures real?"

Verify:

-   grounded answer
-   cited evidence activates
-   only relevant evidence highlights

### D --- Negotiation

Use:

> "Can I get it under 1900?"

Then:

> "Ok 1800"

Then:

> "Can you do better if I take 2?"

Verify:

-   correct rounds
-   actual backend prices
-   quantity reflected
-   total = unit price × quantity

### E --- Acceptance

Use:

> "Ok done"

Verify active counter is accepted.

Also verify a fresh-session "Ok done" does NOT manufacture a deal.

### F --- Product isolation

Start negotiation on Product A, switch to Product B.

Verify:

-   old negotiation does not leak
-   evidence belongs to Product B
-   price belongs to Product B

### G --- Browser quality

Check:

-   console errors
-   runtime exceptions
-   overflow
-   broken images
-   mobile layout
-   loading states

### H --- Security/economic regression

Run the existing backend regression and adversarial tests.

------------------------------------------------------------------------

# 50 --- VISUAL QA CHECKLIST

Antigravity must inspect the page visually, not only programmatically.

Ask:

### Hierarchy

Can I immediately see the product? Can I immediately see where to talk
to the AI? Can I immediately understand the commercial state?

### Polish

Do any elements look like default HTML? Do any cards look pasted
together? Are borders overused? Are buttons consistent?

### Typography

Are prices visually strong? Are headings properly hierarchical? Is
secondary information genuinely secondary?

### Motion

Does anything jump? Does anything animate excessively? Do state
transitions feel intentional?

### Trust

Can I tell who supplied an evidence item? Does cited evidence visually
connect to the AI answer?

### Commerce

Does negotiation feel like a real commercial interaction? Does the final
deal feel trustworthy?

### Demo

Would a judge understand the product from the screen alone?

------------------------------------------------------------------------

# 51 --- WHAT "CRAZY GOOD" MEANS HERE

"Crazy" does NOT mean:

-   more gradients
-   more animation
-   more colors
-   more cards
-   more AI terminology

"Crazy good" means:

> **Every visual element has a reason.**

The product should feel unusually coherent.

A judge should think:

> "This looks like a real product."

Then:

> "Wait --- the evidence actually activates when the AI cites it."

Then:

> "And now the chat has turned into a negotiation desk."

Then:

> "And that deal is validated before Razorpay."

That sequence is the wow factor.

------------------------------------------------------------------------

# 52 --- FINAL CREATIVE DIRECTOR TEST

Before calling the frontend done, ask:

> If I remove all backend labels and technical terminology, does this
> still look like a premium commerce product?

If no: redesign.

Then:

> Does the visual interface make the AI's intelligence observable?

If no: improve evidence activation, contextual UI, or negotiation
visualization.

Then:

> Does the final deal feel more trustworthy because of the interface?

If no: improve the validation and transaction transition.

------------------------------------------------------------------------

# 53 --- FINAL DESIGN THESIS

AURA is not:

> a chatbot with a product page.

AURA is:

> **a commerce workspace where uncertainty becomes evidence,
> conversation becomes negotiation, and negotiation becomes a validated
> transaction.**

The interface must make that transformation visible.

``` text
DISCOVER
   ↓
UNDERSTAND
   ↓
TRUST
   ↓
NEGOTIATE
   ↓
AGREE
   ↓
VALIDATE
   ↓
PAY
```

### Design it as one story, not seven disconnected screens.

------------------------------------------------------------------------

# 54 --- NON-NEGOTIABLES

1.  Premium commerce, not SaaS dashboard.
2.  No neon/purple/glassmorphism aesthetic.
3.  Product imagery must be visually important.
4.  AI must be integrated into the product experience.
5.  Evidence must have visible provenance.
6.  Cited evidence must visibly activate.
7.  Negotiation must become a visual Deal Desk.
8.  Quantity must visibly affect commercial presentation.
9.  Deal confirmation must emerge from the conversation.
10. Validation must feel like a real trust boundary.
11. Payment must feel like the natural final step.
12. No seller-private economic values in the UI.
13. No fabricated evidence.
14. Backend remains the economic authority.
15. Preserve existing working architecture.
16. Implement incrementally.
17. Hard-test every step in a real browser.
18. Never accept "tests pass" as the only proof of quality.

------------------------------------------------------------------------

# END --- AURA DESIGNER.md
