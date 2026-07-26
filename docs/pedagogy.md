# Crates Studio: Pedagogical Specification

**Status:** Core intellectual asset. Derives from `synthesis.md`.
**Date:** 21 July 2026

---

## 0. Why this document exists

Every other component of this company could be reproduced by a well-funded competitor within eighteen months. The integration layer is open source. The corpus is a matter of trust and time. The discovery algorithm is a research bet.

This document is the part that cannot be copied by someone who has not done the work, because it requires a discipline that essentially nobody in music technology has training in. It is the difference between a chat interface bolted to a DAW and an instrument of instruction.

It is also, incidentally, the strongest grant and fellowship narrative available to the company, and the most credible answer to "why you."

---

## 1. The problem being solved

Learning music production has an unusually brutal acquisition curve, for reasons that are structural rather than intellectual:

**Every early action is failable in a non-obvious way.** A beginner who wants a drum loop must first create a track of the correct type, then locate an instrument in a browser containing thousands of items, then load it correctly, then create a clip, then open an editor, then set a grid resolution, then place notes at positions defined by a mental model of musical time they may not yet have. Each step has multiple wrong outcomes and most produce silence rather than an error message.

**Silence is the worst possible feedback signal.** It does not indicate which of eight prior steps failed. The learner cannot localize the error, so the error teaches nothing.

**The reinforcer is delayed past the point of usefulness.** The thing that makes music learning self-sustaining is hearing something good. Traditional instruction places forty minutes of failure-dense procedure between the learner and their first reinforcer, and the majority of learners quit inside that interval.

**Most instruction is delivered in the wrong modality.** Video tutorials require the learner to hold a procedure in working memory while executing it in a different window. This is a working memory task disguised as a motor learning task, and it fails for the same reason reading assembly instructions in another room fails.

The result is a population, very large, of people who can write music and have concluded they cannot produce it. They have not concluded this from a lack of aptitude. They concluded it from an acquisition procedure that generates dense early failure with uninformative feedback.

---

## 2. Why errorless learning

Errorless learning is a family of instructional procedures from applied behavior analysis designed to minimize learner errors during skill acquisition, developed originally for teaching populations for whom trial-and-error methods produced failure, frustration, and escape behavior rather than learning.

The core insight is that **an error is not neutral information.** In acquisition, an error is a practiced response. It gets reinforced by whatever follows it, it competes with the correct response for retrieval, and it produces emotional side effects (frustration, avoidance, escape) that suppress future engagement with the task.

Errorless procedures arrange the instructional environment so that the correct response occurs on the first trial and every trial, and then systematically withdraw the arrangement.

**The mechanism is not physical prevention.** This is the most commonly misunderstood point and it determines the entire implementation. Errorless learning is achieved through a prompt hierarchy delivered such that the correct response occurs before an error can, followed by systematic fading. Response blocking is one tool among several. The defining feature is the arrangement plus the fading, not the blocking.

This is what makes the approach implementable in software that cannot intercept operating system input.

### 2.1 The honest counterargument

Errorless learning is not universally superior and this document should not pretend otherwise.

**Prompt dependency.** The known failure mode. If fading is not systematic and criterion-driven, the learner becomes dependent on the prompt and never performs independently. Every criticism of errorless procedures reduces to inadequate fading. This is why sections 6 and 7 exist, and why the fading protocol is treated as more important than the prompting protocol.

**Desirable difficulties.** There is a substantial literature indicating that effortful and even error-producing retrieval improves long-term retention relative to easy acquisition. Errorless learning optimizes acquisition speed and affective outcome; it does not automatically optimize retention.

**The resolution used here:** errorless procedures for acquisition, effortful retrieval for maintenance. Acquire the skill without errors, then maintain it through spaced, unprompted probes that are deliberately difficult. This is stated as a design principle in section 8 and it is one of the things that makes this specification credible rather than evangelical.

---

## 3. Definitions

Terms are used throughout with these meanings.

| Term | Definition |
|---|---|
| **Target** | A discrete skill to be acquired, defined by an observable behavior and its controlling stimulus. |
| **Trial** | One opportunity to perform a target. |
| **Prompt** | Any supplementary stimulus that increases the probability of a correct response. |
| **Prompt hierarchy** | An ordered set of prompts arranged by intrusiveness. |
| **Prompt fading** | Systematic reduction of prompt intrusiveness across trials, according to criteria. |
| **Most-to-least prompting** | Beginning with the most intrusive prompt and fading down. The errorless default. |
| **Least-to-most prompting** | Beginning with minimal help and escalating. Higher error rate; used for maintenance, not acquisition. |
| **Time delay** | Inserting a latency between the instruction and the prompt, allowing an independent response to occur first. |
| **Independent response** | The target performed with no prompt at any level. |
| **Mastery criterion** | The threshold of independent responding at which a target is considered acquired. |
| **Maintenance probe** | An unprompted trial on a previously mastered target, delivered after a delay. |
| **Generalization probe** | A trial of a mastered target under conditions that differ from the training conditions. |

---

## 4. Skill taxonomy

Targets are organized into domains with explicit prerequisite relationships. A learner cannot be presented with a target whose prerequisites are not mastered; the curriculum engine enforces this.

### Domain 1: Transport and navigation
- Start and stop playback
- Set and move the playhead
- Toggle loop
- Switch between Session and Arrangement view
- Set tempo
- Toggle metronome

### Domain 2: Track structure
- Create a MIDI track *(prereq: Domain 1)*
- Create an audio track
- Rename a track
- Delete a track
- Arm a track
- Group tracks

### Domain 3: Instrument loading
- Navigate the browser *(prereq: 2.1)*
- Load an instrument onto a track
- Load a preset
- Swap an instrument

### Domain 4: MIDI entry
- Create an empty clip *(prereq: 3.2)*
- Open the note editor
- Set grid resolution
- Place a note on the grid
- Set note length
- Set note velocity
- Delete a note
- Duplicate a clip
- Set clip loop length

### Domain 5: Rhythmic literacy
*Conceptual targets, taught in parallel with Domain 4 rather than sequentially.*
- Identify bar boundaries
- Identify beats within a bar
- Identify subdivisions
- Place an element on a specified beat
- Recognize and reproduce a stated pattern

### Domain 6: Arrangement
- Move a clip in time *(prereq: Domain 4)*
- Create a section
- Duplicate a section
- Build a transition

### Domain 7: Audio
- Record audio to a track *(prereq: 2.5)*
- Trim and fade
- Warp to tempo

### Domain 8: Signal chain
- Load an effect *(prereq: Domain 3)*
- Order effects
- Adjust a device parameter

### Domain 9: Mix
- Set track level *(prereq: Domain 2)*
- Set pan
- Create and use a send
- Solo and mute

### Domain 10: Automation
- Draw an automation envelope *(prereq: Domain 8)*
- Edit automation points

### Domain 11: Output
- Set loop and export range *(prereq: Domain 6)*
- Export audio

**Design note on ordering.** The curriculum must reach an audible musical result inside Domain 4, because the reinforcer that sustains everything downstream is hearing something you made. Domains 6 through 11 exist and can wait. A learner who has not heard their own loop by the end of their first session is a learner who will not return.

---

## 5. The prompt hierarchy

This is the central contribution of this document: the standard ABA prompt hierarchy mapped onto digital audio workstation interaction.

Ordered from most to least intrusive.

| Level | ABA term | DAW implementation | Learner action |
|---|---|---|---|
| **P0** | Full physical | The assistant performs the entire action. Track created, instrument loaded, notes printed. | Observes and hears the result |
| **P1** | Partial physical | The assistant performs part; the learner completes the terminal step. Track created and instrument loaded; learner places the notes. | Completes the final step |
| **P2** | Model | The assistant performs the action, undoes it, and asks the learner to repeat it. | Repeats a just-demonstrated action |
| **P3** | Gestural | An overlay highlights the exact target: the menu item, the browser entry, the grid cell. | Acts on the highlighted target |
| **P4** | Positional | The environment is arranged so the correct choice is trivially available: browser filtered to four items, one track present, grid pre-set. No highlight. | Selects from a constrained field |
| **P5** | Verbal, direct | Explicit instruction: "Press Ctrl+Shift+T to create a MIDI track." | Executes a stated instruction |
| **P6** | Verbal, indirect | Functional instruction with no procedure: "You'll need somewhere to put the drums." | Recalls and executes the procedure |
| **P7** | Independent | The goal is stated; nothing else is provided. "Make a four-bar drum loop, kick on 1 and 3." | Performs the full chain unprompted |

### 5.1 Two properties worth noticing

**P0 is the product.** The assistant, used normally by an experienced producer, is the most intrusive prompt level in the hierarchy. This means the assistant and the teacher are not two products; they are the same product at different points on one continuum. A user who never engages teaching mode is simply parked at P0 permanently, which is a legitimate way to use the tool.

**P4 is where errorless learning is achieved without input interception.** Environmental constraint does the work that response blocking would otherwise do. If the browser contains four items and one track exists and the grid is pre-set, the field of possible actions is small enough that error is unlikely without a single keystroke being intercepted. This is why v1 ships without OS-level control and still delivers the pedagogy.

### 5.2 Error handling at each level

Errors are not blocked. They are **detected and silently reversed** within a short window.

If a learner creates a second empty track, the state listener notices and removes it. No error dialog, no correction message, no marking of failure. The environment simply returns to the state where the correct action remains available.

This is the software analogue of errorless correction: the error occurred, it was not reinforced, it was not attended to, and it did not become a practiced response. The learner may not even notice it happened.

**Silent reversal must never touch anything the learner authored.** It applies only to structural artifacts created within the current trial. If there is ambiguity about whether something was learner-intended, do nothing.

---

## 6. The fading protocol

**This is the product roadmap. It is more important than the prompting.**

An unfaded prompt is a crutch, and a crutch is precisely the accusation the entire company is positioned against. The fading protocol is the operationalization of the Hinge principle: the tool is designed to be outgrown, and here is the measurable definition of outgrown.

### 6.1 Method: most-to-least with progressive time delay

Acquisition begins at the most intrusive level that guarantees a correct response, and moves down as criteria are met.

**Progressive time delay** is the primary within-level fading mechanism, and it maps unusually well onto software.

- Trial 1 through 3: prompt delivered simultaneously with the instruction. Zero delay.
- Trial 4 through 6: two second delay before the prompt appears.
- Trial 7 through 9: four second delay.
- Continuing until: the instruction is given and the prompt never appears unless requested.

The overlay simply waits longer before offering help. The learner is given progressively more room to respond independently, and the moment they do, they have performed at a lower prompt level without being told they were being tested.

### 6.2 Advancement criteria

Advance one level when:
- The learner responds correctly and independently of the current prompt on **three consecutive trials**, or
- The learner responds correctly during the delay interval, before the prompt appears, on **three consecutive trials**.

Return one level when:
- Two consecutive errors occur at the current level, or
- The learner requests help twice within one trial.

Returning a level is silent. It is not framed as failure and it is not announced.

### 6.3 Mastery criterion

A target is mastered when the learner performs it at **P7, independently, correctly, across three separate sessions on different days.**

Same-session repetition does not establish mastery. Cross-session performance does. This is deliberately conservative because the entire value proposition depends on the fading being real.

### 6.4 The exit condition

**A learner has completed Crates Studio's teaching function when they have mastered all targets in Domains 1 through 5 and can produce a stated musical idea faster manually than by prompting.**

That second clause is measurable. The system already times both paths. When manual execution time drops below prompt-and-review time for a given class of task, the product should say so, explicitly, and recommend the learner stop using it for that task.

A product that tells users to stop using it is not a marketing gesture here. It is the falsifiable claim the entire brand rests on, and it is measurable enough to publish.

---

## 7. Data collection

Every trial produces a record. Without this the fading is guesswork and none of the above is real.

Per trial:
- Target identifier
- Prompt level delivered
- Delay interval used
- Response latency
- Independent, prompted, error, or no response
- Error type where applicable
- Whether silent reversal fired
- Session and timestamp

Per learner:
- Targets mastered, in progress, and not yet introduced
- Current prompt level per target
- Trials to criterion per target
- Maintenance probe results
- Generalization probe results
- Manual versus prompted execution time per task class

This dataset is a second novel research asset. Nobody has trial-level acquisition data for creative software skills. It supports curriculum optimization, it supports academic publication, and it is the evidentiary basis for any claim the company makes about whether the teaching actually works.

**Privacy note:** this is learning performance data about identified individuals. It is sensitive, it should be treated as such in the artist agreement, and it must never be shared with third parties or used to rank or judge users publicly.

---

## 8. Maintenance and generalization

Acquisition is the easy half. A curriculum that ends at mastery produces learners who can do the thing in the environment they learned it in, once.

### 8.1 Maintenance probes

Previously mastered targets are re-presented, unprompted, at expanding intervals: one week, one month, three months.

**This is where the desirable difficulties argument from section 2.1 is honored.** Maintenance probes are deliberately unassisted and deliberately effortful. Errorless acquisition, effortful retention. If a probe fails, the target returns to the curriculum at P4 rather than at P0, because partial retention is likely.

### 8.2 Generalization probes

A skill acquired in one context is not a skill. Generalization is programmed, not assumed.

Probe dimensions:
- **Different tempo.** Grid placement learned at 120 BPM, probed at 90 and 160.
- **Different time signature.** Learned in 4/4, probed in 3/4 and 6/8.
- **Different instrument.** Learned on a drum rack, probed on a synth.
- **Different session state.** Learned in an empty project, probed in a project with eight existing tracks.
- **Different genre framing.** The same rhythmic target, requested in different stylistic language.

### 8.3 Programming for generalization

Following the standard technology of generalization: train with multiple exemplars from the outset rather than teaching in a single context and hoping for transfer. Vary tempo, instrument, and session state *during* acquisition, not only during probing. Teach loosely, avoiding a single rigid procedure where several valid paths exist, so the learner acquires the function rather than a memorized keystroke sequence.

This last point matters practically: Ableton often offers three ways to accomplish something. Teaching one and enforcing it produces a learner who is helpless when the interface changes. Teaching the function and accepting any valid path produces a producer.

---

## 9. Implementation phases

### v1: Environmental constraint plus result detection

- Purpose-built lesson template sessions
- Filtered browser views
- LOM state listeners for detection
- Silent reversal of structural errors
- Transparent always-on-top overlay for P3 gestural prompts
- Full prompt hierarchy P0 through P7
- Full fading protocol with progressive time delay
- Full data collection

**No operating system integration whatsoever.** Everything in sections 5 through 8 is deliverable in v1. This is the point: the pedagogy does not depend on the hard engineering.

### v2: True response blocking

Requires the perception layer described in `technical-architecture.md` (T-02, T-03). Adds genuine input interception so that invalid actions are not merely reversed but never occur.

**What v2 actually buys:** closer fidelity to the errorless ideal at the highest prompt levels, particularly for learners whose failure history has produced strong escape behavior around this task. For that population, the difference between "the error was silently undone" and "the error was impossible" may be significant.

**What v2 does not buy:** any of the curriculum, the hierarchy, the fading, the mastery criteria, or the data. Those are v1.

This is why the demo does not wait for v2, and why the demo is the instrument for recruiting the engineer who builds v2.

---

## 10. Open research questions

These are genuine unknowns, and they are the reason this is a research program rather than a feature list.

1. **Does the prompt hierarchy in section 5 have the intrusiveness ordering assumed?** P3 gestural and P4 positional may be inverted for software, since a highlight may be less intrusive than a constrained environment. Empirically testable.

2. **What are the correct advancement criteria for this domain?** Three consecutive trials is imported from established practice in other domains. Software skill acquisition may warrant different thresholds.

3. **Is silent reversal detectable, and does detection matter?** If learners notice their errors being erased, does that undermine the affective benefit that is the primary reason for errorless procedures?

4. **Does errorless acquisition of production skills transfer to creative independence,** or does it produce learners who can execute procedures but do not initiate them? This is the deepest question in the document and the one most worth publishing on.

5. **What is the retention curve without maintenance probes?** Establishes how much the maintenance system is actually contributing.

6. **Does prompt level correlate with self-reported creative ownership?** If a learner at P0 feels the music is not theirs and a learner at P4 feels it is, that finding would reshape the entire product.

7. **Does the exit condition ever actually trigger in the wild?** The strongest possible validation of the whole company would be published data showing users measurably outgrowing the tool.

---

## 11. Why this is the moat

Restated plainly, because it will need to be said in rooms:

The integration layer is open source and reproducible in a month. The corpus is reproducible by anyone willing to spend years earning artist trust. The discovery model is a research bet.

This document requires someone who has run acquisition programs, faded prompts against criteria, collected trial-level data, and watched a learner who believed they were incapable perform independently. That is a specific professional background, it is essentially absent from music technology, and it is not acquirable by reading a paper.

It is also the reason the company's central claim is falsifiable. Anyone can assert their tool teaches. This specification defines mastery, defines the exit condition, collects the data, and can be shown to be wrong.
