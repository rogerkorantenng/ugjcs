"""Closed vocabularies of the editorial domain."""

from enum import StrEnum


class Role(StrEnum):
    AUTHOR = "author"
    REVIEWER = "reviewer"
    EDITOR = "editor"
    EDITOR_IN_CHIEF = "editor_in_chief"
    ADMINISTRATOR = "administrator"


class ManuscriptStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_SCREENING = "under_screening"
    DESK_REJECTED = "desk_rejected"
    UNDER_REVIEW = "under_review"
    REVIEWS_COMPLETE = "reviews_complete"
    REVISION_REQUESTED = "revision_requested"
    RESUBMITTED = "resubmitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"


class Recommendation(StrEnum):
    ACCEPT = "accept"
    MINOR_REVISION = "minor_revision"
    MAJOR_REVISION = "major_revision"
    REJECT = "reject"


class DecisionType(StrEnum):
    DESK_REJECT = "desk_reject"
    SEND_TO_REVIEW = "send_to_review"
    REQUEST_REVISION = "request_revision"
    ACCEPT = "accept"
    REJECT = "reject"


class AssignmentStatus(StrEnum):
    INVITED = "invited"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    SUBMITTED = "submitted"
    EXPIRED = "expired"


class EventType(StrEnum):
    MANUSCRIPT_SUBMITTED = "manuscript_submitted"
    SCREENING_STARTED = "screening_started"
    REVIEWER_ASSIGNED = "reviewer_assigned"
    INVITATION_ANSWERED = "invitation_answered"
    REVIEW_SUBMITTED = "review_submitted"
    DECISION_RECORDED = "decision_recorded"
    REVISION_SUBMITTED = "revision_submitted"
    MANUSCRIPT_WITHDRAWN = "manuscript_withdrawn"
    SCHEDULED_FOR_ISSUE = "scheduled_for_issue"
    MANUSCRIPT_PUBLISHED = "manuscript_published"
