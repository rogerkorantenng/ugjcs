# SDJ Editorial Portal — User Manual

**Project:** SDJ Editorial Portal — an editorial portal for the Science and Development
Journal (SDJ), published by the College of Basic and Applied Sciences, University of Ghana
**Author:** Roger Koranteng Obeng (22424140)
**Assessor:** Prof. Solomon Mensah
**Date:** 2026-08-12
**Status:** Written from the live, deployed system, not from the source code. Every screen,
label, button caption and error message described below was observed by signing in as each
role in turn — author, reviewer, editor, Editor-in-Chief and administrator — and operating the
real application at the addresses below. Where a screen does not exist, this manual says so
rather than describing one that would be convenient.

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
| **Editor-in-Chief** | Everything an editor can do, plus the exclusive authority to schedule an accepted manuscript into a volume and issue number, and to publish it. |

An **Administrator** account also exists for signing in to the API, but at the time of writing
the web application has no screens built for it — see §9 for what this means in practice.

Every manuscript's progress is described entirely by its **status** (Submitted, Under
screening, Under review, and so on). §8 explains every status in plain language.

---

## 2. Getting started

### 2.1 Reaching the site

Open a web browser and go to:

```
https://ugjcs-frontend.vercel.app
```

The home page is public. It shows a short introduction to the journal and a "Recently
published" list of papers. No account is required to reach it.

### 2.2 What is public and what needs an account

| Without signing in | Requires signing in |
|---|---|
| The home page and its "Recently published" list | Submitting a manuscript |
| Opening any published paper's page | Tracking a manuscript's status |
| Searching the archive | Reviewing an assigned manuscript |
| | Screening, assigning reviewers, and recording decisions |
| | Scheduling and publishing an accepted manuscript |

### 2.3 Signing in

1. Click **Sign in** at the top right of any public page, or go directly to
   `https://ugjcs-frontend.vercel.app/login`.
2. You should see a page headed **Sign in**, with an **Email** field, a **Password** field, and
   a **Sign in** button.
3. Enter your account's email and password and click **Sign in**.
4. If your credentials are correct, you are taken to the working area for your role: authors
   land on **My submissions**, reviewers on **My assignments**, and editors and the
   Editor-in-Chief on the **Screening queue**. The page banner along the top now shows your
   email address and a **Sign out** button in place of the **Sign in** link.
5. If your credentials are wrong, the page stays on the sign-in form and shows an alert
   reading:

   > **AuthenticationError**
   > email or password is incorrect

   Check for typing mistakes — in particular a mistyped password — and try again.

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

1. Go to `https://ugjcs-frontend.vercel.app`.
2. Under the heading **Recently published**, you will see a list of published papers. Each
   entry shows its tracking code (for example `SDJ-2026-0005`), its title, its author or
   authors, a short abstract, and its keywords.
3. Click any paper's title to open it.

### 3.2 Opening a paper

A paper's page (`/papers/<tracking-code>`) shows its tracking code, title, author(s),
keywords and abstract.

**Limitation to be aware of:** the paper page does not currently offer a way to download the
manuscript's PDF, and it does not show a publication date, volume or issue number. Only the
title, authors, keywords and abstract are shown. If you need the full text, there is currently
no public download link for it.

### 3.3 Searching

1. Click **Search** in the top navigation bar, or go to `/search`.
2. You will see a single search box labelled **Search papers**, with the placeholder text
   "Title, abstract or keyword", and a **Search** button.
3. Type a word or phrase and either press Enter or click **Search**.
4. Matching papers appear as a list below the search box, in the same format as the home
   page's "Recently published" list.
5. If nothing matches, the page reads "No papers matched "your search term"" with the
   suggestion "Try a different title, keyword or author name."

**Limitation to be aware of:** despite that suggestion, searching by an author's name did not
return that author's papers when tested against the live archive (searching "Ama Serwaa", an
author of five published papers, returned no results). In practice, search reliably matches
words that appear in a paper's **title**, **abstract** or **keywords** — do not rely on it to
find a particular author's work.

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
   `SDJ-2026-939860`). If it fails, an alert appears above the form explaining why — see §9
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
- A **Download my submitted document** button/link, which downloads the exact PDF you
  uploaded.
- A red **Withdraw submission** button, present at every stage up to and including
  "Revision requested" — click it to pull the manuscript out of consideration. Withdrawal
  cannot be undone.

See §8 for what each status means and what happens next.

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
abstract, and its keywords, followed by a **Download anonymised manuscript** link and a
**Submit your review** form.

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
its own text (§4.1). If you do recognise or infer an author's identity from the text itself,
treat that as you would in any double-blind process — it is not something the platform can
prevent.

### 5.3 Submitting your review

The **Submit your review** form has two fields:

- **Recommendation** — a dropdown with four options: `accept`, `minor revision`,
  `major revision`, `reject`.
- **Comments** — a free-text box for your written assessment.

There is no separate numeric scoring by criterion (originality, methodology, clarity, etc.) —
the review consists solely of your chosen recommendation and your written comments.

To submit:

1. Choose the option from **Recommendation** that best reflects your judgement.
2. Write your comments in the **Comments** box. This is what the editor — and, indirectly, the
   author — will read, so be specific.
3. Click **Submit review**.
4. On success you are returned to **My assignments**; the manuscript no longer requires
   further action from you. Once every reviewer assigned to a manuscript has submitted, its
   status moves on automatically (§8) and the editor is able to record a decision.

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

1. From the queue, click a manuscript's tracking code to open it. You should see its title, a
   **Submitted** status badge, its abstract, the reviews-submitted count, a **Download
   manuscript** link, and a **Begin screening** button.
2. Read the manuscript (download it if needed) and click **Begin screening**.
3. The page updates in place: the status badge changes to **Under screening**, and two new
   sections appear — **Assign a reviewer** and **Decision**.

### 6.3 Assigning reviewers

Under **Assign a reviewer**, you will see a single field, **Reviewer account id**, and an
**Assign** button.

**This expects the reviewer's account id, not their name or email address.** There is no
picker or search box to choose a reviewer from — you must already know the id of the account
you want to assign, obtained separately (for example from your own records or from the
reviewer directly).

1. Enter the reviewer's account id.
2. Click **Assign**.
3. The field clears on success. Repeat for each reviewer you want assigned; two are normally
   expected before a decision on the reviews becomes possible (§8).

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
3. Click **Record decision**.
4. The manuscript's status badge updates immediately to reflect the outcome (see §8 for what
   each decision leads to).

*A small labelling quirk you may notice:* the "send to review" option is occasionally rendered
by the interface as **"send to_review"**, with the underscore left in. This is a cosmetic
formatting slip, not a different option — it is still the same "send to review" decision.

---

## 7. For the Editor-in-Chief

Everything in §6 is also available to the Editor-in-Chief account. In addition, on any
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
2. The status badge updates to **Published**. The paper now appears in the public archive
   ("Recently published" on the home page, its own `/papers/<tracking-code>` page, and in
   search results) immediately.

Publishing is not reversible through the web application — there is no "unpublish" action.

---

## 8. Understanding manuscript status

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
| **Revision requested** | The editor has asked the author to revise the manuscript before it can proceed. | Author | Upload a revised PDF and a written response to reviewers (§4.4); or withdraw the manuscript instead. |
| **Resubmitted** | The author has uploaded a revised version and explained the changes. It is back with the editor. | Editor | Decide whether it needs another round of review (send back to Under screening) or straight to review (Under review) — this is an editorial judgement call, not shown as a distinct button in the interface at the time of writing. |
| **Accepted** | The editor has decided to accept the manuscript for publication. | Editor-in-Chief | Schedule it into a volume and issue number (§7.1). |
| **Rejected** | *Terminal.* The editor decided, after review, not to publish the manuscript. | — | Nothing further happens to this manuscript. |
| **Scheduled** | The Editor-in-Chief has assigned the manuscript to a specific volume and issue number, but it is not yet public. | Editor-in-Chief | Publish it (§7.2). |
| **Published** | *Terminal.* The manuscript is live on the public site — visible on the home page, its own paper page, and in search. | — | Nothing further happens to this manuscript through the application. |
| **Withdrawn** | *Terminal.* The author pulled the manuscript out of consideration. Available from Submitted, Under screening, Under review, Reviews complete, or Revision requested. | — | Nothing further happens to this manuscript. |

A manuscript that reaches **Accepted** cannot be withdrawn through the application — once it
is accepted, the only paths forward are scheduling and publishing.

---

## 9. Troubleshooting

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
purpose. Check the status badge at the top of the page against §8 to see what is expected
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

**"Could not assign that reviewer — Check the account id and try again."**
The reviewer assignment field expects an account id, not an email address or name, and there
is no directory or search box built into the form to look one up. Confirm you have the
correct account id for the reviewer before retrying.

**As a reader, you cannot find a way to download a paper's PDF**
This is a genuine gap in the current system, not a mistake on your part — the public paper
page shows only the title, authors, keywords and abstract; no PDF download link is offered to
readers at the time of writing.

**Signing in with the Administrator account does not lead anywhere useful**
This is expected with the system as currently built: the Administrator account authenticates
successfully, but the web application has no screens built for it. Signing in redirects
straight back to the public home page, and none of the `/author`, `/reviewer` or `/editor`
areas will admit it. There is nothing further for this role to do in the browser at the time
of writing.
