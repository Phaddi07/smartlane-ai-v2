
from datetime import datetime, timezone
from uuid import uuid4

from smartlane.models import DriverReport


class ReportGenerator:

    def generate(
        self,
        metadata,
        score,
        behavior_events,
        incidents=None,
        responsibility_assessments=None,
    ) -> DriverReport:

        incidents = incidents or []
        responsibility_assessments = responsibility_assessments or []

        duration = metadata.duration_seconds

        summary = (
            f"The video analysis processed a {duration:.1f}-second "
            f"drive and identified {len(behavior_events)} "
            f"candidate driving behaviour events and "
            f"{len(incidents)} incident candidates. "
            f"Driving score has not been evaluated because "
            f"validated scoring measurements are not yet available. "
            f"Detected candidates have not automatically reduced "
            f"the score."
        )

        return DriverReport(
            report_id=str(uuid4()),
            video_id=metadata.video_id,
            processing_mode=metadata.processing_mode,
            duration_seconds=duration,
            score=score,
            behavior_events=behavior_events,
            incidents=incidents,
            responsibility_assessments=responsibility_assessments,
            summary=summary,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
