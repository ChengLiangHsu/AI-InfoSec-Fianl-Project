from __future__ import annotations

import asyncio
from copy import deepcopy
import io
from unittest.mock import AsyncMock
from urllib.parse import unquote
from zipfile import ZipFile

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from pypdf import PdfReader
import pytest

from src.controllers.dependencies import get_task_usecase
from src.controllers.task import router
from src.entities.task import Task
from src.presenter.error_handlers import register_error_handlers
from src.usecases.ports.odm import OdmPort
from src.usecases.ports.task import TaskPort
from src.usecases.task import TaskUseCase
from src.utility.formulas import get_algorithm_list
from src.utility.image_export import atomic_output

RGB_FORMULAS = [item['id'] for item in get_algorithm_list() if 'RGB' in item['filters']]
SPATIAL_TAGS = {
    33550: (0.1, 0.1, 0.0),
    33922: (0.0, 0.0, 0.0, 300000.0, 2600000.0, 0.0),
    34735: (1, 1, 0, 1, 1024, 0, 1, 1),
}


def source_tiff() -> bytes:
    image = Image.new('RGBA', (96, 64), (20, 120, 40, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 23, 63), fill=(0, 0, 0, 0))
    draw.rectangle((48, 0, 95, 31), fill=(160, 70, 20, 255))
    stream = io.BytesIO()
    image.save(stream, 'TIFF', tiffinfo=SPATIAL_TAGS)
    return stream.getvalue()


@pytest.fixture
def export_context(tmp_path, monkeypatch):
    monkeypatch.setattr('src.usecases.task.ODM_DIR', tmp_path)
    task = Task(id='test-task', name='試驗田 / A', images=10, progress=100, scenario={'note': 'keep'})
    repo = AsyncMock(spec=TaskPort)
    repo.get_task.return_value = task
    odm = AsyncMock(spec=OdmPort)
    original = source_tiff()
    archive = io.BytesIO()
    with ZipFile(archive, 'w') as zipped:
        zipped.writestr('odm_orthophoto/odm_orthophoto.tif', original)
    odm.download_task_assets.return_value = archive.getvalue()
    usecase = TaskUseCase(repo, odm)
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router, prefix='/api/task')
    app.dependency_overrides[get_task_usecase] = lambda: usecase
    with TestClient(app) as client:
        yield client, usecase, task, repo, odm, tmp_path, original


@pytest.mark.parametrize('formula', ['rgb', *RGB_FORMULAS])
@pytest.mark.parametrize('file_format,media_type', [
    ('tiff', 'image/tiff'), ('jpg', 'image/jpeg'), ('pdf', 'application/pdf'),
])
def test_every_layer_and_format_is_a_real_full_size_attachment(export_context, formula, file_format, media_type):
    client, _, task, repo, _, cache, original = export_context
    before = deepcopy(task)
    response = client.get(f'/api/task/odm-task-export/{task.id}', params={'formula': formula, 'format': file_format})
    assert response.status_code == 200, response.text if response.status_code != 200 else ''
    assert response.headers['content-type'] == media_type
    attachment = unquote(response.headers['content-disposition'])
    assert attachment.startswith('attachment;')
    assert '試驗田 _ A' in attachment and attachment.endswith(f'.{file_format}')
    if file_format == 'pdf':
        reader = PdfReader(io.BytesIO(response.content))
        assert len(reader.pages) == 1
        page = reader.pages[0]
        assert float(page.mediabox.width) / float(page.mediabox.height) == pytest.approx(1.5)
        assert page.images[0].image.size == (96, 64)
        assert min(page.images[0].image.getpixel((5, 5))) >= 250
    else:
        with Image.open(io.BytesIO(response.content)) as image:
            assert image.size == (96, 64)
            assert image.format == ('TIFF' if file_format == 'tiff' else 'JPEG')
            if file_format == 'tiff':
                for tag, value in SPATIAL_TAGS.items():
                    assert image.tag_v2[tag] == value
                assert image.getpixel((5, 5))[3] == 0
                if formula != 'rgb':
                    with Image.open(cache / f'{task.id}_{formula}.png') as preview:
                        assert image.tobytes() == preview.tobytes()
            else:
                assert min(image.getpixel((5, 5))) >= 250
    if formula == 'rgb' and file_format == 'tiff':
        assert response.content == original
    assert task == before
    repo.update_task.assert_not_called()
    repo.update_plots.assert_not_called()
    repo.update_scenario.assert_not_called()


@pytest.mark.parametrize('formula', ['NDVI', '../VARI', '_TESTRB', 'unknown'])
def test_invalid_or_unavailable_formula_is_rejected(export_context, formula):
    client, _, task, _, odm, _, _ = export_context
    response = client.get(f'/api/task/odm-task-export/{task.id}', params={'formula': formula})
    assert response.status_code == 400
    odm.download_task_assets.assert_not_called()


def test_incomplete_missing_and_invalid_format(export_context):
    client, _, task, repo, odm, _, _ = export_context
    task.progress = 42
    assert client.get(f'/api/task/odm-task-export/{task.id}').status_code == 409
    assert client.get(f'/api/task/odm-task-export/{task.id}?format=exe').status_code == 422
    repo.get_task.side_effect = KeyError('missing')
    assert client.get('/api/task/odm-task-export/missing').status_code == 404
    odm.download_task_assets.assert_not_called()


def test_legacy_png_cache_recovers_original_tiff_and_handles_case(export_context):
    client, _, task, _, odm, cache, original = export_context
    with Image.open(io.BytesIO(original)) as image:
        image.save(cache / f'{task.id}.png')
    assert client.get(f'/api/task/odm-task-export/{task.id}?formula=vndvi&format=jpg').status_code == 200
    odm.download_task_assets.assert_not_called()
    response = client.get(f'/api/task/odm-task-export/{task.id}?format=tiff')
    assert response.content == original
    odm.download_task_assets.assert_awaited_once()


def test_concurrent_exports_publish_one_complete_cached_artifact(export_context):
    _, usecase, task, _, odm, cache, _ = export_context
    async def run():
        return await asyncio.gather(*[
            usecase.get_image_export_path(task.id, 'VARI', 'jpg') for _ in range(4)
        ])
    paths = asyncio.run(run())
    assert len(set(paths)) == 1
    with Image.open(paths[0]) as image:
        image.load()
        assert image.size == (96, 64)
    odm.download_task_assets.assert_awaited_once()
    assert not list(cache.glob('*.part'))


def test_failed_write_never_publishes_partial_output(tmp_path):
    output = tmp_path / 'failed.pdf'
    with pytest.raises(RuntimeError):
        with atomic_output(output) as temporary:
            temporary.write_bytes(b'partial')
            raise RuntimeError('encoding failed')
    assert not output.exists()
    assert not list(tmp_path.glob('*.part'))


def test_cached_download_and_asset_cleanup(export_context):
    client, usecase, task, _, odm, cache, _ = export_context
    url = f'/api/task/odm-task-export/{task.id}?formula=VARI&format=jpg'
    first = client.get(url)
    odm.download_task_assets.side_effect = RuntimeError('offline')
    assert client.get(url).content == first.content
    for extension in ('pdf', 'tiff'):
        (cache / f'{task.id}_rgb.{extension}').write_bytes(b'cached')
    other = cache / f'{task.id}-other.png'
    other.write_bytes(b'keep')
    asyncio.run(usecase.delete_task(task.id))
    assert list(cache.iterdir()) == [other]


def test_asset_failure_can_be_retried(export_context):
    client, _, task, _, odm, cache, _ = export_context
    archive = odm.download_task_assets.return_value
    odm.download_task_assets.return_value = b''
    url = f'/api/task/odm-task-export/{task.id}'
    assert client.get(url).status_code == 404
    assert not list(cache.iterdir())
    odm.download_task_assets.return_value = archive
    assert client.get(url).status_code == 200


def test_deletion_without_any_asset_directory(export_context, monkeypatch):
    _, usecase, task, repo, _, cache, _ = export_context
    monkeypatch.setattr('src.usecases.task.ODM_DIR', cache / 'not-created')
    asyncio.run(usecase.delete_task(task.id))
    repo.delete_task.assert_awaited_once_with(task.id)
