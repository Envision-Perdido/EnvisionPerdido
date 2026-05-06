# Play Perdido — Data Model & Taxonomy Strategy
## Events + Adventures + Music + Food Discovery System

---

# 1. Purpose

This document defines the content architecture for Play Perdido so the site stays organized, scalable, searchable, and discovery-first.

Play Perdido is not just a calendar. It is a connected local discovery system built around four related content types:

1. **Events** — time-based things happening in Perdido
2. **Adventures** — anytime experiences and places to explore
3. **Music** — live music, musicians, venues, and schedules
4. **Food** — food trucks, restaurants, and local flavor connections

The goal is to make all of these systems work together without turning the site into a messy directory.

---

# 2. Core Content Architecture

## Primary Content Types

### 1. Events

Use for:
- festivals
- live music nights
- community events
- markets
- classes
- public gatherings
- family activities
- recurring local happenings

Primary behavior:
- date/time driven
- filterable
- EventON-powered

---

### 2. Adventures

Use for:
- trails
- beaches
- boardwalks
- kayak routes
- wildlife viewing
- historic spots
- scenic places
- quiet places
- free explore-on-your-own experiences

Primary behavior:
- evergreen
- editorial/guide-style
- connected to nearby events and food

---

### 3. Music Profiles

Use for:
- local musicians
- bands
- regular performers
- venues with music
- recurring music schedules

Primary behavior:
- connected to events
- discoverable by artist, venue, genre, and date

---

### 4. Food / Local Flavor

Use for:
- food trucks
- restaurants
- markets
- event-adjacent food options
- cross-links to PerdidoFoodTrucks.com

Primary behavior:
- supports events and adventures
- helps users stay local

---

# 3. Content Relationship Model

## Events connect to:
- category
- venue/location
- date/time
- organizer
- musician/artist if applicable
- nearby adventures
- nearby food
- featured status
- source/origin

## Adventures connect to:
- location
- adventure type
- difficulty
- cost
- best time of day
- nearby events
- nearby food
- related adventures

## Music connects to:
- musician/artist profile
- venue
- scheduled events
- genre
- recurring pattern
- event category: Live Music

## Food connects to:
- food truck or restaurant profile
- location
- schedule if available
- nearby events
- nearby adventures

---

# 4. Recommended WordPress Structure

## Events

Recommended system:
- EventON custom post type / event system

Event data should remain in EventON unless there is a strong reason to duplicate.

---

## Adventures

Recommended system:
- Custom post type: `adventure`

Why:
- Adventures are not normal blog posts.
- They need their own taxonomy and template.
- They are evergreen, structured content.

---

## Music Profiles

Recommended system:
- Custom post type: `musician` or `artist`

Optional if initial scope is small:
- Start with EventON categories + custom fields
- Add musician CPT later when volume grows

Best long-term:
- Use a musician/artist profile model so schedules can connect to performers.

---

## Venues / Locations

Recommended system:
- Reuse EventON location fields when possible.
- Consider a shared `venue` taxonomy or CPT if venues become important across Events, Adventures, Food, and Music.

Important:
Do not create duplicate venue data in multiple systems unless required.

---

## Food

Recommended system:
- Connect to existing PerdidoFoodTrucks.com where possible.
- Avoid duplicating the full food truck directory unless there is a strategic reason.

Use Play Perdido for:
- previews
- cross-links
- event-adjacent food recommendations

---

# 5. Event Taxonomy Strategy

## Primary Event Categories

Use user-facing categories, not internal organization categories.

Recommended:

- Live Music
- Family Friendly
- Food & Drink
- Markets & Makers
- Community
- Arts & Culture
- Beach & Water
- Nature & Outdoors
- Free
- Classes & Workshops
- Nightlife
- Seasonal

---

## Category Rules

### Categories should answer:
“What kind of thing is this?”

Examples:
- Live Music
- Family Friendly
- Market
- Food & Drink

### Categories should NOT answer:
“Who submitted this?”
“Which organization owns this?”
“Is this a chamber event?”
“Is this a member event?”

Those belong in internal metadata, not public categories.

---

# 6. Event Tags Strategy

Tags should support discovery but not become clutter.

Recommended tags:

- Free
- Kid-friendly
- Rainy day
- Pet friendly
- Outdoor
- On the water
- Sunset
- Recurring
- Local favorite
- Date night
- Low-cost
- Educational
- Volunteer
- Music
- Food available

---

## Tag Rules

Use tags for attributes, not categories.

Good:
- Free
- Pet friendly
- Outdoor

Bad:
- Chamber event
- Member event
- Networking
- Pensacola
- Gulf Shores

---

# 7. Adventure Taxonomy Strategy

## Adventure Types

Recommended taxonomy: `adventure_type`

Values:
- Trail
- Boardwalk
- Beach
- Bayou
- Kayak / Paddle
- Wildlife
- Birding
- Historic
- Scenic Spot
- Sunset Spot
- Stargazing
- Quiet Place
- Free Adventure

---

## Adventure Attributes

Recommended taxonomy or structured fields:

- Free
- Easy
- Family friendly
- Dog friendly
- Good for sunrise
- Good for sunset
- Good in summer
- Good in cooler weather
- Buggy season warning
- Accessible
- Short walk
- Long walk
- Water access
- Photography spot

---

## Adventure Regions / Areas

Recommended:
- Perdido Key
- Inner Perdido
- Big Lagoon
- Tarkiln Bayou
- Johnson Beach
- Perdido Bay
- Intercoastal / Intracoastal
- Gulf Beach
- Bayou / Marsh

Use local region names that users understand.

---

# 8. Music Taxonomy Strategy

## Music Event Category

All music performances should use:
- Category: Live Music

## Music Tags

Recommended:
- Acoustic
- Country
- Rock
- Blues
- Singer-songwriter
- Worship / Gospel
- Jazz
- Local artist
- Outdoor venue
- Dinner music
- Late night
- Family friendly

## Musician / Artist Fields

If using musician profiles:

- Artist name
- Genre(s)
- Home area
- Bio
- Photo
- Website/social links
- Booking contact if public
- Upcoming shows
- Regular venues

## Venue Fields for Music

- Venue name
- Address
- Indoor/outdoor
- Food available
- Family friendly
- Waterfront
- Typical music nights
- Website/social

---

# 9. Food / Local Flavor Taxonomy Strategy

## Food Categories

Recommended:
- Food Truck
- Restaurant
- Coffee / Dessert
- Seafood
- Casual Dining
- Waterfront Dining
- Market Vendor
- Event Food

## Food Tags

Recommended:
- Kid friendly
- Outdoor seating
- Pet friendly
- Local favorite
- Quick bite
- Late night
- Near beach
- Near trail
- Near event venue

## Food Integration Rule

Food should usually appear as:
- “Nearby food”
- “Food trucks today”
- “Eat local after this”
- “Pair this adventure with…”

It should not overpower the event/adventure experience.

---

# 10. Location Strategy

Location is one of the most important filters because Play Perdido’s mission is geographic integrity.

## Location Fields

Every event/adventure should have:

- display location name
- street address if applicable
- region/area
- latitude/longitude if available
- inside Perdido? yes/no
- distance from Perdido center or key anchor locations if useful

---

## Geographic Integrity Rules

Include if:
- located in Perdido
- directly serves Perdido
- begins/ends in Perdido
- is locally relevant and clearly connected to Perdido

Exclude or downgrade if:
- primarily in Pensacola
- primarily in Gulf Shores / Orange Beach
- a generic regional event
- mainly promotes leaving Perdido

---

## Borderline Handling

Some nearby regional attractions may be relevant, but they should not dominate.

Use labels:
- “Nearby”
- “Regional”
- “Day trip”

Do not mix them into core Perdido-first feeds unless intentionally included.

---

# 11. Source / Origin Metadata

Every event should track where it came from.

Recommended internal fields:

- source type
  - scraped
  - submitted
  - manually created
  - musician schedule
  - partner feed
- original source URL
- submission contact
- review status
- confidence score
- last updated
- cleanup needed
- approved by

This should be internal, not public-facing.

---

# 12. Moderation Workflow Taxonomy

## Event Status

Recommended statuses:

- Draft
- Needs Review
- Approved
- Rejected
- Needs More Info
- Expired
- Featured
- Sponsored

## Review Flags

Recommended flags:

- Out of area
- Spammy / promotional
- Private event
- Not enough details
- Duplicate
- Needs better image
- Needs title cleanup
- Needs category review

---

# 13. Featured / Curation Model

## Featured Should Be Separate From Category

An event can be:
- Live Music
- Family Friendly
- Featured

Featured is a curation layer, not a category.

## Recommended Featured Fields

- featured yes/no
- featured section
  - Top Picks
  - This Weekend
  - Live Music Tonight
  - Family Picks
  - Free Things To Do
- featured priority
- featured start/end date
- sponsored yes/no
- sponsor label if applicable

---

# 14. SEO Structure

## Events

Event pages should target:
- event name
- date
- venue
- Perdido location language
- category language

Example:
“Live Music at [Venue] in Perdido — Friday Night”

---

## Adventure Pages

Adventure pages should target:
- place name
- activity
- Perdido / Perdido Key / Pensacola area terms where natural
- free things to do
- nature trails
- boardwalks
- bayou / coastal forest

Example:
“Tarkiln Bayou Boardwalk — A Free Nature Adventure Near Perdido”

---

## Category Pages

Category pages should target:
- Live Music in Perdido
- Family Events in Perdido
- Free Things to Do in Perdido
- Nature Trails Near Perdido
- Food Trucks in Perdido

---

# 15. URL Strategy

Keep URLs human-readable and stable.

## Suggested URL Patterns

Events:
- `/events/event-name/`

Category pages:
- `/events/live-music/`
- `/events/family-friendly/`
- `/events/this-weekend/`

Adventures:
- `/adventures/tarkiln-bayou-boardwalk/`
- `/adventures/johnson-beach-stargazing/`

Adventure categories:
- `/adventures/trails/`
- `/adventures/free/`
- `/adventures/bayou/`

Music:
- `/live-music/`
- `/musicians/artist-name/` if profiles are used

Food:
- `/food-trucks/` or cross-link to PerdidoFoodTrucks.com

---

# 16. Internal Linking Strategy

The site should feel interconnected.

## On Event Pages

Show:
- nearby adventures
- nearby food
- same-category events
- venue page if available
- more this weekend

## On Adventure Pages

Show:
- events nearby
- live music tonight
- food nearby
- related adventures
- family-friendly or free tags

## On Live Music Pages

Show:
- venues
- musician profiles
- food nearby
- weekend picks

## On Food Sections

Show:
- events nearby
- adventures nearby
- today’s schedule if available

---

# 17. Search Strategy

Search should support natural user intent.

Users may search:
- “live music”
- “kids”
- “free”
- “beach”
- “Tarkiln”
- “food trucks”
- “tonight”
- “Blue Angels”
- “market”
- “rainy day”

Search should prefer:
1. current/upcoming events
2. relevant adventure pages
3. live music profiles
4. food/local flavor content

Expired events should not dominate search results.

---

# 18. Empty State Strategy

Empty states should be helpful and branded.

## Example: No Events Today

Instead of:
“No events found.”

Use:
“Nothing listed for this filter right now, but Perdido is never empty. Try This Weekend, Live Music, or explore an Adventure.”

## Example: No Live Music Tonight

“Looks quiet tonight. Check this week’s lineup or find a local spot to explore.”

## Example: No Category Events

“We’re still building this category. Know of something happening in Perdido? Submit it for free.”

---

# 19. Data Quality Rules

## Event Titles

Clean raw titles into useful titles.

Bad:
“Blue Angels Practice . Skip the Traffic . Skip the Crowds . Watch from the Water”

Better:
“Watch Blue Angels Practice from the Water”

---

## Event Descriptions

Descriptions should include:
- what it is
- who it is for
- why it matters
- practical details

Avoid:
- marketing spam
- all caps
- vague hype
- raw scraped fragments

---

## Images

Priority order:
1. real local photography
2. event-specific images
3. venue images
4. category fallback image
5. styled placeholder

Do not let missing images break visual hierarchy.

---

# 20. Governance Rules

## New Categories

Before adding a new category, ask:
- Will users understand this?
- Does it help filtering?
- Will it have enough content?
- Is this actually a tag instead?
- Is this internal metadata instead?

## New Tags

Before adding a new tag, ask:
- Will users filter by this?
- Does it describe an attribute?
- Is it too specific?
- Will it create clutter?

## New Content Types

Before adding a new CPT, ask:
- Is this structurally different?
- Does it need its own template?
- Does it need its own fields?
- Can it be handled as a category or tag instead?

---

# 21. Recommended MVP Taxonomy

## Launch Categories

Start with:

- Live Music
- Family Friendly
- Food & Drink
- Markets & Makers
- Community
- Beach & Water
- Nature & Outdoors
- Free

## Launch Adventure Types

Start with:

- Trails & Boardwalks
- Beaches
- Bayou & Water
- Wildlife & Birding
- Free Adventures
- Sunset & Stargazing

## Launch Tags

Start with:

- Free
- Kid-friendly
- Outdoor
- Pet friendly
- On the water
- Local favorite
- Recurring
- Rainy day

Keep launch taxonomy intentionally lean.

---

# 22. Codex Worker Guidance

When building anything related to data or taxonomy, Codex workers should:

- avoid creating duplicate taxonomy systems
- reuse existing categories where possible
- keep user-facing taxonomy simple
- keep internal metadata separate
- preserve geographic integrity
- connect Events and Adventures wherever useful
- support future partner embeds
- document assumptions

---

# 23. Anti-Patterns to Avoid

Do not:

- recreate a chamber directory
- use member status as a public category
- mix Pensacola/Gulf Shores content into Perdido-first feeds
- create too many categories too early
- let tags become random
- allow expired events to dominate
- treat Adventures like generic blog posts
- treat Food as unrelated to Events and Adventures
- build isolated content silos

---

# 24. Success Criteria

The data model is successful if:

- users can quickly find what to do
- events and adventures reinforce each other
- live music becomes easy to discover
- food discovery supports local spending
- partner widgets can reuse clean feeds
- future growth does not create taxonomy chaos
- Play Perdido feels like one connected local guide

---

# 25. Final Principle

> The taxonomy should disappear.

Users should not feel categories, post types, or plugin systems.

They should feel:

- “What can we do today?”
- “Where should we go next?”
- “What else is nearby?”
- “I didn’t realize Perdido had this much.”

That is the purpose of the data model.
