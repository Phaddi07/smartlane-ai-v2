# Smartlane AI Data Contracts

## 1. Purpose

This document defines the data contracts shared between all Smartlane AI modules.

The schemas in `schemas/` are the source of truth.

Every module must produce data that follows these contracts.

The contracts are designed to support both:

- Batch video processing
- Live dashcam processing

---

## 2. Core Pipeline

Smartlane AI processes driving data through the following stages:

VIDEO
↓
INGESTION
↓
PERCEPTION
↓
GEOMETRY
↓
BEHAVIOR
↓
INTERACTION
↓
INCIDENT REASONING
↓
RESPONSIBILITY
↓
SCORING
↓
REPORT
↓
APP

Each stage consumes structured data from the previous stage.

---

## 3. Contract Principles

### 3.1 Schemas are the source of truth

Python dataclasses and implementation details must follow the JSON schemas.

Experimental scripts and CSV formats are not official contracts.

### 3.2 Never assume fixed FPS

Frame numbers are useful for locating events in the source video.

Timestamps are authoritative for time-based calculations.

Modules must not assume:

- 24 FPS
- 30 FPS
- any other fixed FPS

The actual FPS comes from video metadata.

### 3.3 Never assume fixed resolution

Coordinates are expressed relative to the actual video frame.

Modules must work with different resolutions and aspect ratios.

### 3.4 Track IDs are temporary

Vehicle track IDs identify vehicles only within the current processing session.

A track ID must not be treated as a permanent real-world vehicle identity.

### 3.5 Preserve uncertainty

The system must not invent information when perception is uncertain.

Use:

- null values
- unknown classifications
- indeterminate responsibility
- confidence scores
- evidence fields

when appropriate.

### 3.6 Evidence must be preserved

Higher-level reasoning should be traceable back to lower-level observations.

Important calculations and decisions should store supporting information in `evidence`.

### 3.7 Batch and live compatibility

Contracts must not depend on processing the entire video at once.

A live pipeline may produce information incrementally.

---

# 4. Contract: Vehicle Track

Schema:

`schemas/vehicle_track.schema.json`

Owner:

Person 1 - Perception / Tracking

Purpose:

Represents the detected and tracked trajectory of one vehicle.

Contains:

- track ID
- vehicle type
- ego/non-ego classification
- first and last frame
- frame-by-frame observations
- bounding boxes
- detection confidence
- timestamps

Used by:

- Geometry
- Behavior
- Interaction
- Incident reasoning

Important rule:

A track ID is valid only for the current processing session.

---

# 5. Contract: Ego State

Schema:

`schemas/ego_state.schema.json`

Owner:

Person 1 - Perception / Geometry

Purpose:

Represents the state of the POV vehicle at a particular frame.

May contain:

- speed
- acceleration
- heading
- lane ID
- motion state
- confidence
- supporting evidence

Used by:

- Behavior
- Interaction
- Responsibility
- Scoring

Missing values are allowed when the system cannot reliably estimate them.

---

# 6. Contract: Lane Geometry

Schema:

`schemas/lane_geometry.schema.json`

Owner:

Person 1 - Geometry / Scene

Purpose:

Represents the estimated road and lane structure.

May contain:

- lane count
- ego lane
- lane boundaries
- boundary points
- confidence
- supporting evidence

Used by:

- Lane-change detection
- Merge detection
- Cut-in detection
- Interaction reasoning
- Responsibility reasoning

Lane geometry is allowed to be unknown when visual evidence is insufficient.

---

# 7. Contract: Behavior Event

Schema:

`schemas/behavior_event.schema.json`

Owner:

Person 2 - Behavior

Purpose:

Represents a detected driving behavior performed by the ego vehicle or another vehicle.

Supported behavior types:

- braking
- acceleration
- lane change
- following
- cut-in
- merge
- sudden movement

Every event identifies its subject as either:

- ego
- another tracked vehicle

The event contains:

- event ID
- subject
- time range
- frame range
- magnitude when available
- confidence
- related vehicles
- evidence

Behavior events should describe what was observed.

They should not make responsibility decisions.

---

# 8. Contract: Interaction

Schema:

`schemas/interaction.schema.json`

Owner:

Person 3 - Interaction

Purpose:

Represents meaningful interaction between the ego vehicle and another vehicle.

Possible measurements include:

- physical distance
- normalized image-space distance
- relative speed
- closing rate
- time headway
- interaction type
- confidence
- evidence

Image-space measurements and physical measurements must remain distinguishable.

A normalized image-space distance is not automatically a physical distance.

Interactions may reference behavior events.

---

# 9. Contract: Incident

Schema:

`schemas/incident.schema.json`

Owner:

Person 3 - Incident Reasoning

Purpose:

Represents a significant traffic event constructed from interactions and behavior events.

Possible types:

- collision candidate
- near collision
- unsafe following
- lane conflict
- interaction
- unknown

Possible severities:

- low
- medium
- high
- critical
- unknown

An incident may reference:

- involved vehicles
- behavior events
- interactions
- supporting evidence

Incident reasoning must not assume that a particular track ID is always the accident vehicle.

---

# 10. Contract: Responsibility Assessment

Schema:

`schemas/responsibility.schema.json`

Owner:

Person 3 - Responsibility

Purpose:

Determines the POV driver's contribution to an incident.

Possible classifications:

- `pov_primary`
- `other_vehicle_primary`
- `shared_contribution`
- `no_contribution_by_pov`
- `indeterminate`

Responsibility must be evidence-based.

The system must be able to return `indeterminate` when available evidence is insufficient.

The responsibility module should explain its decision using the `reasoning` field and supporting evidence.

---

# 11. Contract: Driver Score

Schema:

`schemas/driver_score.schema.json`

Owner:

Person 3 - Scoring

Purpose:

Converts validated driving behavior and incident information into a driver safety score.

Score range:

`0-1000`

Higher is better.

The score contains category-level scores for:

- following
- braking
- acceleration
- lane behavior
- interaction
- incidents

Ratings:

- EXCELLENT
- GOOD
- MODERATE
- POOR
- CRITICAL

Scoring must use validated events rather than raw detections.

Contextual events should not automatically become penalties.

---

# 12. Contract: Trip Report

Schema:

`schemas/trip_report.schema.json`

Owner:

Person 3 - Reporting

Consumed by:

Person 4 - Frontend / App

Purpose:

Represents the complete result of one driving session.

Contains:

- report ID
- video/session ID
- processing mode
- trip duration
- driver score
- behavior events
- incidents
- responsibility assessments
- human-readable summary
- generation timestamp

The frontend should consume this contract rather than directly reading internal tracking or behavior data.

---

# 13. Data Flow

## Perception

Input:

Video

Output:

- Vehicle Tracks
- Ego State
- Scene/Lane information

---

## Geometry

Input:

- Vehicle Tracks
- Video Metadata
- Scene information

Output:

- Ego State
- Lane Geometry
- Physical/relative measurements

---

## Behavior

Input:

- Vehicle Tracks
- Ego State
- Lane Geometry

Output:

- Behavior Events

---

## Interaction

Input:

- Vehicle Tracks
- Ego State
- Geometry
- Behavior Events

Output:

- Interactions

---

## Incident Reasoning

Input:

- Interactions
- Behavior Events
- Vehicle Tracks

Output:

- Incidents

---

## Responsibility

Input:

- Incidents
- Interactions
- Behavior Events
- Vehicle trajectories

Output:

- Responsibility Assessments

---

## Scoring

Input:

- Behavior Events
- Incidents
- Responsibility Assessments

Output:

- Driver Score

---

## Reporting

Input:

- Driver Score
- Behavior Events
- Incidents
- Responsibility Assessments

Output:

- Trip Report

---

## Frontend

Input:

- Trip Report

The frontend should not depend directly on internal AI implementation details.

---

# 14. Experimental Data vs Official Contracts

The following existing files are experimental implementations and are not official API contracts:

- `tracks.csv`
- `tracks_caronly.csv`
- `incident_interactions.csv`
- `incident_timeline.csv`
- `incident_events.csv`
- `consolidated_incidents.csv`
- other generated CSV files

These files may be used for debugging, validation and research.

They may be replaced as the v2 architecture develops.

Official inter-module communication must follow the schemas in `schemas/`.

---

# 15. Contract Change Rules

A contract change can affect multiple people.

Before changing a schema:

1. Identify which modules consume it.
2. Identify which modules produce it.
3. Update the schema.
4. Update this document.
5. Update affected Python models.
6. Update tests.
7. Update mock data if necessary.
8. Notify the affected teammates.

Do not silently change field names or meanings.

---

# 16. Current Ownership

| Area | Owner |
|---|---|
| Ingestion | Person 1 |
| Vehicle Detection | Person 1 |
| Vehicle Tracking | Person 1 |
| Ego State | Person 1 |
| Scene Understanding | Person 1 |
| Geometry | Person 1 |
| Behavior | Person 2 |
| Interaction | Person 3 |
| Incident Reasoning | Person 3 |
| Responsibility | Person 3 |
| Scoring | Person 3 |
| Reporting | Person 3 |
| Frontend/App | Person 4 |

---

# 17. Development Rule

All team members should build against the contracts and mock data rather than waiting for another person's implementation.

This allows development to happen in parallel.

The contract layer is the boundary between modules.

Implementation details may change.

The contract should remain stable unless the team explicitly changes it.