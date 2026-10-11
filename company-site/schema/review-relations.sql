-- Proposed SQLite/D1 schema. Not a deployed migration.
PRAGMA foreign_keys = ON;
CREATE TABLE review_companies (id TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE review_guests (id TEXT PRIMARY KEY);
CREATE TABLE review_owners (id TEXT PRIMARY KEY);
CREATE TABLE review_apartments (id INTEGER PRIMARY KEY);
CREATE TABLE review_stays (
  id TEXT PRIMARY KEY,
  realtycalendar_booking_id TEXT NOT NULL UNIQUE,
  apartment_id INTEGER NOT NULL REFERENCES review_apartments(id),
  guest_id TEXT NOT NULL REFERENCES review_guests(id),
  company_id TEXT REFERENCES review_companies(id),
  owner_id_at_stay TEXT NOT NULL REFERENCES review_owners(id),
  completed_at TEXT NOT NULL
);
CREATE TABLE linked_reviews (
  id TEXT PRIMARY KEY,
  stay_id TEXT NOT NULL REFERENCES review_stays(id),
  author_role TEXT NOT NULL CHECK(author_role IN ('guest','company','owner','staff')),
  author_id TEXT NOT NULL,
  text TEXT NOT NULL CHECK(length(text) BETWEEN 10 AND 2000),
  rating INTEGER CHECK(rating BETWEEN 1 AND 5),
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
  public_consent INTEGER NOT NULL DEFAULT 0 CHECK(public_consent IN (0,1)),
  created_at TEXT NOT NULL
);
-- The same review is linked to all participants through its verified stay;
-- do not create copies or imply that the participants all authored it.
CREATE VIEW linked_review_context AS
SELECT r.*, s.apartment_id, s.guest_id, s.company_id, s.owner_id_at_stay
FROM linked_reviews r JOIN review_stays s ON s.id=r.stay_id;
-- Public apartment reviews must be guest/company-authored, moderated and consented.
CREATE VIEW public_apartment_reviews AS
SELECT r.id, r.text, r.rating, r.created_at, s.apartment_id
FROM linked_reviews r JOIN review_stays s ON s.id=r.stay_id
WHERE r.status='approved' AND r.public_consent=1
AND r.author_role IN ('guest','company');
-- Private views require server-side authorization for each guest/company/owner.
