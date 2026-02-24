# Trip Matching Logic Architecture

## Problem Statement

In a travel or ride-sharing application, the matching logic connects users traveling from a similar source to a similar destination.

The current database architecture in `app/models/travel.py` and `app/models/request.py` poses a logical challenge:

- Users create a `Travel` plan.
- The `Request` model expects a single `travel_id`, `sent_by`, and `sent_to`.

**The Issue**: If both the host (offering a trip) and the seeker (looking for a trip) are required to create separate `Travel` database records to find matches, it becomes ambiguous **whose `travel_id` should be used in the `Request` record**. Additionally, forcing seekers to create an independent `Travel` record just to search for existing trips adds unnecessary friction.

Below are the three standard architectural solutions to resolve this depending on the desired behavior of the platform.

---

## Solution 1: The "Search & Request" Flow (Host & Passenger Model)

_Best suited for: UberPool, BlaBlaCar, or standard driver-passenger ride-sharing._

In this model, only one person is "hosting" the trip. The other person is merely looking for a trip to join.

### How it works:

1. **User A (Host)** creates a `Travel` route (e.g., Office to Home). This is saved to the database.
2. **User B (Seeker)** opens the app, enters a source and destination, and hits a `GET /search-trips` endpoint.
   - _Crucial difference_: User B **does not** create their own `Travel` record in the database.
3. The system finds User A's `Travel` record using spatial queries and returns it to User B.
4. User B clicks "Request to Join" on User A's trip.
5. A `Request` is created:
   - `travel_id` = **User A's** `Travel` ID
   - `sent_by` = User B's user ID
   - `sent_to` = User A's user ID
6. User A accepts the request.

### Database Changes:

No changes required to your existing `Travel` and `Request` models. The change is purely in the API logic and Frontend flow.

---

## Solution 2: The "Travel Companion" Flow (Peer-to-Peer Model)

_Best suited for: Finding walking companions, study buddies, or mutual travel partners where both users have equal standing and independent plans._

If your app requires both users to create their own `Travel` plans (e.g., two women walking the same route for safety), the `Request` model must be updated to link **both** trips together.

### How it works:

1. **User A** creates Travel A (saved to DB).
2. **User B** creates Travel B (saved to DB).
3. The system identifies an overlap (time and route) and recommends them to each other.
4. User A clicks "Connect with User B".
5. A `Request` is generated that references both distinct trips.

### Database Changes:

Update your `app/models/request.py`:

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base
from sqlalchemy.orm import relationship

class Request(Base):
    __tablename__ = "requests"

    request_id = Column(Integer, primary_key=True, index=True)

    # Replaces single travel_id: link both matching trips
    sender_travel_id = Column(Integer, ForeignKey("travels.travel_id"), nullable=False)
    receiver_travel_id = Column(Integer, ForeignKey("travels.travel_id"), nullable=False)

    sent_by = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    sent_to = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    status = Column(String, default="pending")
    # values: pending / accepted / rejected

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    sender_travel = relationship("Travel", foreign_keys=[sender_travel_id])
    receiver_travel = relationship("Travel", foreign_keys=[receiver_travel_id])
    sender = relationship("User", foreign_keys=[sent_by])
    receiver = relationship("User", foreign_keys=[sent_to])
```

---

## Solution 3: The Role-Based Travel Flow

_Best suited for: Applications where you want a complete historical record of all searches and trips, but still need to differentiate between who is hosting and who is joining._

In this model, everyone creates a `Travel` record, but they must explicitly declare their intent (their "Role").

### How it works:

1. The `Travel` model gets a new column: `travel_type` (`OFFERING` vs `SEEKING`).
2. Only `Travel` records marked as `OFFERING` can act as the host trip.
3. Users who create a `SEEKING` trip use it to find overlapping `OFFERING` trips.
4. When a request is made, the `Request.travel_id` always points to the `OFFERING` user's travel ID.

### Database Changes:

Update your `app/models/travel.py`:

```python
class Travel(Base):
    __tablename__ = "travels"

    travel_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    # NEW: Differentiate the intent of the trip
    travel_type = Column(String, nullable=False, default="SEEKING") # 'OFFERING' or 'SEEKING'

    start_label = Column(String, nullable=False)
    end_label = Column(String, nullable=False)
    # ... rest of your columns ...
```

---

## Recommendation

- **For Peer Safety / Walking Companions** (e.g., SheConnect context usually implies mutual peer-to-peer safety networks): Go with **Solution 2 (Travel Companion Flow)**. It allows two independent users to propose a route and the system dynamically connects them together.
- **For Ride-Sharing (Vehicle context):** Go with **Solution 1 (Search & Request Flow)**. Passengers shouldn't clutter the exact same `travels` table just to perform a map search.
