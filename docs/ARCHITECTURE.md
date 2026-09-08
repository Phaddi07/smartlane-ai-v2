# Smartlane AI Archi(.venv) PS C:\Users\pragu\Desktop\smartlane-ai-v2> tree docs schemas mock_data

Too many parameters - schemastecture

## 1. Purpose

Smartlane AI is an AI-powered driving analysis system designed to operate primarily as a live dashcam application.

The system observes the road while driving, analyzes vehicle movement and driver behavior, detects interactions and incidents, evaluates the contribution of the POV driver, and generates a driver safety score and trip report.

The long-term product flow is:

Camera → Live AI Analysis → Trip Analysis → Driver Report → Overall Driver Score

---

## 2. System Pipeline

The canonical Smartlane AI pipeline is:

1. Ingestion
2. Perception
3. Geometry and calibration
4. Behavior analysis
5. Vehicle interaction analysis
6. Incident construction
7. Responsibility assessment
8. Driver scoring
9. Report generation
10. Application presentation

Conceptually:

```text
Camera / Video
      ↓
Ingestion
      ↓
Perception
 ┌───────────────┐
 │ Detection     │
 │ Tracking      │
 │ Ego state     │
 │ Scene state   │
 └───────┬───────┘
         ↓
Geometry / Calibration
         ↓
Behavior Analysis
         ↓
Interaction Analysis
         ↓
Incident Construction
         ↓
Responsibility Assessment
         ↓
Driver Scoring
         ↓
Trip Report
         ↓
Application
```

---

## 3. Module Ownership

### Person 1: Perception and Tracking

Responsibilities:

* Video ingestion
* Video metadata
* Vehicle detection
* Multi-object tracking
* Vehicle observations
* Vehicle tracks
* Ego vehicle state
* Scene understanding
* Lane context
* Geometry and calibration
* Distance estimation
* Relative speed estimation
* Time headway estimation

Primary modules:

```text
src/smartlane/ingestion/
src/smartlane/tracking/
src/smartlane/scene/
src/smartlane/geometry/
```

---

### Person 2: Behavior Analysis

Responsibilities:

* Braking detection
* Acceleration detection
* Following behavior
* Tailgating
* Lane changes
* Cut-ins
* Merging
* Sudden movements
* Behavior event generation

Primary output:

```text
BehaviorEvent[]
```

Primary module:

```text
src/smartlane/behavior/
```

---

### Person 3: Interaction, Incident, Responsibility and Scoring

Responsibilities:

* Vehicle interaction analysis
* Interaction grouping
* Incident construction
* Incident severity
* Collision/near-collision reasoning
* Driver responsibility
* Risk scoring
* Driver score generation

Primary modules:

```text
src/smartlane/interaction/
src/smartlane/incidents/
src/smartlane/responsibility/
src/smartlane/scoring/
```

---

### Person 4: Application

Responsibilities:

* Dashcam interface
* Live analysis status
* Driving session management
* Trip report UI
* Score display
* Event timeline
* Overall driver score
* Backend/API integration

The application consumes the official Smartlane output contracts.

---

## 4. Data Flow

Modules communicate through structured data contracts.

The important boundaries are:

```text
VideoMetadata
      ↓
VehicleTrack[]
EgoState[]
SceneState[]
LaneContext[]
      ↓
BehaviorEvent[]
      ↓
Interaction[]
      ↓
Incident[]
      ↓
ResponsibilityAssessment[]
      ↓
DriverScore
      ↓
DriverReport
```

No module should depend on another module's internal implementation.

---

## 5. Design Principles

### Contract-first development

Interfaces are defined before implementation.

### No hard-coded video assumptions

The system must not assume:

* fixed FPS
* fixed resolution
* fixed camera
* fixed video duration
* fixed number of vehicles
* fixed track IDs

### Track IDs are temporary identifiers

A track ID is valid only within its processing session unless a future identity layer explicitly defines otherwise.

### Evidence-based reasoning

Behavior and incident decisions should retain numerical or structured evidence where possible.

### Confidence-aware processing

AI outputs should include confidence values where meaningful.

### Graceful uncertainty

The system must support:

```text
UNKNOWN
INDETERMINATE
INSUFFICIENT_EVIDENCE
```

rather than forcing unsupported conclusions.

### Real-time compatibility

The architecture must support both:

* batch video processing
* live camera processing

The analysis modules should not fundamentally depend on the input being a pre-recorded video.

---

## 6. Current Experimental Code

The existing experimental scripts are valuable research/prototyping code.

They must not be treated as the final architecture.

Examples include:

```text
src/track_vehicles.py
src/track_vehicles_caronly.py
src/extract_incident_events.py
src/build_incident_timeline.py
src/analyze_incident_interaction.py
src/characterize_incidents.py
```

Their validated logic may later be migrated into the appropriate `src/smartlane/` modules.

Experimental scripts may contain:

* hard-coded track IDs
* hard-coded frame ranges
* hard-coded FPS
* CSV-specific assumptions
* temporary thresholds

These assumptions must be removed before production integration.

---

## 7. Application Architecture

The intended product architecture is:

```text
                SMARTLANE APP
                     │
              Camera / Dashcam
                     │
                     ▼
             Smartlane AI Engine
                     │
        ┌────────────┴────────────┐
        │                         │
   Live Analysis             Trip Analysis
        │                         │
        └────────────┬────────────┘
                     ▼
                Trip Report
                     │
                     ▼
             Overall Driver Score
```

The live system should eventually process frames continuously while the trip is occurring.

The trip report is generated after the driving session.

The overall driver score is updated from completed trips.

---

## 8. Non-Goals for the Current Prototype

The current prototype does not need to solve perfectly:

* universal road understanding
* perfect accident reconstruction
* perfect responsibility attribution
* global vehicle identity
* production-grade mobile deployment
* every possible traffic scenario

The goal is a strong, measurable prototype with clear evidence and interpretable results.
