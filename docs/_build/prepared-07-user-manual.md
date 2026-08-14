# SDJ Editorial Portal — User Manual

<dl class="docmeta">
  <dt>Project</dt>
  <dd>SDJ Editorial Portal — an editorial portal for the Science and Development Journal (SDJ), published by the College of Basic and Applied Sciences, University of Ghana</dd>
  <dt>Author</dt>
  <dd>Roger Koranteng Obeng (22424140)</dd>
  <dt>Assessor</dt>
  <dd>Prof. Solomon Mensah</dd>
  <dt>Date</dt>
  <dd>2026-08-12, revised 2026-08-14 against the running system</dd>
  <dt>Status</dt>
  <dd>Written from the live, deployed system, not from the source code. Every screen, label, button caption and error message described below was observed by signing in as each role in turn — author, reviewer, editor, Editor-in-Chief and administrator — and operating the real application at the addresses below. Where a screen does not exist, this manual says so rather than describing one that would be convenient.</dd>
</dl>

**Application:** `https://ugjcs-frontend.vercel.app`
**API:** `https://tsxsbf9rzp.us-east-1.awsapprunner.com`

---

## 1. Introduction

The SDJ Editorial Portal is a web application for running the editorial process of the
Science and Development Journal (SDJ), published by the College of Basic and Applied
Sciences, University of Ghana, end to end: an author submits a manuscript, an editor screens
it and sends it for review, one or more reviewers assess it without knowing who wrote it, an
editor records a decision, and — once a manuscript is accepted — the Editor-in-Chief
schedules it into a numbered issue and publishes it to the public archive. The deployed
system described in this manual is a prototype built for an Advanced Software Engineering
exam, not SDJ's official production system.

The system recognises five kinds of user, and a person may hold more than one role at once:

| Role | What they do in the portal |
|---|---|
| **Reader** | Anyone with a web browser. No account is needed to browse or search published papers. |
| **Author** | Submits manuscripts, tracks their progress, downloads their own submitted files, and responds when a revision is requested. |
| **Reviewer** | Is assigned manuscripts to assess, reads an anonymised copy, and submits a recommendation and comments. |
| **Editor** | Screens newly submitted manuscripts, assigns reviewers, and records editorial decisions (desk-reject, send to review, request revision, accept, reject). |
| **Editor-in-Chief** | Everything an editor can do, plus the exclusive authority to schedule an accepted manuscript into a volume and issue number, to publish it, and to waive an article processing charge. |
| **Administrator** | Manages accounts: grants and revokes roles, sets how many reviews a reviewer may hold at once, and deactivates accounts. See section 8. |

Every manuscript's progress is described entirely by its **status** (Submitted, Under
screening, Under review, and so on). Section 10 explains every status in plain language.

### Accounts for reviewing this prototype

Every demo account uses the pattern `<role>@sdj.test`. The sign-in page's role chips fill
these addresses for you (section 2.3); the passwords are typed by hand.

| Role | Email | Password |
|---|---|---|
| Author | `author@sdj.test` | `Sdj-Author-2026!` |
| Author (second) | `author2@sdj.test` | `Sdj-Author2-2026!` |
| Reviewer | `reviewer@sdj.test` | `Sdj-Reviewer-2026!` |
| Reviewer (2 to 7) | `reviewer2@sdj.test` … `reviewer7@sdj.test` | `Sdj-Reviewer2-2026!` … `Sdj-Reviewer7-2026!` |
| Editor | `editor@sdj.test` | `Sdj-Editor-2026!` |
| Editor-in-Chief | `eic@sdj.test` | `Sdj-EditorChief-2026!` |
| Administrator | `admin@sdj.test` | `Sdj-Admin-2026!` |

Seven reviewer accounts exist rather than one because the reviewer-candidate screen (section 6.3)
only demonstrates its conflict-of-interest and capacity rules if there are enough people to
exclude some and still leave others eligible. Two share the authors' affiliation, and five
sit at five other institutions.

---

## 2. Getting started

### 2.1 Reaching the site

Open a web browser and go to:

```
https://ugjcs-frontend.vercel.app
```

The address lands on the sign-in page. That is deliberate: the portal is a working tool for
authors, reviewers and editors, so the front door is the door you sign in through. A notice
across the top states plainly that this is a final-project prototype and not the journal's
official system.

If you are already signed in, the page recognises your session and forwards you straight to
your own working area without asking for credentials again.

The public archive is still open to anyone. Follow **Browse the archive** from the sign-in
page, or go directly to `/search`, to read published papers without an account.

### 2.2 What is public and what needs an account

| Without signing in | Requires signing in |
|---|---|
| Searching and browsing the archive | Submitting a manuscript |
| Opening any published paper's page | Tracking a manuscript's status |
| Downloading a published paper's PDF | Reviewing an assigned manuscript |
| Verifying a paper's editorial provenance | Screening, assigning reviewers, and recording decisions |
| Exporting a citation as BibTeX or RIS | Scheduling and publishing an accepted manuscript |
| The About, For authors and For reviewers pages | Paying or waiving an article processing charge |
| | Managing accounts (Administrator only) |

### 2.3 Signing in

1. Go to `https://ugjcs-frontend.vercel.app`, which opens the sign-in page directly. From
   any public page you can also click **Sign in** at the top right.
2. You should see a page headed **Sign in**, with an **Email** field, a **Password** field, and
   a **Sign in** button. A campus photograph fills the left half of the screen on a
   wide display, and sits above the form on a phone.
3. Enter your account's email and password and click **Sign in**.
4. If your credentials are correct, you are taken to the working area for your role: authors
   land on **My submissions**, reviewers on **My assignments**, editors and the
   Editor-in-Chief on the **Screening queue**, and administrators on **Accounts**. The
   banner along the top now shows your email address and a **Sign out** button in place of
   the **Sign in** link.
5. If your credentials are wrong, the page stays on the sign-in form and shows an alert
   reading:

   > **AuthenticationError**
   > email or password is incorrect

   Check for typing mistakes, a mistyped password most often, and try again.

**Demo accounts.** Above the form is a row of role chips: **Author**, **Reviewer**,
**Editor**, **Editor-in-chief**, **Administrator**. Clicking one fills in that desk's email
address and moves the cursor to the password box, which you then type yourself. The chips
save you retyping a long address; they do not sign you in, and they never fill a password.
The passwords are listed in section 1.

**Creating your own account.** If you have no account, click **Sign up as an author** below
the form. Give your full name, affiliation, email and a password of at least twelve
characters. Self-registration creates an author account and nothing more. Reviewer, editor
and administrator roles are granted by the editorial office through the admin console (section 8),
never chosen by the person signing up.

A person with more than one role (the Editor-in-Chief account, for example, also carries
editor authority) can move between the different working areas by editing the address bar —
`/author`, `/reviewer`, `/editor` — once signed in; the navigation bar at the top only ever
shows a link to one of them at a time.

### 2.4 Signing out

Click **Sign out** in the top navigation bar, next to your email address. You are returned to
the sign-in page. If you then try to open a page that needs an account — for instance by using
the browser's back button — you are sent back to the sign-in page automatically, with the page
you wanted attached so you return to it after signing in again.

---

## 3. For readers (no account needed)

### 3.1 Browsing the archive

1. Go to `https://ugjcs-frontend.vercel.app` and follow **Browse the archive**, or go
   directly to `/search`.
2. Published papers are listed with their tracking code (for example `SDJ-2026-0005`),
   title, author(s), a short abstract and keywords.
3. Click any paper's title to open it.

### 3.2 Opening a paper

A paper's page (`/papers/<tracking-code>`) shows its tracking code, title, author(s),
keywords and abstract, followed by:

- **The full PDF**, previewed inline on the page, with a **Download PDF** link beneath it.
- **A DOI-shaped identifier and citation export** — copy the identifier, or download the
  citation as **BibTeX** or **RIS**. (The identifier is DOI-shaped but not registered, so
  resolving it at doi.org will not work — a documented limit of this prototype.)
- **An editorial provenance panel**, which verifies the paper's editorial history against
  the tamper-evident audit chain and reports whether the chain is intact, its head hash,
  and each event's type and timestamp.

**Limitation to be aware of:** the page shows no publication date, volume or issue number —
the system does not store one.

### 3.3 Searching

1. Click **Search** in the top navigation bar, or go to `/search`.
2. You will see a single search box labelled **Search papers**, with the placeholder text
   "Title, abstract or keyword", and a **Search** button.
3. Type a word or phrase and either press Enter or click **Search**.
4. Matching papers appear as a list below the search box, in the same format as the home
   page's "Recently published" list.
5. If nothing matches, the page reads "No papers matched "your search term"" with the
   suggestion "Try a different title, keyword or author name."

Search covers each paper's **title**, **abstract**, **keywords** and the **full text of
the PDF itself** — a distinctive phrase from inside a paper finds it, with the matching
passage shown as a highlighted snippet under the result.

**Limitation to be aware of:** author names are not part of the search index. Searching
"Ama Serwaa", an author of several published papers, returns no results (re-verified
against the live archive on 2026-08-14). Search by topic words, not by author name.

---

## 4. For authors

Sign in with an author account (or any account that also carries author rights) to reach
**My submissions** at `/author`.

### 4.1 Submitting a manuscript

1. From **My submissions**, click **Submit** in the top navigation bar, or go to
   `/author/submit`. You should see a page headed **Submit a manuscript**.
2. Fill in the fields:
   - **Title**
   - **Abstract**
   - **Keywords (comma-separated)** — for example `edge computing, rural connectivity`
   - **Co-author account ids (comma-separated, optional)** — leave this blank unless a
     co-author already has a portal account and its account id.
3. Under **Manuscript PDF (max 10 MB)**, either drag your PDF onto the box that reads "Drag a
   PDF here, or click to browse", or click it to open a file picker. Once a file is chosen,
   its name and size (in MB) replace that text.
4. Click **Submit manuscript**.
5. If the submission succeeds, you are taken straight to the manuscript's own page, which now
   shows a **Submitted** badge and a newly minted tracking code (for example
   `SDJ-2026-939860`). If it fails, an alert appears above the form explaining why — see section 11
   for the two most common reasons (wrong file type, file too large).

**Preparing your file for double-blind review is your responsibility.** The portal strips the PDF's
embedded metadata (author name, document title, etc.) automatically before a reviewer ever
sees it — but it has no way to read the words printed on the page. If your name, your
institution, or an obvious self-citation ("as we showed in our earlier work…") appears in the
body of the manuscript itself, anonymisation will not remove it. Before submitting, check that
the manuscript text itself does not identify you.

### 4.2 Tracking your submissions and understanding their status

From **My submissions**, every manuscript you have submitted is listed with its title,
tracking code, and a coloured status badge (Submitted, Under review, Resubmitted, Published,
and so on). Click any entry to see its full detail page.

That detail page shows:

- The title and current status badge.
- The tracking code.
- The abstract.
- A line reading "*N* of *M* reviews submitted" — how many of the required reviews are in.
- An inline preview of your submitted PDF, with a download link.
- A red **Withdraw submission** button, present at every stage up to and including
  "Revision requested". Withdrawal is terminal, so it asks twice: the first click arms a
  confirmation, and only the second, explicit confirm actually withdraws.
- Once the manuscript is **Accepted**, an **Article processing charge** panel (section 9).

See section 10 for what each status means and what happens next.

### 4.3 Downloading your own submission

On any of your manuscripts' detail pages, click **Download my submitted document**. This
starts a download of your original PDF, exactly as you uploaded it (not the anonymised copy
reviewers see). The link is time-limited internally, so if it ever fails, simply reload the
page and click it again to get a fresh one.

### 4.4 Responding to a requested revision

When a manuscript's status is **Revision requested**, its detail page grows a new section
headed **Resubmit a revised manuscript**, with:

- **Revised manuscript PDF (max 10 MB)** — the same drag-and-drop/click-to-browse control used
  when submitting.
- **Response to reviewers** — a required text box (at least 20 characters) where you explain,
  point by point, what you changed and why.
- A **Resubmit manuscript** button.

To respond to a revision request:

1. Open the manuscript from **My submissions**.
2. Attach your revised PDF.
3. Write your response to reviewers in the text box provided.
4. Click **Resubmit manuscript**.
5. On success, the manuscript's status changes to **Resubmitted** and it goes back into the
   editorial process — an editor decides from there whether it returns to review or moves
   straight to a decision.

---

## 5. For reviewers

Sign in with a reviewer account to reach **My assignments** at `/reviewer` — a list of every
manuscript currently assigned to you, showing each one's title and tracking code.

### 5.1 Opening an assignment

Click any assignment to open it. You will see the manuscript's tracking code, title, a short
abstract, and its keywords, followed by an inline preview of the **anonymised** PDF (with a
**Download anonymised PDF** link) and a **Submit your review** form.

### 5.2 What "anonymised" means here — read this before you review

**The copy you are given to review has had two layers of identifying information removed:**

1. **No author name is shown anywhere on the page.** The reviewer's view of a manuscript never
   displays who wrote it — not on the assignment list, not on the manuscript's own page. This
   is enforced structurally: the reviewer-facing screens are built from a version of the data
   that has no author field to display in the first place, not by a filter that might be
   forgotten.
2. **The PDF itself has had its embedded metadata stripped** before it is stored as the copy
   reviewers download. Clicking **Download anonymised manuscript** downloads this stripped
   version — never the author's original file, which reviewers have no route to reach at all.

**What this does *not* do:** metadata stripping removes information embedded in the PDF file
(author, title, and similar fields set by the word processor that produced it) — it cannot
touch anything printed as visible text on the page. If an author's name, institution, or an
identifying self-reference is typed into the body of the manuscript, you may still see it.
Anonymisation is therefore a shared responsibility: the system strips what it can strip
automatically, and authors are asked to prepare a manuscript that does not identify itself in
its own text (section 4.1). If you do recognise or infer an author's identity from the text itself,
treat that as you would in any double-blind process — it is not something the platform can
prevent.

### 5.3 Submitting your review

The **Submit your review** form asks for:

- **Four criterion scores**, each from 1 to 5: **Originality**, **Rigour**, **Clarity** and
  **Significance**.
- **Recommendation** — a dropdown with four options: `accept`, `minor revision`,
  `major revision`, `reject`.
- **Comments to the author** — your written assessment as the author will read it.
- **Confidential comments to the editor** — remarks only the editor can see. Nothing you
  write here is ever shown to the author, and no reviewer- or author-reachable screen can
  display it.

To submit:

1. Score each criterion and choose the recommendation that reflects your judgement.
2. Write both comment fields — be specific in the author-facing one, and candid in the
   confidential one.
3. Click **Submit review**.
4. On success you are returned to **My assignments**; the manuscript no longer requires
   further action from you. Once every reviewer assigned to a manuscript has submitted, its
   status moves on automatically (section 10) and the editor is able to record a decision.

---

## 6. For editors

Sign in with an editor account (or the Editor-in-Chief account, which also carries editor
rights) to reach the **Screening queue** at `/editor`.

### 6.1 The screening queue

The queue is a table of **Tracking code**, **Title** and **Status**, captioned "Manuscripts
awaiting editorial action". **It lists only manuscripts whose status is "Submitted"** — as
soon as you begin screening one, it disappears from this table. If you need to return to a
manuscript that is already under screening, under review, or awaiting a decision, you will
need its tracking code (from an earlier visit, or from the author) and can go directly to
`/editor/<tracking-code>` — there is currently no second queue listing manuscripts waiting on
a decision.

### 6.2 Screening a submission

1. From the queue, click a manuscript's tracking code to open it. You should see its title,
   a **Submitted** status badge, its abstract, the reviews-submitted count, an inline
   preview of the PDF, and a **Begin screening** button.
2. Read the manuscript and click **Begin screening**.
3. The page updates in place: the status badge changes to **Under screening**, and the
   reviewer-assignment and **Decision** sections appear.

### 6.3 Assigning reviewers

The assignment section lists **every reviewer in the pool as a candidate, ranked by how
well their declared expertise matches the manuscript's keywords**, with their current
workload shown against their capacity. Candidates who must not be assigned are not hidden
— they appear marked **"Excluded"** with the reason stated (they share an author's
affiliation, are already assigned to this manuscript, or are at capacity), so you can see
why an obvious name is unavailable. The ranking is advice, not authority: you remain free
to assign any eligible candidate regardless of their position in it.

1. Select a candidate from the list.
2. Click **Assign selected reviewer**.
3. The assignment appears in the assignments panel with its **due date** and, once the date
   passes without a review, an **overdue** flag. Repeat for the second reviewer; two are
   normally expected before a decision becomes possible (section 10).

### 6.4 Recording a decision

The **Decision** section shows a **Decision** dropdown and a required **Rationale** text box
(at least 20 characters), followed by a **Record decision** button. The options offered in the
dropdown depend on the manuscript's current status:

- While the manuscript is **Under screening**, the choices are **desk reject** and
  **send to review**.
- Once every assigned reviewer has submitted their review and the manuscript's status has
  become **Reviews complete**, the choices become **request revision**, **accept** and
  **reject**.
- At any other status, no decision is currently possible and this section shows only its
  heading with no form under it.

To record a decision:

1. Choose the option that reflects your editorial judgement.
2. Write your reasoning in **Rationale** (this is required and must be at least 20 characters
   — a one-word rationale will be rejected).
3. Click **Record decision**. For a final decision (accept, reject, desk reject) the button
   re-labels to **Confirm …** beside a **Go back** escape, and only the second, explicit
   click records it — a deliberate guard against recording an irreversible decision by
   accident.
4. The manuscript's status badge updates immediately (see section 10 for what each decision
   leads to). Once reviews are in, this page also shows both of each review's channels —
   including the confidential comments only editors can read — and, after a final decision,
   a **Decision certificate** download: a PDF stating the decision, the tracking code and
   the audit chain's head hash.

---

## 7. For the Editor-in-Chief

Everything in section 6 is also available to the Editor-in-Chief account. In addition, on any
manuscript whose status is **Accepted** or **Scheduled**, a further **Publication** section
appears on its detail page — visible only to the Editor-in-Chief, not to ordinary editors.

### 7.1 Scheduling an accepted manuscript into an issue

1. Open an **Accepted** manuscript's page (from `/editor/<tracking-code>`).
2. Under **Publication**, you will see a small form with two number fields, **Volume** and
   **Number**, and a **Schedule** button.
3. Enter the volume and issue number you want this manuscript to appear in (for example
   Volume `3`, Number `1`).
4. Click **Schedule**.
5. The status badge updates to **Scheduled**, and the **Publication** section is replaced by a
   single **Publish** button.

### 7.2 Publishing

1. On a **Scheduled** manuscript's page, click the **Publish** button under **Publication**.
2. The status badge updates to **Published**. The paper appears in the public archive
   immediately: on its own `/papers/<tracking-code>` page and in search results.

Publishing also extracts the text of the PDF so the paper becomes findable by its body
content and not only its title and abstract. If the text cannot be extracted, the paper is
still published; it simply stays searchable by title, abstract and keywords alone.

Publishing is not reversible through the web application. There is no "unpublish" action.

### 7.3 Waiving an article processing charge

Only the Editor-in-Chief can waive a charge. Open the accepted manuscript, find the
**Article processing charge** panel, and click **Waive**. A charge that has already been
paid cannot be waived; the button refuses with an explanation rather than reversing a
settled payment. See section 9 for the charge itself.

---

## 8. For administrators

Sign in as an administrator and you land on **Accounts**, the roster of every account in the
system. This screen exists to do four things.

**Grant or revoke a role.** Each row lists the roles that account holds. Use the controls on
the row to add or remove `author`, `reviewer`, `editor` or `editor_in_chief`. This is how
someone becomes a reviewer or an editor: it cannot be chosen by the person signing up.

**Set reviewer capacity.** Capacity is how many live assignments a reviewer may hold at
once, between 1 and 10. It feeds the reviewer-candidate screen (section 6.3), where a reviewer at
capacity is shown to the editor as excluded, with the reason stated, rather than hidden.

**Deactivate or reactivate an account.** A deactivated account cannot sign in and stops
appearing as an eligible reviewer.

**Read the roster.** This is the only screen that shows an account's email address alongside
its activation and verification state.

Two things the console deliberately refuses, both to stop an administrator locking everyone
out of the system:

- The **administrator role itself cannot be granted or revoked** here. Changing who is an
  administrator is a database-level operation, not a click.
- **You cannot deactivate your own account.** The attempt is refused with an explanation.

---

## 9. Article processing charges

SDJ raises an article processing charge (APC) once a manuscript is accepted. Nothing is
billed before acceptance, so no charge appears at submission, during screening, or while a
manuscript is under review.

**As an author.** Open your accepted manuscript. Below the manuscript details is an
**Article processing charge** panel showing the amount and one of three states:

| Status | Meaning |
|---|---|
| **Pending** | The charge is outstanding. A **Pay** button starts settlement. |
| **Paid** | Settled. The panel shows the transaction reference, which you need if you have to reconcile a card statement. |
| **Waived** | The Editor-in-Chief has cancelled the charge. Nothing is owed. |

Click **Pay** and one of two things happens, depending on how the deployment is configured.

In the default configuration the portal uses a **mock payment gateway**: the charge settles
immediately, the panel flips to **Paid**, and no card is involved. This is how the deployed
prototype behaves, and it is the mode you should expect while reviewing this project. **No
real money moves through this system.**

If a live Paystack key is configured, clicking **Pay** instead sends you to Paystack's
checkout page. After paying you return to the manuscript, and the portal confirms the charge
with Paystack before marking it **Paid**. A charge is never marked paid on your say-so.

**As an editor.** Any editor can read a manuscript's charge and its status. Only the
corresponding author can pay it, and only the Editor-in-Chief can waive it (section 7.3).

---

## 10. Understanding manuscript status

Every manuscript carries exactly one status at a time, shown as a coloured badge throughout
the application. The table below explains each one in plain language: what it means, who can
act on it next, and what they can do. ("Terminal" means the manuscript stays there permanently
— nothing in the application can move it any further.)

| Status badge | What it means | Who can act | What they can do |
|---|---|---|---|
| *(Draft — never shown)* | An internal starting point created for an instant when a manuscript is first submitted, immediately superseded by "Submitted" in the same action. No screen in the application ever shows a manuscript sitting at this status. | — | — |
| **Submitted** | The author has uploaded the manuscript and it is waiting for an editor to look at it. Appears in the editor's screening queue. | Editor | Begin screening, or the author may withdraw it. |
| **Under screening** | An editor has opened the manuscript and is deciding whether it deserves review. | Editor | Assign reviewers; record a desk-reject or send-to-review decision; or the author may withdraw it. |
| **Desk rejected** | *Terminal.* The editor decided, without sending it for review, that the manuscript is not suitable for the journal. | — | Nothing further happens to this manuscript. |
| **Under review** | The manuscript has been sent to one or more reviewers and is awaiting their assessments. | Reviewer(s) | Submit their review; the author may still withdraw it. |
| **Reviews complete** | Every required review has been submitted. The manuscript is waiting for an editor to record a decision. | Editor | Record a decision: request revision, accept, or reject; or the author may withdraw it. |
| **Revision requested** | The editor has asked the author to revise the manuscript before it can proceed. | Author | Upload a revised PDF and a written response to reviewers (section 4.4); or withdraw the manuscript instead. |
| **Resubmitted** | The author has uploaded a revised version and explained the changes. It is back with the editor. | Editor | Decide whether it needs another round of review (send back to Under screening) or straight to review (Under review) — this is an editorial judgement call, not shown as a distinct button in the interface at the time of writing. |
| **Accepted** | The editor has decided to accept the manuscript for publication. | Editor-in-Chief | Schedule it into a volume and issue number (section 7.1). |
| **Rejected** | *Terminal.* The editor decided, after review, not to publish the manuscript. | — | Nothing further happens to this manuscript. |
| **Scheduled** | The Editor-in-Chief has assigned the manuscript to a specific volume and issue number, but it is not yet public. | Editor-in-Chief | Publish it (section 7.2). |
| **Published** | *Terminal.* The manuscript is live on the public site — visible on the home page, its own paper page, and in search. | — | Nothing further happens to this manuscript through the application. |
| **Withdrawn** | *Terminal.* The author pulled the manuscript out of consideration. Available from Submitted, Under screening, Under review, Reviews complete, or Revision requested. | — | Nothing further happens to this manuscript. |

A manuscript that reaches **Accepted** cannot be withdrawn through the application — once it
is accepted, the only paths forward are scheduling and publishing.

---

## 11. Troubleshooting

**"UnsupportedDocumentTypeError — document does not begin with the PDF magic number"**
The file you attached is not actually a PDF (or is empty/corrupted), regardless of its file
extension. The portal checks the file's own contents, not its name, so renaming a Word document to
`.pdf` will not get past this check. Export or print your document to a genuine PDF and try
again.

**"That file is too large — the limit is 10 MB"**
Manuscript and revision uploads are capped at 10 MB. This message appears immediately, before
you even click Submit. If your PDF is larger, reduce it — flattening embedded images or
re-exporting at a lower image resolution usually brings a typeset paper well under the limit —
and attach the smaller file instead.

**You are dropped back at the sign-in page while working, or a page you expect to see
redirects you to "Sign in"**
Your session has ended — either you were signed out, or enough time has passed that you are
no longer recognised as signed in. Sign in again with your account's email and password; you
should be returned to roughly where you were.

**"AuthenticationError — email or password is incorrect"**
Exactly what it says: the email/password combination you entered does not match an account.
Check for typing mistakes, particularly trailing spaces or the Caps Lock key, and try again.

**A button or form you expect to see is missing (for example, no "Begin screening" button, or
the Decision section shows only its heading and nothing else)**
This almost always means the manuscript is not currently in the status that action requires.
The portal only offers an action when the manuscript's status allows it — for example, the Decision
form's "accept/reject/request revision" choices only appear once every assigned review is in
(status "Reviews complete"); while reviews are still outstanding, that section is empty on
purpose. Check the status badge at the top of the page against section 10 to see what is expected
before the action you want becomes available.

**You try to act on a manuscript and are told "cannot move manuscript from *X* to *Y*"**
This is the same rule as above, surfaced as an error rather than a hidden button — it usually
happens if a manuscript's status changed (for instance, another editor acted on it) between
when you opened the page and when you clicked the button. Reload the page to see its current
status and try again from there.

**A manuscript you are screening or deciding on has disappeared from the Screening queue**
This is expected, not a fault: the queue only lists manuscripts whose status is "Submitted".
The moment you begin screening one, it moves to "Under screening" and drops out of the queue
table. Keep a note of its tracking code, or navigate directly to
`/editor/<tracking-code>`, to return to it.

**A reviewer you expected to assign shows as "Excluded" in the candidate list**
That is the conflict-of-interest and workload screen working as designed: the stated reason
(shared affiliation with an author, already assigned to this manuscript, or at capacity)
explains why. An excluded candidate is shown rather than hidden precisely so you know the
exclusion happened. If capacity is the reason, an administrator can raise it (section 8).

**The Administrator account lands on Accounts and nothing else**
That is the whole of the administrator's workspace, and it is deliberate. The role manages
accounts (section 8); it does not screen manuscripts, review them, or record decisions, so
`/author`, `/reviewer` and `/editor` all refuse it.
