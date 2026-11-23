from __future__ import annotations
from smartlane.responsibility.assessor import ResponsibilityAssessor
from smartlane.incidents.collision_detector import CollisionDetector
from smartlane.behavior.motion_state import MotionStateAnalyzer
from smartlane.models import (
    BehaviorEvent,
    BehaviorSubject,
    BehaviorType,
    ValidatedBehavior,
)
from smartlane.behavior.motion_signal import MotionSignalAnalyzer
from smartlane.behavior.ego_motion import EgoMotionEstimator

import json
from dataclasses import asdict
from enum import Enum
from pathlib import Path

from smartlane.tracking import VehicleTracker
from smartlane.tracking.visualizer import annotate_tracking_video
from smartlane.behavior.following import FollowingAnalyzer
from smartlane.behavior.lane_change import EgoLanePositionAnalyzer
from smartlane.geometry.analyzer import GeometryAnalyzer
from smartlane.scoring.engine import ScoringEngine
from smartlane.reporting.generator import ReportGenerator


class SmartLanePipeline:
    def __init__(self, video_path: str | Path):
        self.video_path = Path(video_path)

        self.output_dir = Path("data/processed")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.ego_motion_results = None
        self.motion_signal_results = None
        self.motion_state_results = None
        self.video_metadata = None
        self.tracking_output = None
        self.frame_tracks = []
        self.lane_contexts = []
        self.geometry_results = None
        self.lane_position_results = None

        self.behavior_events = []
        self.validated_behaviors: list[ValidatedBehavior] = []
        self.incidents = []
        self.responsibility_assessments = []

        self.driver_score = None
        self.report = None

    def ingest(self):
        print("\n[1/6] Preparing video...")

        if not self.video_path.is_file():
            raise FileNotFoundError(
                f"Video not found: {self.video_path}"
            )

    def detect_and_track(self):
        print("[2/6] Detecting and tracking vehicles...")

        self.tracking_output = VehicleTracker().process_video(
            self.video_path
        )

        self.video_metadata = self.tracking_output.metadata
        self.frame_tracks = self.tracking_output.frame_tracks

        print(f"      Frames processed: {len(self.frame_tracks)}")
        print(
            f"      Unique vehicles: "
            f"{len(self.tracking_output.vehicle_tracks)}"
        )

    def analyze_geometry(self):
        print("[3/6] Detecting and tracking lane boundaries...")

        self.geometry_results = GeometryAnalyzer().process_video(
            self.video_path
        )

        self.lane_contexts = self.geometry_results["contexts"]

        print(
            f"      Geometry frames: "
            f"{self.geometry_results['frames_processed']}"
        )
        print(
            f"      Frames with lane boundaries: "
            f"{self.geometry_results['frames_with_boundaries']}"
        )
        print(
            f"      Boundary detection coverage: "
            f"{self.geometry_results['detection_rate'] * 100:.2f}%"
        )

    def analyze_behavior(self):
        print("[4/6] Analysing driving behaviour...")



        self.lane_position_results = EgoLanePositionAnalyzer().analyze(
            contexts=self.lane_contexts,
            frame_width=self.video_metadata.width,
        )


        print(
            f"      Frames with lateral-position measurements: "
            f"{self.lane_position_results['frames_with_position']}"
        )
        print(
            f"      Lateral-position coverage: "
            f"{self.lane_position_results['coverage'] * 100:.2f}%"
        )
        self.ego_motion_results = EgoMotionEstimator().process_video(
            video_path=self.video_path,
            frame_tracks=self.frame_tracks,
        )

        print(
            f"      Valid ego-motion measurements: "
            f"{self.ego_motion_results['valid_measurement_count']}"
        )
        print(
            f"      Ego-motion coverage: "
            f"{self.ego_motion_results['coverage'] * 100:.2f}%"
        )
        self.motion_signal_results = MotionSignalAnalyzer().analyze(
            self.ego_motion_results
        )

        print(
            f"      Reliable motion measurements: "
            f"{self.motion_signal_results['reliable_measurement_count']}"
        )
        print(
            f"      Motion signal reliability coverage: "
            f"{self.motion_signal_results['reliable_coverage'] * 100:.2f}%"
        )
        self.motion_state_results = MotionStateAnalyzer().analyze(
            self.motion_signal_results
        )
        following_events = FollowingAnalyzer().analyze(
            tracking_output=self.tracking_output,
            motion_state_results=self.motion_state_results,
        )

        # Convert persistent deceleration flags into candidate event segments.
        measurements = self.motion_signal_results.get("measurements", [])
        active = [
            item for item in measurements
            if item.get("deceleration_candidate")
            and item.get("reliable")
        ]

        groups = []
        for item in active:
            if (
                not groups
                or item["frame_number"] > groups[-1][-1]["frame_number"] + 1
            ):
                groups.append([item])
            else:
                groups[-1].append(item)

        braking_events = []

        for group in groups:
            start = group[0]
            end = group[-1]
            duration = end["timestamp_seconds"] - start["timestamp_seconds"]

            # Reject short, noisy detections.
            if duration < 0.15 or len(group) < 4:
                continue

            changes = [
                item["radial_relative_change"]
                for item in group
                if item.get("radial_relative_change") is not None
            ]

            braking_events.append(
                BehaviorEvent(
                    event_id=f"deceleration_candidate_{start['frame_number']}",
                    behavior_type=BehaviorType.BRAKING,
                    subject=BehaviorSubject(type="ego", id=None),
                    start_frame=start["frame_number"],
                    end_frame=end["frame_number"],
                    start_time_seconds=start["timestamp_seconds"],
                    end_time_seconds=end["timestamp_seconds"],
                    confidence=0.35,
                    evidence={
                        "classification": "possible_deceleration_candidate",
                        "detection_method": "persistent_radial_flow_reduction",
                        "duration_seconds": round(duration, 3),
                        "minimum_radial_relative_change": (
                            round(min(changes), 3) if changes else None
                        ),
                        "sample_count": len(group),
                        "confirmed_braking": False,
                        "limitations": [
                            "Vehicle braking is not directly measured.",
                            "Deceleration magnitude is not calibrated.",
                            "Road and camera motion may affect optical flow.",
                            "Hard braking is not established.",
                        ],
                    },
                )
            )

        self.behavior_events = following_events + braking_events

        print(f"      Candidate following events: {len(following_events)}")
        print(f"      Possible deceleration events: {len(braking_events)}")

        print(f"      Total behavior events: {len(self.behavior_events)}")

        print("      Motion-state candidates:")
        for state, count in self.motion_state_results["state_counts"].items():
            print(f"        {state}: {count}")
        self.incidents = CollisionDetector().analyze(
            tracking_output=self.tracking_output,
            motion_state_results=self.motion_state_results,
        )

        print(
            f"      Collision candidates detected: "
            f"{len(self.incidents)}"
        )

        for incident in self.incidents:
            print(
                f"        Candidate at "
                f"{incident.start_time_seconds:.2f}s"
            )
        self.responsibility_assessments = (
            ResponsibilityAssessor().analyze(self.incidents)
        )

        print(
            f"      Responsibility assessments: "
            f"{len(self.responsibility_assessments)}"
        )

        for assessment in self.responsibility_assessments:
            print(
                f"        {assessment.incident_id}: "
                f"{assessment.classification.value}"
            )

    def calculate_score(self):
        print("[5/6] Calculating preliminary score...")

        self.driver_score = ScoringEngine().calculate(
            self.behavior_events,
            self.incidents,
            validated_behaviors=self.validated_behaviors,
        )

        print(
            f"      Scoring status: "
            f"{self.driver_score.scoring_status}"
        )
        print(
            f"      Validated evidence coverage: "
            f"{self.driver_score.evidence_coverage:.1%}"
        )
        print(
            f"      Driving score: "
            f"{self.driver_score.score if self.driver_score.score is not None else 'Not evaluated'}"
        )

    def generate_report(self):
        print("[6/6] Generating report...")

        self.report = ReportGenerator().generate(
            metadata=self.video_metadata,
            score=self.driver_score,
            behavior_events=self.behavior_events,
            incidents=self.incidents,
            responsibility_assessments=self.responsibility_assessments,
        )

        video_name = self.video_path.stem

        report_path = self.output_dir / f"{video_name}_report.json"
        annotated_path = (
            self.output_dir / f"{video_name}_annotated.mp4"
        )
        geometry_path = (
            self.output_dir / f"{video_name}_geometry.json"
        )
        lane_position_path = (
            self.output_dir / f"{video_name}_lane_position.json"
        )
        ego_motion_path = (
            self.output_dir / f"{video_name}_ego_motion.json"
        )
        motion_signal_path = (
            self.output_dir / f"{video_name}_motion_signal.json"
        )
        motion_state_path = (
            self.output_dir / f"{video_name}_motion_state.json"
        )

        with ego_motion_path.open("w", encoding="utf-8") as file:
            json.dump(
                self.ego_motion_results,
                file,
                indent=4,
            )
        with motion_signal_path.open("w", encoding="utf-8") as file:
            json.dump(
                self.motion_signal_results,
                file,
                indent=4,
            )
        with motion_state_path.open("w", encoding="utf-8") as file:
            json.dump(
                self.motion_state_results,
                file,
                indent=4,
            )

        report_data = asdict(self.report)

        def serialize(value):
            if isinstance(value, Enum):
                return value.value

            raise TypeError(
                f"Cannot serialize {type(value).__name__}"
            )

        with report_path.open("w", encoding="utf-8") as file:
            json.dump(
                report_data,
                file,
                indent=4,
                default=serialize,
            )

        geometry_data = {
            "frames_processed": self.geometry_results["frames_processed"],
            "frames_with_boundaries": self.geometry_results["frames_with_boundaries"],
            "detection_rate": self.geometry_results["detection_rate"],
            "geometry_measurement_count": self.geometry_results[
                "geometry_measurement_count"
            ],
            "frames": [
                asdict(context)
                for context in self.lane_contexts
        ],
    "road_geometry": self.geometry_results["road_geometry"],
}

        with geometry_path.open("w", encoding="utf-8") as file:
            json.dump(
                geometry_data,
                file,
                indent=4,
                default=serialize,
            )

        with lane_position_path.open("w", encoding="utf-8") as file:
            json.dump(
                self.lane_position_results,
                file,
                indent=4,
            )

        print("      Creating annotated tracking video...")

        video_result = annotate_tracking_video(
            self.video_path,
            self.tracking_output,
            annotated_path,
            incidents=self.incidents,
            lane_contexts=self.lane_contexts,
            behavior_events=self.behavior_events,
        )

        print(f"\nReport saved: {report_path}")
        print(f"Geometry saved: {geometry_path}")
        print(f"Lane position saved: {lane_position_path}")
        print(f"Annotated video saved: {video_result['output_path']}")
        print(f"Ego-motion saved: {ego_motion_path}")
        print(f"Motion signal saved: {motion_signal_path}")
        print(f"Motion state saved: {motion_state_path}")

        return self.report

    def run(self):
        print("\n========== SMARTLANE AI ==========")

        self.ingest()
        self.detect_and_track()
        self.analyze_geometry()
        self.analyze_behavior()
        self.calculate_score()
        self.generate_report()

        print("\n========== ANALYSIS COMPLETE ==========")

        return self.report
