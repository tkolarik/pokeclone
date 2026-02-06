from src.overworld.state import MapData, MapLayer
from src.overworld.world_view import AUTO_FLAG, WorldView


def _build_map(map_id: str) -> MapData:
    return MapData(
        map_id=map_id,
        name=map_id,
        version="1.0.0",
        tile_size=32,
        dimensions=(4, 4),
        tileset_id="basic_overworld",
        layers=[
            MapLayer(name="ground", tiles=[[None for _ in range(4)] for _ in range(4)]),
            MapLayer(name="overlay", tiles=[[None for _ in range(4)] for _ in range(4)]),
        ],
        connections=[],
        entities=[],
        triggers=[],
        overrides={},
    )


def test_add_auto_edge_records_source_edge_coordinate_metadata():
    source = _build_map("source")
    WorldView._add_auto_edge(
        WorldView.__new__(WorldView),
        source_map=source,
        direction="up",
        target_id="target",
        spawn={"x": 1, "y": 3},
        facing="up",
        x_tag=1,
    )

    assert len(source.connections) == 1
    connection = source.connections[0]
    assert connection.from_ref == "up"
    assert connection.extra["auto"] == AUTO_FLAG
    assert connection.extra["sourceEdgeCoord"] == 1
