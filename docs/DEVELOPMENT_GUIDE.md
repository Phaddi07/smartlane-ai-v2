# Smartlane AI — Development Guide

## 1. Purpose

This document defines the development rules, module ownership, testing strategy, and integration process for Smartlane AI.

Smartlane AI is a modular driving-analysis system that processes dashcam footage and produces driving behavior analysis, incident reasoning, responsibility assessment, and a driver safety score.

The pipeline is:

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

---

## 2. Core Development Principles

Smartlane AI should be:

- Modular
- Testable
- Explainable
- Contract-driven
- Robust to different videos and FPS values
- Easy for multiple developers to work on simultaneously

The following rules apply to all development:

1. Modules communicate through defined data contracts.
2. Do not silently change shared contracts.
3. Do not hard-code video FPS.
4. Keep detection separate from reasoning.
5. Keep responsibility separate from incident detection.
6. Keep scoring separate from detection.
7. Preserve frame and timestamp information wherever possible.
8. Represent uncertainty explicitly.
9. Avoid duplicate penalties for the same underlying event.
10. Every major module should have tests.

---

## 3. Team Ownership

### Person 1 — Ingestion, Perception, Tracking, Scene, Geometry

Responsible for:

- Video ingestion
- Frame processing
- Video metadata
- Vehicle detection
- Vehicle tracking
- Ego vehicle state
- Scene understanding
- Lane detection
- Lane geometry
- Distance estimation
- Relative motion estimation

Primary outputs:

- ego_state
- vehicle_track
- lane_geometry

Person 1 should provide reliable observations and measurements.

Person 1 should NOT decide whether the driver was unsafe or responsible for an incident.

---

### Person 2 — Behavior

Responsible for:

- Following behavior
- Tailgating
- Hard braking
- Sudden acceleration
- Rapid closing
- Rapid separation
- Lane changes
- Temporal behavior analysis
- Behavior event confidence

Primary output:

- behavior_event

Behavior detection describes what happened.

It should NOT assign responsibility.

---

### Person 3 — Interaction, Incidents, Responsibility, Scoring, Reporting

Responsible for:

- Vehicle interactions
- Interaction timelines
- Incident reasoning
- Incident severity
- Responsibility assessment
- Driver scoring
- Trip reports
- Driver summaries

Primary outputs:

- interaction
- incident
- responsibility
- driver_score
- trip_report

---

### Person 4 — Frontend / App

Responsible for:

- Dashcam interface
- Camera access
- Drive session
- Recording controls
- Live AI status
- Trip completion
- Trip report UI
- Driver score UI
- Overall driver score
- Driver history

The frontend should consume backend contracts rather than recreate backend logic.

---

## 4. Shared Data Contracts

The schemas inside:

schemas/

are the shared contracts between modules.

The current contracts are:

- vehicle_track
- ego_state
- lane_geometry
- behavior_event
- interaction
- incident
- responsibility
- driver_score
- trip_report

When a contract changes:

1. Identify all producers.
2. Identify all consumers.
3. Update the JSON schema.
4. Update DATA_CONTRACTS.md.
5. Update mock data.
6. Update tests.
7. Verify all affected modules.

Do not change shared fields casually.

---

## 5. Pipeline Responsibilities

### Ingestion

Responsible for understanding the input video.

Output includes information such as:

- FPS
- Resolution
- Frame count
- Duration
- Frame timestamps

---

### Perception

Responsible for understanding what exists in the scene.

Examples:

- Vehicles
- Vehicle IDs
- Bounding boxes
- Tracking information
- Ego vehicle state

---

### Geometry

Responsible for understanding spatial relationships.

Examples:

- Vehicle distance
- Relative position
- Lane position
- Relative speed
- Time headway

---

### Behavior

Responsible for identifying driving behaviors.

Examples:

- Tailgating
- Hard braking
- Sudden acceleration
- Lane change
- Closing traffic
- Separating traffic

---

### Interaction

Responsible for understanding relationships between vehicles.

Example:

Ego vehicle
↓
Following
↓
Lead vehicle
↓
Closing
↓
Braking

---

### Incident Reasoning

Responsible for determining whether an interaction constitutes a meaningful incident.

A behavior event does NOT automatically equal an incident.

Example:

Behavior event
↓
Interaction context
↓
Temporal analysis
↓
Incident reasoning
↓
Incident

This prevents isolated detector outputs from creating false incidents.

---

### Responsibility

Responsible for determining contribution to an incident.

Possible outcomes include:

- Ego responsible
- Other vehicle responsible
- Shared responsibility
- Uncertain
- No responsibility

Responsibility must be based on available evidence.

---

### Scoring

Responsible for converting validated behavior and incident information into a driver score.

Starting score:

1000

Penalties must:

- Reflect severity
- Avoid double counting
- Account for overlapping events
- Be explainable

---

### Reporting

Responsible for converting the final analysis into a human-readable trip report.

The report should explain:

- What happened
- When it happened
- Vehicles involved
- Driver behavior
- Incident severity
- Responsibility
- Score impact

---

## 6. FPS and Timing

Never assume:

FPS = 30

The actual video FPS must be obtained from the input video.

Frame timestamps should be derived consistently:

timestamp = frame_index / fps

unless a more accurate timestamp source is available.

All time-dependent calculations must use the correct video FPS.

---

## 7. Confidence and Uncertainty

AI outputs are not automatically ground truth.

The system should distinguish between:

- Detected
- Probable
- Uncertain
- Confirmed

A weak signal should not automatically become a confirmed incident.

Where applicable, confidence should be preserved through the pipeline.

---

## 8. Incident vs Behavior

This distinction is fundamental.

A behavior event describes something the vehicle or driver did.

An incident describes a meaningful interaction or safety event resulting from contextual reasoning.

For example:

Tailgating detected
↓
Vehicle interaction identified
↓
Closing distance detected
↓
Braking/context evaluated
↓
Incident reasoning

This prevents isolated detector outputs from creating false incidents.

---

## 9. Responsibility Rules

Responsibility should consider multiple signals.

Examples:

- Relative motion
- Lane position
- Braking
- Acceleration
- Lane changes
- Timing
- Interaction history
- Available evidence

Proximity alone is not sufficient to determine responsibility.

If evidence is insufficient, responsibility should remain uncertain.

---

## 10. Scoring Rules

The driver starts each trip with:

1000

Events may reduce the score according to configured severity rules.

The scoring system must avoid double-counting.

For example, the same underlying event should not automatically receive:

- Tailgating penalty
- Closing penalty
- Incident penalty
- Braking penalty

if all of these represent the same underlying event.

Overlapping events should be handled carefully.

The score should always be explainable through its underlying events.

---

## 11. Testing

Every major module should have tests.

### Unit Tests

Test individual functions.

Examples:

- Distance calculation
- THW calculation
- Relative speed calculation
- Event classification
- Score calculation

### Contract Tests

Verify that produced objects conform to their JSON schemas.

### Integration Tests

Verify that modules work together.

Example:

vehicle_track
↓
geometry
↓
behavior_event
↓
interaction
↓
incident
↓
responsibility
↓
driver_score
↓
trip_report

### End-to-End Tests

Run the complete pipeline against real driving footage.

---

## 12. Required Test Scenarios

The system should eventually be tested on:

### Road Types

- Urban roads
- Highways
- Freeways
- Multi-lane roads
- Intersections

### Traffic

- Light traffic
- Heavy traffic
- Stop-and-go traffic
- Merging
- Cut-ins
- Lane changes
- Overtaking
- Vehicles passing on either side

### Driving Events

- Normal following
- Tailgating
- Hard braking
- Sudden acceleration
- Rapid closing
- Rapid separation
- Near collision
- Collision

### Conditions

- Day
- Night
- Different resolutions
- Different FPS values

---

## 13. Mock Data

Before the complete AI pipeline is available, modules should be testable using mock contract-compliant data.

The mock pipeline should follow:

ego_state
+
vehicle_track
+
lane_geometry
↓
behavior_event
↓
interaction
↓
incident
↓
responsibility
↓
driver_score
↓
trip_report

This allows different team members to develop modules independently.

---

## 14. Frontend Architecture

The product is primarily a dashcam application.

During a drive:

Camera
↓
Recording
↓
Live AI processing
↓
Driving analysis

After the drive:

Drive ends
↓
Analysis finalized
↓
Trip report generated
↓
Trip score generated
↓
Overall driver score updated

The frontend should display the results but should not duplicate backend reasoning.

---

## 15. Error Handling

Pipeline failures should be explicit.

Possible states include:

- SUCCESS
- PARTIAL
- FAILED
- UNCERTAIN

The system should not silently convert missing or failed data into valid-looking results.

---

## 16. Configuration

Thresholds and tunable parameters should be stored in configuration files where practical.

Examples:

- Detection thresholds
- Tracking thresholds
- Behavior thresholds
- Confidence thresholds
- Temporal windows
- Scoring penalties

Avoid scattering important constants throughout source code.

---

## 17. Logging

Logs should provide enough information to identify problems.

Where relevant, logs should include:

- Pipeline stage
- Frame number
- Timestamp
- Vehicle ID
- Event ID
- Confidence
- Warning/error information

Avoid excessive raw-data logging.

---

## 18. Definition of Done

A module is considered complete when:

- Implementation exists
- Tests exist
- Contract compatibility is verified
- Edge cases have been considered
- Mock data works
- Integration works
- Documentation is updated

---

## 19. Development Order

Development should proceed in this order:

1. Contract validation
2. Mock data
3. Perception
4. Geometry
5. Behavior
6. Interaction
7. Incident reasoning
8. Responsibility
9. Scoring
10. Reporting
11. Frontend integration
12. Real-time optimization
13. End-to-end validation

---

## 20. Main Principle

Smartlane AI is not simply an object detector.

The system must transform:

Raw video
↓
Observations
↓
Measurements
↓
Behaviors
↓
Interactions
↓
Incidents
↓
Responsibility
↓
Score
↓
Explanation

Every stage should make its reasoning and data understandable to the next stage.