# Crates: Synthesis

**Status:** Canonical parent document. Every other artifact in this set derives from this one.
**Date:** 21 July 2026
**Naming:** All product names below are provisional pending trademark search.

---

## 0. Purpose of this document

This is the source of truth for what the company is. When any other document in this set contradicts this one, this one is correct and the other should be updated. When a claim in a pitch, an application, or a conversation does not appear here, it has not been decided yet.

The failure mode this document exists to prevent is drift: the same idea described five slightly different ways in five places, until nobody including the founder can state the thing in one sentence.

---

## 1. The thesis

Creative ideas are fragile. They arrive as a feeling that is barely held, and they are destroyed by friction. The interval between having a musical idea and hearing it played back is the interval in which most musical ideas die. This is not a metaphor and it is not a productivity complaint. An idea lost to friction is not recoverable in its original form; it can be approximately retraced and it will never feel the same.

Almost every tool currently being built with AI in music attacks the wrong problem. Generative music tools attempt to supply creativity, which was never scarce. What is scarce is the ability to transcribe creativity fast enough that it survives.

**The correct use of AI in music is the elimination of transcription friction, not the substitution of creative judgment.**

This has a strong consequence that defines the entire product: the user must still know what music is. Nobody can ask for a four-bar loop with the kick on 1 and 3 without understanding bars, beats, and subdivision. The tool does not pull the creative weight. It removes the obstacle between the idea and the playback.

And it follows from that thesis that the tool should be designed to be outgrown. Success is a user becoming fluent enough that typing a prompt is more friction than doing it themselves. The product is aiming at its own obsolescence for each individual user, and it should say so publicly.

---

## 2. Who this is for

**Independent artists, exclusively.**

Not as a market segment chosen for tractability, though it is also that. As the actual constituency. The company exists to serve independent artists and the founder holds no personal ambition to profit from it.

Two user populations sit inside that:

**Songwriters with no production ability.** People who can write but cannot get what they write out of their head. They currently have three options: learn production over years, pay a producer they cannot afford, or abandon the work. This is the early adopter population and it is the demo subject.

**Producers.** Who are, in the overwhelming majority of cases, songwriters performing composition and arrangement while being classified and compensated as technicians. They are not the early adopters of an education product, since they already know how to produce. They are the constituency of the industry argument in section 6, and they are the primary contributors of session files.

Explicitly out of scope: major labels, major label catalog, and any product decision made to accommodate either.

---

## 3. Why this is one company and not four

The unifying insight is not thematic. It is architectural.

**The session file is the shared substrate.** Every surface of this company reads from or writes to the same object.

| Surface | Relationship to the session file |
|---|---|
| Crates Studio (DAW assistant) | Writes to it. Indexes the user's own local corpus of them. |
| Crates Studio (teaching mode) | Reads its state to detect learner progress. |
| Crates Library (study corpus) | Ingests uploaded sessions from artists as the study material. |
| Crates (discovery) | Derives features from the corpus to enrich its parameter space. |
| Split sheets | Derives contribution provenance from session history. |
| Crates Registry | The only component not built on sessions. |

A company built on masters would need four separate data pipelines and a machine learning problem at each one. A company built on session files has one data model and four front doors. This is why it is one company, and it is the answer to give when someone says the scope is too broad.

---

## 4. The four surfaces

### 4.1 Crates Studio: the assistant

Natural language to printed MIDI inside Ableton Live, via the Live Object Model.

Design commitments:
- The language model never emits DAW commands directly. It emits a validated JSON intermediate representation, and a deterministic renderer converts that into API calls. This gives schema validation, replayability, model portability, and a debuggable failure mode.
- A local deterministic grammar handles common grid requests without any network round trip. The entire premise is friction removal; a two second latency on "kick on 1 and 3" violates the product.
- A snapshot layer wraps every mutation, because Live's undo stack does not capture API edits.
- Voice input over typing, for the same reason as the local grammar.

### 4.2 Crates Studio: the teaching mode

Errorless learning, drawn from applied behavior analysis, applied to digital audio workstation skill acquisition. This is specified in full in `pedagogy.md` and it is the single most defensible asset in the company.

The short version: the tool teaches by constraining the environment so that the correct action is the available action, then systematically fading that constraint according to a defined prompt hierarchy until the learner performs independently. The fading protocol is the product roadmap. The Hinge principle, formalized: the exit criteria are written down and measurable.

### 4.3 Crates Library: the study corpus

Artists upload complete session projects, not finished masters.

This choice removes two entire problem classes:
- **No source separation.** The stems are already separate; they are tracks.
- **No transcription inference.** The MIDI is ground truth, not a guess. Every note position, velocity, and length is exact.

Third-party audio assets (sample pack one-shots, Splice loops, purchased libraries) are stripped at ingestion and replaced with neutral proxy sounds. The student receives the placement, not the sound, and A/Bs the proxy reconstruction against the artist's master. This is both the legally necessary behavior and the pedagogically correct one: the lesson is where the notes are, not which snare it was.

Closed loop: material can only enter a user's DAW through the service, and the plugin refuses to analyze anything not carrying a service tag. This is how provenance is established, and it is why the "how do we know they obtained it legally" problem does not arise.

### 4.4 Crates: discovery

The existing product. No search, no genre picking, no global taste profile, fully isolated journeys, an algorithm that rewards new likes on unheard music.

Session data enters as **additional parameters in an existing feature space** alongside Essentia audio analysis and Music Genome Project-inspired attributes. It is not a replacement predictor and no claim is made that production similarity predicts listener taste. That is an open empirical question (see `crates-internal/risk-register.md`, R-19).

The scaling move, and the more important one: train a model to predict session-derived attributes from audio alone, using the subset of tracks that have both. Then apply it to the whole catalog. This turns a few thousand uploaded sessions into a better analyzer for millions of tracks that will never have a session uploaded, and it is the answer to the cold start problem.

### 4.5 Connective tissue

**Split sheets.** Auto-generated contribution provenance from session history. Who was present, what was added when, which musical elements originated where, produced as a draft split sheet before anyone leaves the room. This attacks the mechanism by which producers lose publishing, which is that nothing is documented at the moment of creation and the conversation happens months later controlled by the party with leverage.

**Crates Registry.** An artist-contributed directory of vendors, venues, and tour support: who actually paid on time, who honored the guarantee. This data does not exist anywhere and cannot be scraped, which is exactly why it is worth having. Hosted, never rewritten. No contribution incentive, because paying for contributions creates an incentive to fabricate them.

---

## 5. The moat

**A corpus of how independent music is actually made, at the decision level.**

Nothing like this exists. Spotify has listening behavior. Shazam has fingerprints. Splice has sample usage, which is the nearest existing thing and a shadow of it. Hooktheory has human-annotated harmony for a few thousand songs. Nobody has session files at scale, because nobody has ever given artists a reason to hand them over.

The corpus supports, in descending order of confidence:
1. An education library with ground-truth material. Direct, requires no unproven inference.
2. Collaboration matching. "Find people who work the way I do" maps to production similarity without passing through taste.
3. A research asset on creative process. The strongest grant and fellowship narrative available.
4. Discovery feature enrichment. Real, but unvalidated, and the weakest claim of the four. Do not lead with it.

**The corpus exists only because the terms are artist-favorable.** This is the alignment argument and it should be the core of every investor conversation: protective terms are not a mission cost being absorbed. They are the mechanism by which the asset comes into existence at all. A competitor with worse terms does not get a smaller corpus; they get no corpus.

---

## 6. The industry position

**Claim:** Producers are songwriters. Composition credit should follow composition, wherever in the workflow it occurs. The overwhelming majority of what is filed as "production" in contemporary popular music, and especially in rap and hip-hop, is melodic, harmonic, and structural composition. The beatmaker designation is doing economic work against people who wrote the record.

**What is true and defensible:** the substance above.

**What is a bet, not a mechanism:** the theory that lowering the barrier to arrangement will cause an observable decline in quality, which the market will correctly attribute to absent producers, thereby raising producer status. The historical base rate argues against it. Drum machines displaced session drummers and the market did not respond by recognizing session drummers as irreplaceable; the aesthetic simply adapted to the tool and entire genres organized around the new sound.

The rebuttal, which must be delivered in one sentence when this is raised: **drum machines replaced a performance function; this replaces a transcription function and leaves composition entirely intact.** The producer contribution being defended is compositional, and composition is precisely what the tool does not do.

This is logged as an accepted bet in the risk register. The company is not built on it.

**What the company will and will not do:**

| Will | Will not |
|---|---|
| Publish aggregate data on what splits actually look like | Provide a forum where producers converge on shared terms |
| Offer contract templates as options individuals select | Recommend a standard that everyone adopts |
| Educate, document, and make the case with evidence | Organize, coordinate, or facilitate collective refusal |
| Build split sheet infrastructure | Publish a public page arguing why antitrust law does not apply to us |

The legal reasoning for the right-hand column is in `crates-internal/legal-brief.md`, section 6. In short: coordinated refusal by independent contractors is a group boycott, the leading case went badly for a far more sympathetic set of plaintiffs, and a platform that provides the coordination mechanism can be pulled in as the hub even without intending to organize anything. The split sheet infrastructure does more real work than the movement anyway, because it changes documentation at the moment of creation rather than requiring anyone to have an epiphany.

---

## 7. Structure and commitments

**Entity.** Delaware public benefit corporation, taxed as a C corporation. To be formed before the first session upload, because a sole proprietorship places platform liability directly on personal assets. PBC status is understood to be primarily a director liability shield and a signal, not enforceable protection for artists; the teeth are contractual.

**Artist rights.** Artists license, they do not assign. The license terminates automatically on change of control unless the acquirer affirmatively re-executes the original terms. This is self-enforcing: the corpus is worthless to a buyer who will not honor the commitments, so the company never becomes attractive to the wrong buyer. It also survives bankruptcy better than a covenant, because there is no unencumbered asset to sell.

**No generative music.** Binding covenant in the artist agreement, surviving change of control. Not a marketing claim, not a term-of-service line that can be amended. This permanently forecloses an adjacent market and that is the entire point; a commitment that costs nothing signals nothing.

**Founder economics.** The founder takes salary for labor and does not seek personal profit from equity appreciation. Equity is held to prevent extraction, not to capture upside. Investors may take normal venture returns; a few points of dividend to people who funded the thing is a different order of extraction from what independent artists currently absorb under pro-rata streaming pooling.

**Conflict of interest.** The founder is an independent artist who will release music. The conflict is fenced structurally rather than solved by renouncing profit: founder-released music is excluded from algorithmic promotion in Crates and excluded from the Library payout pool, and this is disclosed prominently.

**Transparency.** Annual public release of full financials: revenue in, and where it goes. Investor agreement to this is obtained at entry, because it is competitive disclosure and much easier to establish as a founding practice than to introduce later.

**Buyback.** If the option to repurchase outside equity is wanted, it is negotiated at entry as a defined formula (a multiple of invested capital, or a valuation formula tied to revenue), never as an open-ended commitment to pay "above market rate," which is an unbounded liability exercisable at the holder's most advantageous moment.

**Succession.** Estate planning executed alongside formation. Change-of-control reaffirmation protects the artists; a will or trust directing the shares protects everything else from intestate succession.

---

## 8. What is decided and what is open

### Decided

- Ableton Live is the integration target. Not FL Studio (see `technical-architecture.md` section 6 for the API analysis). REAPER is an internal prototyping bench only, never a shipped or demoed surface.
- Sessions, not masters. Upload model, not analysis-of-recordings model.
- Independent artists only. No major label catalog, at any stage.
- Result detection over input blocking for v1 of the teaching mode.
- Passive host posture with DMCA section 512 safe harbor from day one.
- Crates as the company name, with component naming that never contains the word "AI."
- No contribution incentive on the Registry.

### Open

- Whether production-decision similarity carries signal for listener taste. See risk register R-19. NOTE 2026-07-25: this is currently BLOCKED, not merely open. The experiment needs multiple listeners to correlate and the service has one user.
- Entity conversion path: whether steward ownership or cooperative conversion is a real destination or a stated intention. Depends on financing structure chosen at entry.
- Whether OS-level input blocking is ever built, or whether environmental constraint is sufficient permanently.
- Pricing. Entirely undetermined. No financial model should be produced until there are users.
- Whether the Library launches with bring-your-own-session only, or with an opt-in shared catalog from the start.

---

## 9. The sequence

Nothing in this section is a commitment to timing. It is a dependency order.

1. **The `.als` crawler.** Days of work, no permission required, produces the "shape of your taste" artifact. This is the cheapest proof that any of it is real and it is the demo that makes producers feel something.
2. **The offline feature experiment.** Determines whether the discovery claim survives. A weekend that either justifies or redirects years.
3. **The assistant.** AbletonOSC, the intermediate representation, the renderer, the snapshot layer, the local grammar.
4. **The teaching mode, one lesson.** Environmental constraint plus result detection. Sufficient for the demo.
5. **The demo.** Songwriters who believe they cannot produce, finishing a track on camera. This works completely without OS-level blocking; nobody watching can tell the difference. The demo is the recruiting instrument for the systems engineer, not the reverse.
6. **Formation, counsel, artist agreement.** Before any upload from anyone other than the founder.
7. **The Library.**

---

## 10. The one thing to remember

If the whole document had to collapse to a single sentence for a room full of skeptics:

> We are building the infrastructure independent artists have never had, on a dataset nobody else can get, because we are the only ones offering terms that make artists willing to hand it over.
