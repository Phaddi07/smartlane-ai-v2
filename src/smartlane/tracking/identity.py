
from __future__ import annotations

from collections import defaultdict


class TrackIdentityAssociator:
    """
    Associates fragmented tracker IDs when repeated same-frame
    detections strongly indicate duplicate boxes for one vehicle.

    Conservative first-pass method. Does not use appearance embeddings.
    """

    def __init__(
        self,
        min_shared_frames: int = 2,
        min_containment: float = 0.90,
        max_area_ratio: float = 6.0,
        max_center_distance_ratio: float = 0.45,
        max_large_box_area_ratio: float = 0.40,
    ) -> None:
        self.min_shared_frames = min_shared_frames
        self.min_containment = min_containment
        self.max_area_ratio = max_area_ratio
        self.max_center_distance_ratio = max_center_distance_ratio
        self.max_large_box_area_ratio = max_large_box_area_ratio

    def associate(self, tracking_output) -> dict[int, int]:
        pair_frames = defaultdict(set)

        width = tracking_output.metadata.width
        height = tracking_output.metadata.height
        frame_area = width * height

        for frame in tracking_output.frame_tracks:
            vehicles = frame.vehicles

            for i, first in enumerate(vehicles):
                for second in vehicles[i + 1:]:
                    if first.track_id == second.track_id:
                        continue

                    if first.vehicle_type != second.vehicle_type:
                        continue

                    metrics = self._duplicate_box_metrics(
                        first.bbox,
                        second.bbox,
                        frame_area,
                    )

                    if metrics is None:
                        continue

                    containment, area_ratio, center_ratio, large_area = metrics

                    if (
                        containment >= self.min_containment
                        and area_ratio <= self.max_area_ratio
                        and center_ratio <= self.max_center_distance_ratio
                        and large_area <= self.max_large_box_area_ratio
                    ):
                        pair = tuple(sorted((first.track_id, second.track_id)))
                        pair_frames[pair].add(frame.frame_number)

        parent = {
            track_id: track_id
            for track_id in tracking_output.vehicle_tracks
        }

        def find(track_id):
            while parent[track_id] != track_id:
                parent[track_id] = parent[parent[track_id]]
                track_id = parent[track_id]
            return track_id

        def union(first_id, second_id):
            first_root = find(first_id)
            second_root = find(second_id)

            if first_root == second_root:
                return

            # Lowest raw ID becomes the stable identity.
            root = min(first_root, second_root)
            child = max(first_root, second_root)
            parent[child] = root

        for (first_id, second_id), frames in pair_frames.items():
            if len(frames) >= self.min_shared_frames:
                union(first_id, second_id)

        identity_map = {
            track_id: find(track_id)
            for track_id in parent
        }

        for frame in tracking_output.frame_tracks:
            for vehicle in frame.vehicles:
                vehicle.identity_id = identity_map[vehicle.track_id]

        return identity_map

    @staticmethod
    def _duplicate_box_metrics(first, second, frame_area):
        def area(box):
            return max(0.0, box.width) * max(0.0, box.height)

        first_area = area(first)
        second_area = area(second)

        if min(first_area, second_area) <= 0 or frame_area <= 0:
            return None

        small, large = (
            (first, second)
            if first_area <= second_area
            else (second, first)
        )

        small_area = min(first_area, second_area)
        large_area = max(first_area, second_area)

        intersection_width = max(
            0.0,
            min(first.x2, second.x2) - max(first.x1, second.x1),
        )
        intersection_height = max(
            0.0,
            min(first.y2, second.y2) - max(first.y1, second.y1),
        )

        intersection = intersection_width * intersection_height
        containment = intersection / small_area

        area_ratio = large_area / small_area
        large_area_ratio = large_area / frame_area

        dx = small.center_x - large.center_x
        dy = small.center_y - large.center_y

        small_diagonal = (
            small.width ** 2 + small.height ** 2
        ) ** 0.5

        if small_diagonal <= 0:
            return None

        center_ratio = (dx ** 2 + dy ** 2) ** 0.5 / small_diagonal

        return (
            containment,
            area_ratio,
            center_ratio,
            large_area_ratio,
        )
