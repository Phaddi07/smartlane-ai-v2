# Smartlane AI — Development Roadmap

## 1. Project Vision

Smartlane AI is an AI-powered driving analysis system designed to operate primarily as a dashcam application.

During a drive, the application records the road while the AI processes the scene in the background.

After the drive, Smartlane AI generates:

- A trip report
- A trip safety score out of 1000
- Detected driving behaviors
- Detected incidents
- Responsibility analysis
- Explanations for important events

The trip score is then used to update the driver's overall score.

---

## 2. System Pipeline

The complete Smartlane AI pipeline is:

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

Each stage has a defined responsibility and communicates with other stages through shared data contracts.

---

## 3. Phase 0 — Project Foundation

Status: COMPLETE

Completed:

- Repository created
- GitHub repository established
- Python environment established
- Project structure created
- Configuration structure created
- Initial requirements defined
- Architecture established

---

## 4. Phase 1 — Contract and Documentation Layer

Status: IN PROGRESS

### Documentation

- [x] ARCHITECTURE.md
- [x] DATA_CONTRACTS.md
- [x] AI_CONTEXT.md
- [x] DEVELOPMENT_GUIDE.md
- [ ] ROADMAP.md

### JSON Schemas

- [x] vehicle_track.schema.json
- [x] ego_state.schema.json
- [x] lane_geometry.schema.json
- [x] behavior_event.schema.json
- [x] interaction.schema.json
- [x] incident.schema.json
- [x] responsibility.schema.json
- [x] driver_score.schema.json
- [x] trip_report.schema.json

### Remaining Work

- Complete ROADMAP.md
- Validate all documentation
- Validate all JSON schemas
- Create mock data
- Validate mock data against schemas
- Perform final contract review
- Commit the contract layer

---

## 5. Phase 2 — Mock Data and Contract Validation

Status: NOT STARTED

Purpose:

Prove that all modules can communicate using the agreed contracts before real implementation begins.

Tasks:

- Create representative mock ego state
- Create representative mock vehicle tracks
- Create representative lane geometry
- Create representative behavior events
- Create representative interactions
- Create representative incidents
- Create representative responsibility results
- Create representative driver scores
- Create representative trip reports
- Validate all mock objects against schemas
- Test the complete mock pipeline

Target flow:

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

---

## 6. Phase 3 — Ingestion

Owner: Person 1

Status: NOT STARTED

Goals:

- Read input video
- Detect video metadata
- Decode frames
- Provide reliable timestamps
- Handle different resolutions
- Handle different FPS values
- Handle different video formats

Important requirement:

The system must use the actual FPS of the input video.

It must never assume FPS = 30.

---

## 7. Phase 4 — Perception and Tracking

Owner: Person 1

Status: NOT STARTED

Goals:

- Detect vehicles
- Track vehicles across frames
- Maintain stable vehicle IDs
- Identify the ego vehicle
- Produce bounding boxes
- Track vehicle positions
- Preserve confidence information

Primary outputs:

- vehicle_track
- ego_state

---

## 8. Phase 5 — Scene and Geometry

Owner: Person 1

Status: NOT STARTED

Goals:

- Detect road geometry
- Detect lanes
- Estimate lane positions
- Estimate vehicle distances
- Estimate relative positions
- Estimate relative speed
- Calculate time headway where possible

Primary output:

- lane_geometry

Geometry should provide measurements to downstream modules without deciding whether a behavior is dangerous.

---

## 9. Phase 6 — Behavior Analysis

Owner: Person 2

Status: NOT STARTED

Goals:

- Detect following behavior
- Detect tailgating
- Detect hard braking
- Detect sudden acceleration
- Detect rapid closing
- Detect rapid separation
- Detect lane changes
- Group temporal behavior
- Assign appropriate confidence

Primary output:

- behavior_event

Behavior analysis describes observed driving behavior.

It does not assign responsibility.

---

## 10. Phase 7 — Interaction Analysis

Owner: Person 3

Status: NOT STARTED

Goals:

- Identify interacting vehicles
- Associate behavior events with vehicle pairs
- Build interaction timelines
- Track interaction state
- Determine when interactions begin and end
- Combine multiple observations into meaningful interactions

Primary output:

- interaction

---

## 11. Phase 8 — Incident Reasoning

Owner: Person 3

Status: NOT STARTED

Goals:

- Evaluate interactions
- Combine behavior evidence
- Analyze temporal context
- Detect potential conflicts
- Detect near-collision situations
- Detect collision situations
- Determine incident severity
- Preserve supporting evidence

Primary output:

- incident

Important principle:

A behavior event is not automatically an incident.

Incident reasoning must use context.

---

## 12. Phase 9 — Responsibility Analysis

Owner: Person 3

Status: NOT STARTED

Goals:

- Determine ego contribution
- Determine other-vehicle contribution
- Identify shared responsibility
- Identify situations where responsibility cannot be determined
- Preserve evidence supporting the decision

Possible outcomes:

- EGO
- OTHER
- SHARED
- UNCERTAIN
- NONE

Primary output:

- responsibility

---

## 13. Phase 10 — Driver Scoring

Owner: Person 3

Status: NOT STARTED

Goals:

- Start each trip at 1000
- Apply validated event penalties
- Account for severity
- Prevent duplicate penalties
- Handle overlapping events
- Produce an explainable score breakdown
- Generate final trip rating

Primary output:

- driver_score

The scoring system must operate on validated events and incidents rather than raw detector outputs.

---

## 14. Phase 11 — Trip Reporting

Owner: Person 3

Status: NOT STARTED

Goals:

- Generate trip summary
- List important events
- Describe incidents
- Explain responsibility
- Explain score changes
- Generate driver feedback
- Produce final trip score
- Produce overall driver score update

Primary output:

- trip_report

---

## 15. Phase 12 — Frontend / Dashcam Application

Owner: Person 4

Status: NOT STARTED

The application should primarily function as a dashcam.

During driving:

Camera
↓
Recording
↓
Background AI processing
↓
Live driving state

After driving:

Drive ends
↓
Analysis finalized
↓
Trip report generated
↓
Trip score generated
↓
Overall driver score updated

Frontend responsibilities include:

- Camera interface
- Recording
- Drive session management
- AI processing status
- Trip completion
- Trip report
- Score visualization
- Driver history
- Overall driver score

---

## 16. Phase 13 — Backend and Frontend Integration

Status: NOT STARTED

Goals:

- Define application/backend boundary
- Connect live drive sessions
- Connect AI processing state
- Deliver trip reports
- Deliver scores
- Handle processing errors
- Handle incomplete analysis
- Maintain contract compatibility

Target flow:

APP
↓
DRIVE SESSION
↓
AI PIPELINE
↓
TRIP REPORT
↓
APP

---

## 17. Phase 14 — Real-Time AI Processing

Status: FUTURE

Goal:

Move the system from primarily offline video analysis toward live dashcam analysis.

Requirements:

- Live frame ingestion
- Real-time vehicle tracking
- Persistent tracking IDs
- Low-latency behavior analysis
- Background processing
- GPU acceleration
- CPU/GPU resource management
- Graceful performance degradation

The system should prioritize reliable analysis over processing every frame at maximum complexity.

---

## 18. Phase 15 — Validation

Status: FUTURE

The system must be tested against diverse real-world scenarios.

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

### Behaviors

- Normal following
- Tailgating
- Hard braking
- Sudden acceleration
- Rapid closing
- Rapid separation
- Lane changes

### Safety Events

- Near collisions
- Collisions

### Conditions

- Day
- Night
- Different resolutions
- Different FPS values

---

## 19. Phase 16 — Performance Optimization

Status: FUTURE

Measure:

- Processing FPS
- End-to-end latency
- CPU usage
- GPU usage
- GPU memory
- System memory
- Detection throughput
- Tracking stability
- Behavior detection accuracy
- Incident detection accuracy

Optimization should happen after correctness has been established.

---

## 20. Phase 17 — Productization

Status: FUTURE

Potential future capabilities:

- Persistent driver profiles
- Long-term driver score history
- Driving behavior trends
- Personalized feedback
- Multiple driving sessions
- Cloud synchronization
- Privacy controls
- Production deployment
- Monitoring
- Application packaging

---

## 21. Immediate Execution Plan

The immediate development sequence is:

1. Complete ROADMAP.md
2. Validate all documentation
3. Validate all nine JSON schemas
4. Create mock data
5. Validate mock data
6. Run complete contract tests
7. Review all changes
8. Commit the contract layer
9. Create team development branches
10. Begin parallel implementation

No production implementation should begin until the contract layer has been validated.

---

## 22. Long-Term Goal

The final system should transform:

Raw dashcam video
↓
Reliable observations
↓
Spatial understanding
↓
Driving behaviors
↓
Vehicle interactions
↓
Incidents
↓
Responsibility
↓
Driver score
↓
Human-readable report
↓
Long-term driver profile

The objective is not simply to detect vehicles or isolated events.

The objective is to understand driving behavior and vehicle interactions well enough to produce reliable, explainable, and useful driver-safety analysis.