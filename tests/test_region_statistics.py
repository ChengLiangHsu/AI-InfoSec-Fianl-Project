from unittest.mock import AsyncMock

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from src.controllers.dependencies import get_task_usecase
from src.controllers.task import router
from src.entities.task import Task
from src.presenter.error_handlers import register_error_handlers
from src.usecases.task import TaskUseCase
from src.utility.formulas import get_algorithm_list, lookup_formula, normalize_rgb_formula
from src.utility.region_statistics import calculate_region_statistics
from src.utility.spectral import create_spectral_color_lut, generate_spectral_image

FULL = [(0, 0), (1, 0), (1, 1), (0, 1)]


def save_image(tmp_path, pixels):
    path = tmp_path / 'field.png'
    Image.fromarray(np.asarray(pixels, dtype=np.uint8)).save(path)
    return path


def test_polygon_excludes_bounding_box_corners_and_transparency(tmp_path):
    pixels = np.full((4, 4, 4), [20, 100, 40, 255], dtype=np.uint8)
    pixels[3, 3] = [255, 0, 0, 255]  # Inside bounding box, outside triangle.
    pixels[0, 0] = [255, 255, 255, 0]  # Inside polygon, but transparent.
    path = save_image(tmp_path, pixels)
    result = calculate_region_statistics(path, [(0, 0), (1, 0), (0, 1)])
    assert result['pixel_count'] == 5
    assert result['rgb_mean'] == [20, 100, 40]
    vari = next(a for a in result['algorithms'] if a['id'] == 'VARI')
    assert vari['index_mean'] == pytest.approx(1)
    assert vari['valid_pixel_count'] == 5


def test_every_algorithm_rgb_matches_actual_render_and_indices_are_pixel_means(tmp_path):
    path = save_image(tmp_path, [[[20, 100, 40, 255], [100, 60, 20, 255], [255, 0, 0, 0]]])
    result = calculate_region_statistics(path, FULL)
    assert result['pixel_count'] == 2
    assert result['rgb_mean'] == [60, 80, 30]
    assert {a['id'] for a in result['algorithms']} == {'NDYI', 'VARI', 'MPRI', 'EXG', 'GLI'}
    for row in result['algorithms']:
        output = tmp_path / f"{row['id']}.png"
        generate_spectral_image(path, output, row['id'])
        with Image.open(output) as rendered:
            expected = np.asarray(rendered)[0, :2, :3].mean(axis=0).round(2).tolist()
        assert row['rgb_mean'] == expected
    vari = next(a for a in result['algorithms'] if a['id'] == 'VARI')
    assert vari['index_mean'] == pytest.approx((1 - 40 / 140) / 2)


def test_undefined_index_is_not_reported_as_zero(tmp_path):
    path = save_image(tmp_path, [[[0, 0, 0, 255]]])
    result = calculate_region_statistics(path, FULL)
    assert result['rgb_mean'] == [0, 0, 0]
    vari = next(a for a in result['algorithms'] if a['id'] == 'VARI')
    assert vari['index_mean'] is None
    assert vari['valid_pixel_count'] == 0
    assert vari['rgb_mean'] is not None  # Same fallback coloring as the heatmap.


@pytest.mark.parametrize('polygon', [FULL, [(0, 0), (.01, 0), (0, .01)]])
def test_empty_region_has_no_fabricated_values(tmp_path, polygon):
    path = save_image(tmp_path, [[[10, 20, 30, 0]]])
    result = calculate_region_statistics(path, polygon)
    assert result['pixel_count'] == 0
    assert result['rgb_mean'] is None
    assert all(a['index_mean'] is None and a['rgb_mean'] is None for a in result['algorithms'])


def test_api_uses_unsaved_geometry_and_validates_input(tmp_path, monkeypatch):
    monkeypatch.setattr('src.usecases.task.ODM_DIR', tmp_path)
    save_image(tmp_path, [[[20, 100, 40, 255], [200, 0, 0, 255]]])
    repo = AsyncMock()
    repo.get_task.return_value = Task(id='field', name='Test', images=1, progress=100)
    usecase = TaskUseCase(repo, AsyncMock())
    app = FastAPI()
    app.include_router(router)
    register_error_handlers(app)
    app.dependency_overrides[get_task_usecase] = lambda: usecase
    with TestClient(app) as client:
        response = client.post('/region-statistics/field', json={'points': [(0, 0), (.5, 0), (.5, 1), (0, 1)]})
        assert response.status_code == 200
        assert response.json()['data']['rgb_mean'] == [20, 100, 40]
        repo.update_plots.assert_not_called()
        for points in [[], [[0, 0], [1, 0]], [[-1, 0], [1, 0], [0, 1]]]:
            assert client.post('/region-statistics/field', json={'points': points}).status_code == 422
        assert client.post('/region-statistics/field', json={'points': [[0, 0], [.5, .5], [1, 1]]}).status_code == 400
        repo.get_task.side_effect = KeyError('找不到專案')
        assert client.post('/region-statistics/missing', json={'points': FULL}).status_code == 404


def test_only_pure_rgb_formulas_are_executable_and_lut_blue_channel_is_zero():
    algos = get_algorithm_list()
    ids = [a['id'] for a in algos]
    assert ids == ['NDYI', 'VARI', 'MPRI', 'EXG', 'GLI']
    for item in algos:
        assert item['filters'] == ['RGB']
        assert item['limitation']
        expr, hrange = lookup_formula(item['id'])
        assert expr and hrange == (-1, 1)
        assert 'N' not in expr and 'Re' not in expr and 'L' not in expr

    assert normalize_rgb_formula('mpri') == 'MPRI'
    for unsupported in ['vNDVI', 'NDVI', 'NDRE', 'PRI', 'SAVI', 'Celsius']:
        with pytest.raises(ValueError):
            lookup_formula(unsupported)
    with pytest.raises(ValueError):
        lookup_formula('VARI', 'RGBN')

    lut = create_spectral_color_lut()
    assert lut.shape == (256, 3)
    assert np.all(lut[:, 2] == 0)


def test_formulas_endpoint_exposes_rgb_metadata():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        response = client.get('/odm-task-formulas')
        assert response.status_code == 200
        items = response.json()['data']
        assert [item['id'] for item in items] == ['NDYI', 'VARI', 'MPRI', 'EXG', 'GLI']
        by_id = {item['id']: item for item in items}
        assert 'vNDVI' not in by_id
        assert '替代' in by_id['MPRI']['badge']
        assert '531nm' in by_id['MPRI']['limitation']
