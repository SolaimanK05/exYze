import numpy as np
import pytest
import torch
from PIL import Image

from ml.model import infer
from ml.model.network import N_CLASSES, N_HEATMAPS, HourglassFloorPlan
from ml.model.predict import (
    ICON_CLASSES,
    ROOM_CLASSES,
    _turn,
    load_image,
    load_model,
    segment,
)


class Custom:
    """Not a tensor, so a weights-only load has to refuse it."""


@pytest.fixture(scope="module")
def model():
    torch.manual_seed(0)
    return HourglassFloorPlan().eval()


@pytest.fixture
def checkpoint(tmp_path, model):
    path = tmp_path / "weights.pkl"
    torch.save({"model_state": model.state_dict()}, path)
    return path


def test_output_has_all_channels_at_input_size(model):
    with torch.inference_mode():
        out = model(torch.randn(1, 3, 96, 128))
    assert out.shape == (1, N_CLASSES, 96, 128)


def test_odd_input_size_is_resized_back(model):
    image = torch.randn(1, 3, 97, 131)
    seg = segment(model, image, rotate=False)
    assert seg.rooms.shape == (97, 131)
    assert seg.icons.shape == (97, 131)


def test_only_heatmaps_go_through_sigmoid(model):
    with torch.inference_mode():
        out = model(torch.randn(1, 3, 64, 64))
    heat = out[:, :N_HEATMAPS]
    assert heat.min() >= 0 and heat.max() <= 1
    assert out[:, N_HEATMAPS:].min() < 0


def test_class_ids_stay_in_range(model):
    seg = segment(model, torch.randn(1, 3, 64, 96), rotate=True)
    assert seg.rooms.max() < len(ROOM_CLASSES)
    assert seg.icons.max() < len(ICON_CLASSES)
    assert seg.wall_mask.dtype == bool


@pytest.mark.parametrize("n", [1, 2, -1])
def test_turning_back_restores_the_tensor(n):
    t = torch.randn(1, 2, 5, 7)
    assert torch.equal(_turn(_turn(t, n), -n), t)


def test_checkpoint_round_trip(model, checkpoint):
    loaded = load_model(checkpoint)
    x = torch.randn(1, 3, 64, 64)
    with torch.inference_mode():
        assert torch.equal(loaded(x), model(x))


def test_load_refuses_a_pickled_object_unless_trusted(tmp_path, model):
    path = tmp_path / "pickled.pkl"
    torch.save({"model_state": model.state_dict(), "extra": Custom()}, path)
    with pytest.raises(Exception, match="[Ww]eights only"):
        load_model(path)
    assert load_model(path, trust_checkpoint=True) is not None


def test_load_image_scales_to_minus_one_one_and_limits_size(tmp_path):
    path = tmp_path / "plan.png"
    Image.fromarray(np.full((40, 80, 3), 255, dtype=np.uint8)).save(path)
    tensor = load_image(path, max_side=40)
    assert tensor.shape == (1, 3, 20, 40)
    assert torch.allclose(tensor, torch.ones_like(tensor))


def test_cli_writes_the_three_masks(tmp_path, checkpoint, capsys):
    img = tmp_path / "plan.png"
    Image.fromarray(
        np.random.default_rng(0).integers(0, 255, (80, 96, 3), dtype=np.uint8)
    ).save(img)
    out = tmp_path / "out"
    infer.main(
        [str(img), "--weights", str(checkpoint), "--out", str(out), "--no-rotate"]
    )
    for suffix in ("rooms", "icons", "wall"):
        assert (out / f"plan_{suffix}.png").is_file()
    assert "plan.png: 96x80" in capsys.readouterr().out


def test_cli_exits_when_weights_are_missing(tmp_path):
    with pytest.raises(SystemExit, match="weights not found"):
        infer.main([str(tmp_path / "x.png"), "--weights", str(tmp_path / "nope.pkl")])
