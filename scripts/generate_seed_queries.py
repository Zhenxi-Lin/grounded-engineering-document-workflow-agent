from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TypedDict


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger("generate_seed_queries")


class SeedQuery(TypedDict):
    query: str
    category: str


def build_seed_queries() -> list[SeedQuery]:
    return [
        {
            "query": "What is the difference between ROS 2 discovery and QoS, and why do they matter for distributed robotics systems?",
            "category": "factual",
        },
        {
            "query": "What frame conventions differ between PX4 and ROS 2, and what conversions are needed when sending trajectory setpoints?",
            "category": "factual",
        },
        {
            "query": "What is NITROS in Isaac ROS, and what problem is it trying to solve in accelerated ROS 2 pipelines?",
            "category": "factual",
        },
        {
            "query": "What are the main motion planning concepts in MoveIt, and how does the planning scene affect planning results?",
            "category": "factual",
        },
        {
            "query": "What safety actions can PX4 trigger when a failsafe event occurs, such as data link loss or geofence breach?",
            "category": "factual",
        },
        {
            "query": "How do I install ROS 2 Jazzy on Ubuntu 24.04 and set up the environment for beginner tutorials?",
            "category": "procedural",
        },
        {
            "query": "How do I create a ROS 2 workspace and build packages with colcon for a new project?",
            "category": "procedural",
        },
        {
            "query": "How do I build PX4 from source and launch a simulator for the first validation run?",
            "category": "procedural",
        },
        {
            "query": "How do I run the PX4 ROS 2 offboard control example from a new colcon workspace?",
            "category": "procedural",
        },
        {
            "query": "How do I set up Isaac ROS on a supported system and run an initial demo after environment setup?",
            "category": "procedural",
        },
        {
            "query": "How do I set up the MoveIt getting started tutorial workspace and build it from source?",
            "category": "procedural",
        },
        {
            "query": "PX4 build fails with a flash overflow error. What usually causes this and how can I fix it?",
            "category": "troubleshooting",
        },
        {
            "query": "A ROS 2 subscriber is not receiving PX4 topic data correctly. Could QoS incompatibility be the reason, and what should I check?",
            "category": "troubleshooting",
        },
        {
            "query": "The ros_gz_bridge clock topic is not publishing for PX4 simulation with ROS 2. What version mismatch or setup issue should I investigate?",
            "category": "troubleshooting",
        },
        {
            "query": "Isaac ROS setup is failing because the system does not meet supported platform requirements. What hardware or software constraints should I verify first?",
            "category": "troubleshooting",
        },
    ]


def write_seed_queries(output_path: Path) -> Path:
    seed_queries = build_seed_queries()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(seed_queries, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    LOGGER.info("Wrote %s seed queries to %s", len(seed_queries), output_path)
    return output_path


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    output_path = project_root / "data" / "eval" / "seed_queries.json"
    write_seed_queries(output_path)


if __name__ == "__main__":
    main()
