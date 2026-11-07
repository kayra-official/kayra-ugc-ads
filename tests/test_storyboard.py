from src.storyboard_generator import create_storyboard
def test_exactly_25_scenes():
    cfg={"storyboard":{"style":"test"}}
    board=create_storyboard({"category":"earrings"},cfg)
    assert len(board["scenes"])==25
    assert [s["scene_number"] for s in board["scenes"]]==list(range(1,26))
    assert sum(s["duration_seconds"] for s in board["scenes"])==25
