# Identity and permissions

**Status: Current resource permissions; scoped token delegation is proposed.**

Identity establishes the authenticated principal. Permissions determine what that principal can do to projects, surveys, participants and responses. The API enforces permissions at the operation boundary.

Link-based participant admission is distinct from Studio authorization. Possession of a link or a short-lived participant token must convey only its explicitly documented scope.

Proposed signed, short-lived resource permission tokens may reduce repeated database checks, but require defined audience, subject, permitted actions, expiration and revocation semantics. A token must not grant authority beyond its validation rules.
