from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

DEFAULT_FRAME_DURATION_MS = 100
DEFAULT_CANVAS_SIZE = (32, 32)
VALID_ANCHORS = {"attacker", "defender", "screen"}


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp_positive_int(value: Any, default: int) -> int:
    parsed = _as_int(value, default=default)
    return max(1, parsed)


def _normalize_anchor(value: Any) -> str:
    candidate = str(value or "attacker")
    if candidate not in VALID_ANCHORS:
        return "attacker"
    return candidate


def default_frame_image_path(object_id: str, frame_index: int) -> str:
    safe_object_id = str(object_id or "obj").strip() or "obj"
    return f"{safe_object_id}/frame_{frame_index:03d}.png"


@dataclass
class TimelineFrame:
    duration_ms: int = DEFAULT_FRAME_DURATION_MS
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TimelineFrame":
        payload = payload or {}
        known = {"durationMs"}
        duration_ms = _clamp_positive_int(payload.get("durationMs"), DEFAULT_FRAME_DURATION_MS)
        extra = {k: copy.deepcopy(v) for k, v in payload.items() if k not in known}
        return cls(duration_ms=duration_ms, extra=extra)

    def to_dict(self) -> dict[str, Any]:
        payload = {"durationMs": int(self.duration_ms)}
        payload.update(copy.deepcopy(self.extra))
        return payload

    def clone(self) -> "TimelineFrame":
        return TimelineFrame(duration_ms=self.duration_ms, extra=copy.deepcopy(self.extra))


@dataclass
class ObjectFrame:
    image: str = ""
    x: int = 0
    y: int = 0
    visible: bool = True
    flip_x: bool = False
    flip_y: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, object_id: str, frame_index: int) -> "ObjectFrame":
        payload = payload or {}
        known = {"image", "x", "y", "visible", "flipX", "flipY"}
        image = str(payload.get("image") or default_frame_image_path(object_id, frame_index))
        x = _as_int(payload.get("x"), default=0)
        y = _as_int(payload.get("y"), default=0)
        visible = bool(payload.get("visible", True))
        flip_x = bool(payload.get("flipX", False))
        flip_y = bool(payload.get("flipY", False))
        extra = {k: copy.deepcopy(v) for k, v in payload.items() if k not in known}
        return cls(image=image, x=x, y=y, visible=visible, flip_x=flip_x, flip_y=flip_y, extra=extra)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "image": self.image,
            "x": int(self.x),
            "y": int(self.y),
            "visible": bool(self.visible),
            "flipX": bool(self.flip_x),
            "flipY": bool(self.flip_y),
        }
        payload.update(copy.deepcopy(self.extra))
        return payload

    def clone(self) -> "ObjectFrame":
        return ObjectFrame(
            image=self.image,
            x=self.x,
            y=self.y,
            visible=self.visible,
            flip_x=self.flip_x,
            flip_y=self.flip_y,
            extra=copy.deepcopy(self.extra),
        )


@dataclass
class AnimationObject:
    object_id: str
    name: str
    anchor: str = "attacker"
    size_w: int = DEFAULT_CANVAS_SIZE[0]
    size_h: int = DEFAULT_CANVAS_SIZE[1]
    frames: list[ObjectFrame] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    size_extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AnimationObject":
        payload = payload or {}
        known = {"id", "name", "anchor", "size", "frames"}
        object_id = str(payload.get("id") or "obj")
        name = str(payload.get("name") or object_id)
        anchor = _normalize_anchor(payload.get("anchor"))
        size_payload = payload.get("size") if isinstance(payload.get("size"), dict) else {}
        size_w = _clamp_positive_int(size_payload.get("w"), DEFAULT_CANVAS_SIZE[0])
        size_h = _clamp_positive_int(size_payload.get("h"), DEFAULT_CANVAS_SIZE[1])
        size_known = {"w", "h"}
        size_extra = {k: copy.deepcopy(v) for k, v in size_payload.items() if k not in size_known}
        raw_frames = payload.get("frames") if isinstance(payload.get("frames"), list) else []
        frames = [
            ObjectFrame.from_dict(frame_payload, object_id=object_id, frame_index=frame_index)
            for frame_index, frame_payload in enumerate(raw_frames)
        ]
        extra = {k: copy.deepcopy(v) for k, v in payload.items() if k not in known}
        return cls(
            object_id=object_id,
            name=name,
            anchor=anchor,
            size_w=size_w,
            size_h=size_h,
            frames=frames,
            extra=extra,
            size_extra=size_extra,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "id": self.object_id,
            "name": self.name,
            "anchor": self.anchor,
            "size": {"w": int(self.size_w), "h": int(self.size_h)},
            "frames": [frame.to_dict() for frame in self.frames],
        }
        payload["size"].update(copy.deepcopy(self.size_extra))
        payload.update(copy.deepcopy(self.extra))
        return payload

    def clone(self) -> "AnimationObject":
        return AnimationObject(
            object_id=self.object_id,
            name=self.name,
            anchor=self.anchor,
            size_w=self.size_w,
            size_h=self.size_h,
            frames=[frame.clone() for frame in self.frames],
            extra=copy.deepcopy(self.extra),
            size_extra=copy.deepcopy(self.size_extra),
        )


@dataclass
class OnionSkinSettings:
    previous_enabled: bool = True
    next_enabled: bool = True
    previous_alpha: int = 90
    next_alpha: int = 90
    active_object_only: bool = False


@dataclass
class MoveAnimationState:
    version: str = "1.0.0"
    animation_id: str = "new_animation"
    name: str = "New Animation"
    canvas_w: int = DEFAULT_CANVAS_SIZE[0]
    canvas_h: int = DEFAULT_CANVAS_SIZE[1]
    frames: list[TimelineFrame] = field(default_factory=list)
    objects: list[AnimationObject] = field(default_factory=list)
    preview: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)
    canvas_extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def new(
        cls,
        animation_id: str,
        *,
        name: str | None = None,
        canvas_size: tuple[int, int] = DEFAULT_CANVAS_SIZE,
        object_count: int = 1,
    ) -> "MoveAnimationState":
        object_count = max(1, int(object_count))
        canvas_w = _clamp_positive_int(canvas_size[0] if len(canvas_size) > 0 else DEFAULT_CANVAS_SIZE[0], 32)
        canvas_h = _clamp_positive_int(canvas_size[1] if len(canvas_size) > 1 else DEFAULT_CANVAS_SIZE[1], 32)
        state = cls(
            animation_id=animation_id,
            name=name or animation_id.replace("_", " ").title(),
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            frames=[TimelineFrame(duration_ms=DEFAULT_FRAME_DURATION_MS)],
            objects=[],
        )
        for index in range(object_count):
            object_id = f"obj_{index + 1}"
            state.add_object(object_id=object_id, name=f"Object {index + 1}", anchor="attacker")
        state.ensure_alignment()
        return state

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MoveAnimationState":
        payload = payload or {}
        known = {"version", "id", "name", "canvas", "frames", "objects", "preview"}
        version = str(payload.get("version") or "1.0.0")
        animation_id = str(payload.get("id") or "new_animation")
        name = str(payload.get("name") or animation_id)
        canvas_payload = payload.get("canvas") if isinstance(payload.get("canvas"), dict) else {}
        canvas_w = _clamp_positive_int(canvas_payload.get("w"), DEFAULT_CANVAS_SIZE[0])
        canvas_h = _clamp_positive_int(canvas_payload.get("h"), DEFAULT_CANVAS_SIZE[1])
        canvas_known = {"w", "h"}
        canvas_extra = {k: copy.deepcopy(v) for k, v in canvas_payload.items() if k not in canvas_known}
        raw_frames = payload.get("frames") if isinstance(payload.get("frames"), list) else []
        frames = [TimelineFrame.from_dict(frame_payload) for frame_payload in raw_frames]
        raw_objects = payload.get("objects") if isinstance(payload.get("objects"), list) else []
        objects = [AnimationObject.from_dict(obj_payload) for obj_payload in raw_objects]
        preview = copy.deepcopy(payload.get("preview") if isinstance(payload.get("preview"), dict) else {})
        extra = {k: copy.deepcopy(v) for k, v in payload.items() if k not in known}
        state = cls(
            version=version,
            animation_id=animation_id,
            name=name,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            frames=frames,
            objects=objects,
            preview=preview,
            extra=extra,
            canvas_extra=canvas_extra,
        )
        state.ensure_alignment()
        return state

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "version": self.version,
            "id": self.animation_id,
            "name": self.name,
            "canvas": {"w": int(self.canvas_w), "h": int(self.canvas_h)},
            "frames": [frame.to_dict() for frame in self.frames],
            "objects": [obj.to_dict() for obj in self.objects],
            "preview": copy.deepcopy(self.preview),
        }
        payload["canvas"].update(copy.deepcopy(self.canvas_extra))
        payload.update(copy.deepcopy(self.extra))
        return payload

    def clone(self) -> "MoveAnimationState":
        return MoveAnimationState.from_dict(self.to_dict())

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    def get_object(self, object_id: str) -> AnimationObject | None:
        for obj in self.objects:
            if obj.object_id == object_id:
                return obj
        return None

    def ensure_alignment(self) -> None:
        if not self.frames:
            self.frames = [TimelineFrame(duration_ms=DEFAULT_FRAME_DURATION_MS)]
        if not self.objects:
            self.add_object(object_id="obj_1", name="Object 1", anchor="attacker")
        frame_count = len(self.frames)
        for obj in self.objects:
            obj.anchor = _normalize_anchor(obj.anchor)
            obj.size_w = _clamp_positive_int(obj.size_w, DEFAULT_CANVAS_SIZE[0])
            obj.size_h = _clamp_positive_int(obj.size_h, DEFAULT_CANVAS_SIZE[1])
            while len(obj.frames) < frame_count:
                idx = len(obj.frames)
                obj.frames.append(ObjectFrame(image=default_frame_image_path(obj.object_id, idx)))
            if len(obj.frames) > frame_count:
                obj.frames = obj.frames[:frame_count]
            for idx, frame in enumerate(obj.frames):
                if not frame.image:
                    frame.image = default_frame_image_path(obj.object_id, idx)
                frame.x = _as_int(frame.x, 0)
                frame.y = _as_int(frame.y, 0)

    def _normalize_frame_index(self, frame_index: int) -> int:
        if not self.frames:
            self.ensure_alignment()
        return max(0, min(int(frame_index), len(self.frames) - 1))

    def _next_object_id(self) -> str:
        used = {obj.object_id for obj in self.objects}
        next_index = 1
        while True:
            candidate = f"obj_{next_index}"
            if candidate not in used:
                return candidate
            next_index += 1

    def add_object(
        self,
        *,
        object_id: str | None = None,
        name: str | None = None,
        anchor: str = "attacker",
        size: tuple[int, int] | None = None,
    ) -> AnimationObject:
        candidate_id = str(object_id or self._next_object_id())
        if self.get_object(candidate_id) is not None:
            raise ValueError(f"Object id '{candidate_id}' already exists.")
        size = size or (self.canvas_w, self.canvas_h)
        size_w = _clamp_positive_int(size[0], self.canvas_w)
        size_h = _clamp_positive_int(size[1], self.canvas_h)
        obj = AnimationObject(
            object_id=candidate_id,
            name=name or candidate_id,
            anchor=_normalize_anchor(anchor),
            size_w=size_w,
            size_h=size_h,
            frames=[],
        )
        self.objects.append(obj)
        self.ensure_alignment()
        return obj

    def remove_object(self, object_id: str) -> bool:
        if len(self.objects) <= 1:
            return False
        for index, obj in enumerate(self.objects):
            if obj.object_id == object_id:
                self.objects.pop(index)
                return True
        return False

    def move_object(self, old_index: int, new_index: int) -> int:
        if not self.objects:
            return 0
        old_index = max(0, min(int(old_index), len(self.objects) - 1))
        new_index = max(0, min(int(new_index), len(self.objects) - 1))
        if old_index == new_index:
            return old_index
        obj = self.objects.pop(old_index)
        self.objects.insert(new_index, obj)
        return new_index

    def append_frame(
        self,
        *,
        duration_ms: int = DEFAULT_FRAME_DURATION_MS,
        copy_transforms: bool = True,
        copy_images: bool = False,
    ) -> int:
        self.ensure_alignment()
        self.frames.append(TimelineFrame(duration_ms=_clamp_positive_int(duration_ms, DEFAULT_FRAME_DURATION_MS)))
        new_index = len(self.frames) - 1
        for obj in self.objects:
            source = obj.frames[new_index - 1] if obj.frames else None
            if source and copy_transforms:
                new_frame = source.clone()
                if not copy_images:
                    new_frame.image = default_frame_image_path(obj.object_id, new_index)
            else:
                new_frame = ObjectFrame(image=default_frame_image_path(obj.object_id, new_index))
            obj.frames.append(new_frame)
        self.ensure_alignment()
        return new_index

    def duplicate_frame(self, frame_index: int) -> int:
        self.ensure_alignment()
        frame_index = self._normalize_frame_index(frame_index)
        insert_at = frame_index + 1
        self.frames.insert(insert_at, self.frames[frame_index].clone())
        for obj in self.objects:
            obj.frames.insert(insert_at, obj.frames[frame_index].clone())
        self.ensure_alignment()
        return insert_at

    def delete_frame(self, frame_index: int) -> bool:
        self.ensure_alignment()
        if len(self.frames) <= 1:
            return False
        frame_index = self._normalize_frame_index(frame_index)
        self.frames.pop(frame_index)
        for obj in self.objects:
            if frame_index < len(obj.frames):
                obj.frames.pop(frame_index)
        self.ensure_alignment()
        return True

    def move_frame(self, old_index: int, new_index: int) -> int:
        self.ensure_alignment()
        old_index = self._normalize_frame_index(old_index)
        new_index = self._normalize_frame_index(new_index)
        if old_index == new_index:
            return old_index
        frame = self.frames.pop(old_index)
        self.frames.insert(new_index, frame)
        for obj in self.objects:
            obj_frame = obj.frames.pop(old_index)
            obj.frames.insert(new_index, obj_frame)
        self.ensure_alignment()
        return new_index

    def set_frame_duration(self, frame_index: int, duration_ms: int) -> int:
        self.ensure_alignment()
        frame_index = self._normalize_frame_index(frame_index)
        clamped = _clamp_positive_int(duration_ms, DEFAULT_FRAME_DURATION_MS)
        self.frames[frame_index].duration_ms = clamped
        return clamped

    @staticmethod
    def onion_skin_indices(
        current_index: int,
        frame_count: int,
        *,
        previous_enabled: bool = True,
        next_enabled: bool = True,
    ) -> dict[str, int | None]:
        if frame_count <= 0:
            return {"previous": None, "next": None}
        current_index = max(0, min(int(current_index), frame_count - 1))
        previous = current_index - 1 if previous_enabled and current_index > 0 else None
        next_idx = current_index + 1 if next_enabled and current_index < frame_count - 1 else None
        return {"previous": previous, "next": next_idx}

    @staticmethod
    def stage_delta_to_object_delta(
        anchor: str,
        delta_x_stage: float,
        delta_y_stage: float,
        *,
        sprite_scale: int,
    ) -> tuple[int, int]:
        anchor = _normalize_anchor(anchor)
        if anchor in {"attacker", "defender"}:
            scale = max(1, int(sprite_scale))
            return int(round(delta_x_stage / scale)), int(round(delta_y_stage / scale))
        return int(round(delta_x_stage)), int(round(delta_y_stage))

    def apply_drag_delta(
        self,
        object_id: str,
        *,
        frame_index: int,
        delta_x_stage: float,
        delta_y_stage: float,
        apply_to_all_frames: bool = False,
        sprite_scale: int = 1,
    ) -> tuple[int, int]:
        self.ensure_alignment()
        obj = self.get_object(object_id)
        if obj is None:
            raise KeyError(f"Unknown object id '{object_id}'.")
        frame_index = self._normalize_frame_index(frame_index)
        dx, dy = self.stage_delta_to_object_delta(
            obj.anchor,
            delta_x_stage,
            delta_y_stage,
            sprite_scale=sprite_scale,
        )
        target_frames = obj.frames if apply_to_all_frames else [obj.frames[frame_index]]
        for target in target_frames:
            target.x += dx
            target.y += dy
        return dx, dy
