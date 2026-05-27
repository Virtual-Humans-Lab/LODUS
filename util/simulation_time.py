from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationTimeStatus:
    """Represents the current simulation time snapshot."""

    simulation_step: int
    cycle_length: int
    total_cycles: int

    @property
    def cycle_step(self) -> int:
        """Returns the zero-based step index within the current cycle."""
        return self.simulation_step % self.cycle_length

    @property
    def cycle(self) -> int:
        """Returns the zero-based cycle index for the current simulation step."""
        return self.simulation_step // self.cycle_length

    @property
    def is_cycle_start(self) -> bool:
        """Returns True when the current step is the first step of a cycle."""
        return self.cycle_step == 0
    
    @property
    def is_cycle_end(self) -> bool:
        """Returns True when the current step is the last step of a cycle."""
        return self.cycle_step == self.cycle_length - 1
    
    @property
    def is_final_step(self) -> bool:
        """Returns True when the current step is the last step of the simulation."""
        return self.simulation_step == self.cycle_length * self.total_cycles - 1
    

    
