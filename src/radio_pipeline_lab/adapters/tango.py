from __future__ import annotations

from typing import Any

from ..control import PipelineControlService


def build_tango_device(service: PipelineControlService) -> type[Any]:
    """Create a small PyTango device class around the control service.

    PyTango remains optional so the scientific pipeline and tests run without a Tango
    database. This wrapper is intentionally synchronous and introductory.
    """
    try:
        from tango import AttrWriteType, DevState
        from tango.server import Device, attribute, command
    except ImportError as exc:
        raise RuntimeError("Install the 'tango' optional dependency") from exc

    class RadioPipelineDevice(Device):  # type: ignore[misc, valid-type]
        @attribute(dtype=str, access=AttrWriteType.READ)
        def run_id(self) -> str:
            return service.status().run_id

        @attribute(dtype=str, access=AttrWriteType.READ)
        def pipeline_state(self) -> str:
            return service.status().state

        @attribute(dtype=int, access=AttrWriteType.READ)
        def completed_stages(self) -> int:
            return service.status().completed_stages

        @command
        def Start(self) -> None:  # noqa: N802
            self.set_state(DevState.RUNNING)
            try:
                service.start(resume=True)
            except Exception:
                self.set_state(DevState.FAULT)
                raise
            self.set_state(DevState.ON)

        @command
        def Abort(self) -> None:  # noqa: N802
            service.abort()
            self.set_state(DevState.DISABLE)

    return RadioPipelineDevice
